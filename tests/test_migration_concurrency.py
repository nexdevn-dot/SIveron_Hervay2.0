import asyncio
import sqlite3
import pytest
import harvey.state as module
from harvey.state import StateManager


@pytest.mark.asyncio
async def test_parallel_upgrades_are_serial_and_triggers_survive(tmp_path):
    path=str(tmp_path/'parallel.db')
    # Build the schema immediately before approval triggers; future appended
    # migrations are then exercised too, without dropping unrelated tables.
    before=next(i for i,m in enumerate(module.MIGRATIONS) if 'ALTER TABLE outbox ADD COLUMN approved_at' in m)
    with sqlite3.connect(path) as db:
        for migration in module.MIGRATIONS[:before]:db.executescript(migration)
        db.execute(f'PRAGMA user_version={before}')
    await asyncio.gather(*(StateManager(path).init_db() for _ in range(5)))
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==len(module.MIGRATIONS)
        db.execute("INSERT INTO outbox(id,status) VALUES ('approved','approved')")
        assert db.execute("SELECT approved_at FROM outbox WHERE id='approved'").fetchone()[0]


@pytest.mark.asyncio
async def test_failed_migration_rolls_back_schema_and_version(tmp_path,monkeypatch):
    path=str(tmp_path/'atomic.db');sm=StateManager(path);await sm.init_db()
    previous=len(module.MIGRATIONS)
    monkeypatch.setattr(module,'MIGRATIONS',module.MIGRATIONS+["CREATE TABLE partial_change(id TEXT); INVALID SQL;"])
    with pytest.raises(sqlite3.OperationalError):await sm.init_db()
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==previous
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='partial_change'").fetchone()


@pytest.mark.asyncio
@pytest.mark.parametrize('code', [sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED, sqlite3.SQLITE_BUSY | (1 << 8)])
async def test_wal_retries_transient_contention_and_restores_timeout(tmp_path, monkeypatch, code):
    original = module.aiosqlite.Connection.execute
    attempts = 0

    def execute(connection, sql, *args, **kwargs):
        nonlocal attempts
        if sql == 'PRAGMA journal_mode=WAL':
            attempts += 1
            if attempts == 1:
                error = sqlite3.OperationalError('synthetic contention')
                error.sqlite_errorcode = code
                raise error
        return original(connection, sql, *args, **kwargs)

    monkeypatch.setattr(module.aiosqlite.Connection, 'execute', execute)
    sm = StateManager(str(tmp_path / 'transient.db'))
    async with sm._connect() as db:
        await sm._enable_wal(db)
        async with db.execute('PRAGMA busy_timeout') as cursor:
            assert (await cursor.fetchone())[0] == int(module.BUSY_TIMEOUT_SECONDS * 1000)
        async with db.execute('PRAGMA journal_mode') as cursor:
            assert (await cursor.fetchone())[0] == 'wal'
    assert attempts == 2


@pytest.mark.asyncio
async def test_wal_permanent_real_lock_is_bounded_and_does_not_migrate(tmp_path, monkeypatch):
    path = str(tmp_path / 'locked.db')
    monkeypatch.setattr(module, 'BUSY_TIMEOUT_SECONDS', 0.08)
    with sqlite3.connect(path) as holder:
        holder.execute('CREATE TABLE retained(value TEXT)')
        holder.commit()
        holder.execute('BEGIN EXCLUSIVE')
        with pytest.raises(sqlite3.OperationalError) as caught:
            await asyncio.wait_for(StateManager(path).init_db(), timeout=2)
        assert caught.value.sqlite_errorcode & 0xff in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
        holder.rollback()
        assert holder.execute('PRAGMA user_version').fetchone()[0] == 0
        assert not holder.execute("SELECT 1 FROM sqlite_master WHERE name='outbox'").fetchone()
    # Once released, normal startup can finish; no partial migration was left behind.
    await StateManager(path).init_db()


@pytest.mark.asyncio
async def test_wal_non_lock_error_is_not_retried(tmp_path, monkeypatch):
    original = module.aiosqlite.Connection.execute
    attempts = 0

    def execute(connection, sql, *args, **kwargs):
        nonlocal attempts
        if sql == 'PRAGMA journal_mode=WAL':
            attempts += 1
            error = sqlite3.OperationalError('synthetic I/O failure')
            error.sqlite_errorcode = sqlite3.SQLITE_IOERR
            raise error
        return original(connection, sql, *args, **kwargs)

    monkeypatch.setattr(module.aiosqlite.Connection, 'execute', execute)
    with pytest.raises(sqlite3.OperationalError, match='I/O failure'):
        await StateManager(str(tmp_path / 'io.db')).init_db()
    assert attempts == 1


@pytest.mark.asyncio
async def test_wal_cancel_during_retry_propagates(tmp_path, monkeypatch):
    original = module.aiosqlite.Connection.execute
    entered = asyncio.Event()

    def execute(connection, sql, *args, **kwargs):
        if sql == 'PRAGMA journal_mode=WAL':
            entered.set()
            error = sqlite3.OperationalError('synthetic contention')
            error.sqlite_errorcode = sqlite3.SQLITE_BUSY
            raise error
        return original(connection, sql, *args, **kwargs)

    monkeypatch.setattr(module.aiosqlite.Connection, 'execute', execute)
    task = asyncio.create_task(StateManager(str(tmp_path / 'cancel.db')).init_db())
    await asyncio.wait_for(entered.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_wal_mode_refusal_is_reported_without_retry(monkeypatch):
    from contextlib import asynccontextmanager

    class RefusingConnection:
        attempts = 0

        @asynccontextmanager
        async def execute(self, sql):
            if sql == 'PRAGMA journal_mode=WAL':
                self.attempts += 1
            yield self

        async def fetchone(self):
            return ('delete',)

    db = RefusingConnection()
    with pytest.raises(sqlite3.OperationalError, match='could not enable WAL'):
        await StateManager()._enable_wal(db)
    assert db.attempts == 1
