"""Opt-in real Chromium test; all HTTP is fulfilled by an in-memory transport."""
import os
from urllib.parse import urlparse

import httpx
import pytest

from harvey.collectors import company_contacts as C


@pytest.mark.skipif(os.environ.get('HARVEY_BROWSER_TESTS') != '1', reason='Opt-in local Chromium integration')
@pytest.mark.asyncio
async def test_browser_executes_javascript_and_blocks_external_network(monkeypatch):
    requests = []
    checks = []
    async def allowed(url, domain):
        checks.append(url)
        return urlparse(url).hostname == domain
    def respond(request):
        requests.append(str(request.url))
        return httpx.Response(200, headers={'content-type': 'text/html'}, text='''
          <html><body><p id="contact"></p><script>
          document.getElementById('contact').textContent = ['info', 'practice.test'].join('@');
          fetch('http://127.0.0.1/private').catch(() => {});
          fetch('https://agency.test/collect').catch(() => {});
          </script></body></html>''')
    original = httpx.AsyncClient
    monkeypatch.setattr(C, '_public_company_url', allowed)
    monkeypatch.setattr(C.httpx, 'AsyncClient', lambda **kw: original(
        transport=httpx.MockTransport(respond), **kw))
    body, url = await C.render_contact_page('https://practice.test/contact', 'practice.test')
    assert 'info@practice.test' in body
    assert url == 'https://practice.test/contact'
    assert requests == ['https://practice.test/contact']
    assert 'http://127.0.0.1/private' in checks
    assert 'https://agency.test/collect' in checks
