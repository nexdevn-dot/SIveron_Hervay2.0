"""Durable public-email/person research jobs. No mail sending or contact creation."""
import asyncio
import uuid
import json
from datetime import datetime,timezone
from harvey.lookup_diagnostics import diagnostic,result_diagnostic

import aiosqlite


class ContactJobs:
    def __init__(self, state, kind="email"):
        if kind not in ("email", "people"):
            raise ValueError("Unknown contact job kind")
        self.kind = kind
        self.jobs = "company_" + kind + "_jobs"
        self.items = "company_" + kind + "_job_items"
        self.state = state
        self.task = None

    async def create(self, company_ids, mode='quick', people_criteria=None):
        if mode not in ('quick','thorough'):
            raise ValueError('Invalid email search mode')
        if people_criteria is not None:
            from harvey.decision_makers import criteria
            people_criteria=criteria(people_criteria)
            if self.kind!='people':raise ValueError('Wrong job kind')
        await self.state.init_db()
        job_id = uuid.uuid4().hex
        async with self.state._connect() as db:
            await db.execute('BEGIN IMMEDIATE')
            active = await (await db.execute(
                f"SELECT id FROM {self.jobs} WHERE status IN ('queued','running') LIMIT 1")).fetchone()
            if active:
                return None
            if self.kind == 'email':
                await db.execute("INSERT INTO company_email_jobs(id,status,mode) VALUES (?, 'queued', ?)", (job_id,mode))
            else:
                await db.execute("INSERT INTO company_people_jobs(id,status,criteria_json) VALUES (?, 'queued',?)", (job_id,json.dumps(people_criteria) if people_criteria else ''))
            await db.executemany(
                f"INSERT INTO {self.items}(job_id, company_id, status) VALUES (?, ?, 'queued')",
                [(job_id, company_id) for company_id in dict.fromkeys(company_ids)])
            await db.commit()
        self.start()
        return job_id

    def start(self):
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.run())

    async def snapshot(self, job_id=None):
        await self.state.init_db()
        async with self.state._connect() as db:
            db.row_factory = aiosqlite.Row
            if job_id:
                row = await (await db.execute(f'SELECT * FROM {self.jobs} WHERE id=?', (job_id,))).fetchone()
            else:
                row = await (await db.execute(
                    f'SELECT * FROM {self.jobs} ORDER BY created_at DESC, rowid DESC LIMIT 1')).fetchone()
            if not row:
                return None
            job = dict(row)
            rows = await (await db.execute(
                f"SELECT company_id,(SELECT name FROM companies WHERE id=company_id) AS name, status{', diagnostic_json, attempts' if self.kind == 'email' else ''} FROM {self.items} WHERE job_id=?", (job['id'],))).fetchall()
        counts = {key: 0 for key in ('found', 'not_found', 'no_website', 'failed')}
        for item in rows:
            if item['status'] in counts:
                counts[item['status']] += 1
        job.update(total=len(rows), done=sum(counts.values()), counts=counts,
                   items=[dict(item,diagnostic=json.loads(item['diagnostic_json'])) if self.kind=='email' else dict(item) for item in rows])
        if job['status'] in ('queued', 'running'):
            self.start()
        return job

    async def retry(self,job_id):
        if self.kind!='email':return False
        async with self.state._connect() as db:
            db.row_factory=aiosqlite.Row
            await db.execute('BEGIN IMMEDIATE')
            job=await (await db.execute('SELECT status FROM company_email_jobs WHERE id=?',(job_id,))).fetchone()
            if not job or job['status']!='completed' or await (await db.execute("SELECT 1 FROM company_email_jobs WHERE status IN ('queued','running')")).fetchone():return False
            rows=await (await db.execute("SELECT * FROM company_email_job_items WHERE job_id=? AND status IN ('failed','not_found') AND attempts<3",(job_id,))).fetchall()
            ids=[]
            for row in rows:
                info=json.loads(row['diagnostic_json'])
                try:
                    checked=datetime.fromisoformat(info['checked_at'].replace('Z','+00:00'))
                    if checked.tzinfo is None:checked=checked.replace(tzinfo=timezone.utc)
                    age=(datetime.now(timezone.utc)-checked).total_seconds()
                except (ValueError,KeyError,TypeError):continue
                if info.get('retryable') and age>=60:ids.append(row['company_id'])
            if not ids:return False
            await db.executemany("UPDATE company_email_job_items SET status='queued' WHERE job_id=? AND company_id=?",[(job_id,cid) for cid in ids])
            await db.execute("UPDATE company_email_jobs SET status='queued',stop_requested=0 WHERE id=?",(job_id,))
            await db.commit()
        self.start();return True

    async def stop(self, job_id):
        async with self.state._connect() as db:
            await db.execute(f"UPDATE {self.jobs} SET stop_requested=1 WHERE id=? AND status IN ('queued','running')", (job_id,))
            await db.commit()

    async def run(self):
        from harvey.collectors.company_contacts import lookup_company_emails
        from harvey.collectors.people import lookup_company_people
        lookup = lookup_company_people if self.kind == "people" else lookup_company_emails
        await self.state.init_db()
        # A previous process may have exited during a lookup. Repeating a read is safe.
        async with self.state._connect() as db:
            if self.kind=='email':
                await db.execute("UPDATE company_email_job_items SET status=CASE WHEN attempts>=3 THEN 'failed' ELSE 'queued' END WHERE status IN ('running','queued')")
            else:
                await db.execute(f"UPDATE {self.items} SET status='queued' WHERE status='running'")
            await db.commit()
        while True:
            async with self.state._connect() as db:
                job = await (await db.execute(
                    f"SELECT id{', mode' if self.kind == 'email' else ', criteria_json'} FROM {self.jobs} WHERE status IN ('queued','running') ORDER BY created_at LIMIT 1")).fetchone()
                if not job:
                    return
                job_id = job[0]
                mode = job[1] if self.kind == 'email' else 'quick'
                people_criteria=json.loads(job[1]) if self.kind=='people' and job[1] else None
                await db.execute(f"UPDATE {self.jobs} SET status='running' WHERE id=?", (job_id,))
                await db.commit()
            async def worker():
                while True:
                    async with self.state._connect() as db:
                        await db.execute('BEGIN IMMEDIATE')
                        stopped = await (await db.execute(f'SELECT stop_requested FROM {self.jobs} WHERE id=?', (job_id,))).fetchone()
                        if stopped[0]:
                            return
                        row = await (await db.execute(
                            f"SELECT company_id FROM {self.items} WHERE job_id=? AND status='queued' LIMIT 1", (job_id,))).fetchone()
                        if not row:
                            return
                        company_id = row[0]
                        await db.execute(f"UPDATE {self.items} SET status='running'{', attempts=attempts+1' if self.kind == 'email' else ''} WHERE job_id=? AND company_id=?", (job_id, company_id))
                        await db.commit()
                    try:
                        company = await self.state.get_company(company_id)
                        result = await asyncio.wait_for(lookup(company, self.state, **({'mode':mode} if self.kind == 'email' and mode != 'quick' else {'include_candidate_ids':True} if people_criteria else {})), timeout=80 if mode == 'thorough' else 25) if company else {'status': 'failed'}
                        if people_criteria:
                            from harvey.decision_makers import qualify_job
                            await qualify_job(self.state,job_id,company_id,result.get('candidate_ids',[]),people_criteria)
                        status = result['status'] if result['status'] in ('found', 'not_found', 'no_website') else 'failed'
                    except TimeoutError:
                        status='failed';result={'status':'failed','diagnostics':[diagnostic('lookup','timeout',retryable=True)]}
                    except Exception:
                        status='failed';result={'status':'failed','diagnostics':[diagnostic('lookup','lookup_failed',retryable=True)]}
                    async with self.state._connect() as db:
                        if self.kind=='email':
                            await db.execute('UPDATE company_email_job_items SET status=?,diagnostic_json=? WHERE job_id=? AND company_id=?',(status,json.dumps(result_diagnostic(result)),job_id,company_id))
                        else:
                            await db.execute(f'UPDATE {self.items} SET status=? WHERE job_id=? AND company_id=?', (status, job_id, company_id))
                        await db.commit()
            await asyncio.gather(worker(), worker())
            async with self.state._connect() as db:
                await db.execute(f"UPDATE {self.jobs} SET status=CASE WHEN stop_requested THEN 'stopped' ELSE 'completed' END WHERE id=?", (job_id,))
                await db.commit()
