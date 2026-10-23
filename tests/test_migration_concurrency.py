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
