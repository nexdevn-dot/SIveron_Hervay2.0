import asyncio

import pytest
from harvey.collectors.contact_jobs import ContactJobs
from harvey.collectors import company_contacts as C
from harvey.models import Company
from harvey.state import StateManager


async def setup_state(tmp_path, count=5):
    state = StateManager(str(tmp_path / 'jobs.db'))
    await state.init_db()
    ids = []
    for index in range(count):
        ids.append(await state.add_company(Company(name=f'Company {index}', domain=f'company{index}.test')))
    return state, ids


@pytest.mark.asyncio
async def test_durable_job_deduplicates_and_limits_concurrency(tmp_path, monkeypatch):
    state, ids = await setup_state(tmp_path)
    active = peak = 0
    both_entered = asyncio.Event()
    async def lookup(company, state):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        if active == 2:
            both_entered.set()
        # Do not infer overlap from filesystem/timer speed on a CI runner.
        await asyncio.wait_for(both_entered.wait(), timeout=10)
        active -= 1
        return {'status': 'found', 'found': 1}
    monkeypatch.setattr(C, 'lookup_company_emails', lookup)
    jobs = ContactJobs(state)
    job_id = await jobs.create(ids + ids)
    await jobs.task
    result = await jobs.snapshot(job_id)
    assert result['status'] == 'completed'
    assert result['total'] == result['done'] == 5
    assert result['counts']['found'] == 5
    assert peak == 2
    # Results are available to a completely new service instance.
    assert (await ContactJobs(state).snapshot(job_id))['counts'] == result['counts']


@pytest.mark.asyncio
async def test_stop_keeps_running_lookups_and_resumes_interrupted_jobs(tmp_path, monkeypatch):
    state, ids = await setup_state(tmp_path)
    entered = asyncio.Event()
    release = asyncio.Event()
    async def lookup(company, state):
        entered.set()
        await release.wait()
        return {'status': 'not_found', 'found': 0}
    monkeypatch.setattr(C, 'lookup_company_emails', lookup)
    jobs = ContactJobs(state)
    job_id = await jobs.create(ids)
    await entered.wait()
    assert await jobs.create(ids) is None
    await jobs.stop(job_id)
    release.set()
    await jobs.task
    snapshot = await jobs.snapshot(job_id)
    assert snapshot['status'] == 'stopped' and 1 <= snapshot['done'] <= 2
    # Simulate a process exiting after claiming an item.
    async with state._connect() as db:
        await db.execute("UPDATE company_email_jobs SET status='running', stop_requested=0 WHERE id=?", (job_id,))
        await db.execute("UPDATE company_email_job_items SET status='running' WHERE job_id=? AND status='queued'", (job_id,))
        await db.commit()
    restored = ContactJobs(state)
    await restored.snapshot(job_id)
    await restored.task
    assert (await restored.snapshot(job_id))['done'] == 5


@pytest.mark.asyncio
async def test_failed_item_does_not_abort_other_companies(tmp_path, monkeypatch):
    state, ids = await setup_state(tmp_path, 2)
    async def lookup(company, state):
        if company.id == ids[0]:
            raise RuntimeError('site unavailable')
        return {'status': 'no_website', 'found': 0}
    monkeypatch.setattr(C, 'lookup_company_emails', lookup)
    jobs = ContactJobs(state)
    job_id = await jobs.create(ids)
    await jobs.task
    result = await jobs.snapshot(job_id)
    assert result['counts']['failed'] == result['counts']['no_website'] == 1
    assert result['done'] == 2 and result['status'] == 'completed'
