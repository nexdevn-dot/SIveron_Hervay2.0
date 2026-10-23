"""Bounded, job-local public page reader. No credentials or automatic HTTP retries."""
import asyncio
from dataclasses import dataclass, field
import time
from urllib.parse import urljoin, urlsplit

import httpx
from harvey.lookup_diagnostics import diagnostic


@dataclass
class Page:
    html: str
    url: str
    diagnostics: list = field(default_factory=list)


class PublicPageReader:
    def __init__(self, client, guard, *, timeout=15, max_bytes=1_000_000,
                 max_hops=3, max_entries=16, cache_seconds=60, content_types=('html',)):
        self.client, self.guard = client, guard
        self.timeout, self.max_bytes, self.max_hops = timeout, max_bytes, max_hops
        self.max_entries, self.cache_seconds, self.content_types = max_entries, cache_seconds, content_types
        self.cache = {}
        self.lock = asyncio.Lock()

    async def read(self, url):
        # Serialize access to this small job-local cache; cancellation propagates.
        async with self.lock:
            now = time.monotonic()
            if url in self.cache and now-self.cache[url][0] < self.cache_seconds:
                return self.cache[url][1]
            try:
                page = await asyncio.wait_for(self._read(url), timeout=self.timeout)
            except (TimeoutError, httpx.TimeoutException):
                page = Page('', url, [diagnostic('fetch', 'timeout', url, retryable=True)])
            except (httpx.HTTPError, ValueError, UnicodeError):
                page = Page('', url, [diagnostic('fetch', 'network_error', url, retryable=True)])
            if len(self.cache) >= self.max_entries:
                self.cache.pop(next(iter(self.cache)))
            self.cache[url] = (time.monotonic(), page)
            return page

    async def _read(self, url):
        seen = set()
        for _ in range(self.max_hops):
            if url in seen:
                break
            seen.add(url)
            if not await self.guard(url):
                return Page('', url, [diagnostic('fetch', 'unsafe_or_external_url', url)])
            async with self.client.stream('GET', url, follow_redirects=False) as response:
                if response.is_redirect:
                    location = response.headers.get('location')
                    if not location:
                        break
                    url = urljoin(url, location)
                    continue
                if response.status_code != 200:
                    return Page('', url, [diagnostic('fetch', 'http_error', url,
                        retryable=response.status_code >= 500 or response.status_code == 429,
                        http_status=response.status_code)])
                ctype = response.headers.get('content-type', '').lower()
                if not any(kind in ctype for kind in self.content_types):
                    return Page('', url, [diagnostic('fetch', 'unsupported_content', url)])
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body)+len(chunk) > self.max_bytes:
                        return Page('', url, [diagnostic('fetch', 'page_too_large', url)])
                    body.extend(chunk)
                return Page(body.decode(response.encoding or 'utf-8', errors='replace'), url)
        return Page('', url, [diagnostic('fetch', 'redirect_limit', url)])


def public_site_domain(url):
    try:
        return (urlsplit(url).hostname or '').lower().removeprefix('www.')
    except ValueError:
        return ''
