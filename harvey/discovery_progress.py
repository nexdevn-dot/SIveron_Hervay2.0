"""Persisted phase progress with measured, explicitly phase-local ETA."""
import time
import json
import uuid

KEY = 'discovery_progress'


class DiscoveryProgress:
    def __init__(self, state, clock=time.time):
        self.state, self.clock = state, clock
        now = clock()
        self.data = {'id': uuid.uuid4().hex, 'status': 'running', 'stage': 'preparing',
                     'started_at': now, 'phase_started_at': now, 'updated_at': now,
                     'completed': 0, 'total': 0, 'current': '', 'samples': [],
                     'new_companies': 0, 'known_companies': 0, 'errors': 0}

    async def update(self, event):
        now = self.clock()
        old = self.data
        stage = event.get('stage', old['stage'])
        if stage != old['stage']:
            old.update(stage=stage, phase_started_at=now, updated_at=now,
                       completed=0, total=0, samples=[])
        if event.get('error'):
            old['errors'] += 1
        completed = event.get('completed', old['completed'])
        if completed > old['completed']:
            duration = (now - old['updated_at']) / (completed - old['completed'])
            old['samples'] = (old['samples'] + [max(0.001, duration)])[-8:]
            old['updated_at'] = now
        for key in ('completed', 'total', 'current', 'new_companies', 'known_companies', 'errors', 'search', 'result_limits', 'email_summary', 'target_summary'):
            if key in event:
                old[key] = event[key]
        await self.state.set_setting(KEY, json.dumps(old))

    async def finish(self, status='completed'):
        self.data.update(status=status, finished_at=self.clock(), current='')
        await self.state.set_setting(KEY, json.dumps(self.data))


def progress_view(data, running, now=None):
    """Never report an interrupted process as still running, or infer total ETA."""
    if not data:
        return None
    now = time.time() if now is None else now
    view = {key: value for key, value in data.items() if key != 'samples'}
    if not running and view['status'] == 'running':
        view['status'] = 'interrupted'
    end = data.get('finished_at', now) if view['status'] != 'interrupted' else data['updated_at']
    view['elapsed_seconds'] = max(0, round(end - data['started_at']))
    remaining = max(0, data['total'] - data['completed'])
    samples = data.get('samples', [])
    age = max(0, now - data['updated_at'])
    eta = None
    if running and remaining and len(samples) >= 2 and age <= max(samples) * 2:
        low = max(0, remaining * min(samples) - age)
        high = max(low + 1, remaining * max(samples) * 1.3 - age)
        eta = [round(low), round(high)]
    view['eta_seconds'] = eta
    view['waiting'] = bool(running and samples and age > max(5, max(samples) * 2))
    return view
