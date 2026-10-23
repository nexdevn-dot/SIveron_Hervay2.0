import asyncio
import httpx
import pytest
from harvey.collectors.public_pages import PublicPageReader


@pytest.mark.asyncio
async def test_shared_page_cache_redirect_guard_and_size():
    calls=[]
    async def guard(url): return url.startswith('https://firm.test/')
    def handler(request):
        calls.append(str(request.url))
        if request.url.path=='/': return httpx.Response(302,headers={'location':'/contact'})
        if request.url.path=='/external': return httpx.Response(302,headers={'location':'https://external.test/'})
        return httpx.Response(200,text='abcdef',headers={'content-type':'text/html'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reader=PublicPageReader(client,guard,max_bytes=6)
        first=await reader.read('https://firm.test/')
        assert first.html=='abcdef' and first.url=='https://firm.test/contact'
        assert await reader.read('https://firm.test/') is first
        assert len(calls)==2
        denied=await reader.read('https://firm.test/external')
        assert denied.diagnostics[0]['code']=='unsafe_or_external_url' and len(calls)==3
        reader=PublicPageReader(client,guard,max_bytes=5)
        assert (await reader.read('https://firm.test/contact')).diagnostics[0]['code']=='page_too_large'


@pytest.mark.asyncio
async def test_reader_failures_are_bounded_without_retry_amplification():
    async def guard(url): return True
    def handler(request):
        if request.url.path=='/loop':return httpx.Response(302,headers={'location':'/loop'})
        if request.url.path=='/429':return httpx.Response(429)
        if request.url.path=='/json':return httpx.Response(200,json={})
        raise httpx.ConnectError('private exception data')
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reader=PublicPageReader(client,guard)
        for path,code in [('loop','redirect_limit'),('429','http_error'),('json','unsupported_content'),('error','network_error')]:
            result=await reader.read('https://firm.test/'+path+'?secret=hidden')
            assert not result.html and result.diagnostics[0]['code']==code
            assert 'hidden' not in str(result.diagnostics)
        assert (await reader.read('https://firm.test/429')).diagnostics[0]['retryable']


@pytest.mark.asyncio
async def test_total_timeout_and_cancellation():
    async def slow_guard(url): await asyncio.sleep(.1);return True
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200))) as client:
        result=await PublicPageReader(client,slow_guard,timeout=.01).read('https://firm.test/')
        assert result.diagnostics[0]['code']=='timeout'
        task=asyncio.create_task(PublicPageReader(client,slow_guard).read('https://firm.test/'))
        await asyncio.sleep(0);task.cancel()
        with pytest.raises(asyncio.CancelledError):await task


def test_domain_helper_handles_www_and_invalid_urls():
    from harvey.collectors.public_pages import public_site_domain
    assert public_site_domain('https://www.firm.test/path')=='firm.test'
    assert public_site_domain('http://[broken')==''


@pytest.mark.asyncio
async def test_profile_reader_uses_shared_policy_for_real_get(monkeypatch):
    from harvey.collectors.profile import ProfileCollector
    from harvey.collectors import company_contacts
    async def guard(url, domain):return domain=='firm.test' and url.startswith('https://firm.test')
    monkeypatch.setattr(company_contacts,'_public_company_url',guard)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,text='robots',headers={'content-type':'text/plain'}))) as client:
        collector=ProfileCollector(None)
        collector._client=client
        assert await collector._get('https://firm.test/robots.txt')=='robots'
        collector._page_domain='firm.test'
        assert await collector._get('https://other.test/')==''
        assert collector.page_diagnostics[-1]['code']=='unsafe_or_external_url'
