"""Exercise current reuse seams using synthetic data and no external services.

Run from the repository root: .venv/bin/python -m examples.reuse.offline_demo
This is an integration example for an installed checkout, not a standalone SDK.
"""
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from harvey.assistant import Plan
from harvey.campaign_content import rich_content
from harvey.collectors.discover import DiscoveryQuery
from harvey.collectors.public_pages import PublicPageReader
from harvey.collectors.structured_company import extract_company_fields
from harvey.company_filtering import validate_filters, page_data
from harvey.company_reports import create_reports, markdown
from harvey.decision_makers import criteria, qualify
from harvey.discovery_progress import DiscoveryProgress, progress_view
from harvey.email_checks import email_checks, normalize_public_email
from harvey.models import Company
from harvey.sales_workflows import opportunity_values
from harvey.signals import seed_signal_catalog
from harvey.state import StateManager
from harvey.target_profiles import validate_profile, evaluate_profile


class MemorySettings:
    def __init__(self):
        self.values = {}

    async def set_setting(self, key, value):
        self.values[key] = value


async def main():
    assert email_checks('hello@demo.test')['send_supported'] is True
    assert email_checks('broken')['reason'] == 'syntax_invalid'
    assert normalize_public_email('hello@example.com') is None

    html = '<script type="application/ld+json">' + json.dumps({
        '@type': 'Organization', 'name': 'Demo Company',
        'url': 'https://demo.test/', 'telephone': '+49 123456789',
    }) + '</script>'

    def mock_response(request):
        return httpx.Response(200, text=html, headers={'content-type': 'text/html'})

    async def mock_only_guard(url):
        # MockTransport handles every request. This host check is NOT a complete
        # production public-address/SSRF policy; never pair it with real HTTP.
        return url == 'https://demo.test/'

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_response)) as client:
        reader = PublicPageReader(client, mock_only_guard)
        page = await reader.read('https://demo.test/')
        fields = extract_company_fields(page.html, page.url, 'demo.test', 'Demo Company')
        assert any(f['field'] == 'phone' and f['value'] == '+49 123456789' for f in fields)
        rejected = await reader.read('https://other.test/')
        assert rejected.diagnostics[0]['code'] == 'unsafe_or_external_url'

    query = DiscoveryQuery(term='sample service', location='Example City')
    assert query.keyword() == 'sample service Example City'
    closed = opportunity_values({'title': 'Synthetic opportunity', 'stage': 'won'})
    assert closed['next_due'] == ''  # Validation only; nothing is saved.

    chosen = criteria({'roles': ['management']})
    assert qualify('CEO', chosen)['verdict'] == 'match'
    assert qualify('Former CEO', chosen)['verdict'] == 'no_match'
    assert qualify('', chosen)['verdict'] == 'unknown'

    document = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [
        {'type': 'text', 'text': 'Hello {{first_name}}'},
    ]}]}
    normalized, plain, rendered = rich_content(document, {'first_name': '<Demo>'})
    assert plain == 'Hello <Demo>' and '&lt;Demo&gt;' in rendered
    assert normalized['type'] == 'doc'

    plan = Plan.model_validate({
        'action': 'discover', 'explanation': 'Synthetic search proposal',
        'terms': ['sample service'], 'cities': ['Example City'], 'radius_km': 25,
    }).checked({})
    assert plan.action == 'discover'  # No provider or model is invoked.

    clock = [100.0]
    memory = MemorySettings()
    progress = DiscoveryProgress(memory, clock=lambda: clock[0])
    for completed in (1, 2):
        clock[0] += 2
        await progress.update({'stage': 'preparing', 'completed': completed, 'total': 4})
    view = progress_view(json.loads(memory.values['discovery_progress']), True, now=clock[0])
    assert view['eta_seconds'] is not None
    assert progress_view(progress.data, False, now=clock[0])['status'] == 'interrupted'
    await progress.finish()

    # All database initialization and report writes are confined to this directory.
    with TemporaryDirectory(prefix='siveron-reuse-') as tmp:
        state = StateManager(str(Path(tmp) / 'example.db'))
        await state.init_db()
        await seed_signal_catalog(state)
        await state.add_company(Company(id='demo', name='Demo Company', domain='demo.test'))
        profile = validate_profile({
            'name': 'Example profile', 'require': ['NO_WEBSITE'],
        }, {'NO_WEBSITE'})
        filters = validate_filters({'q': 'Demo', 'website': 'with'})
        inventory = await page_data(state.db_path, 1, filters)
        assert inventory['total'] == 1
        evaluation = await evaluate_profile(state, profile, company_ids=['demo'])
        assert evaluation['counts']['unknown'] == 1  # No signal was activated or collected.
        reports = await create_reports(state, {
            'company_ids': ['demo'], 'categories': ['discovery'], 'language': 'en',
        })
        assert reports[0]['counts']['potential'] == 0
        assert reports[0]['counts']['unknown'] > 0
        assert 'Demo Company' in markdown(reports[0])

    print('Offline reuse example passed: email, mock pages, structured fields, roles,')
    print('rich text, plan validation, progress, evidence evaluation and report export.')


if __name__ == '__main__':
    asyncio.run(main())
