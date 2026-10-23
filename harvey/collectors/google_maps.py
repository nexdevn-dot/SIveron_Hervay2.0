"""Local Maps collector. No service, extension, account or model required.

Search-unit/checkpoint concepts informed by zimkk/Lead-Scraper-Google-Maps
and sonagara-vashram/google-maps-scraper (MIT); implementation is native to
Siveron's provider contract. Blocks are reported, never bypassed.
"""
import asyncio
from dataclasses import asdict, replace
import hashlib
import json
import math
import os
import re
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs

MAX_UNITS = 100
MAX_RESULTS = 200


def configure_browser_path():
    from harvey.paths import PROJECT_ROOT
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(PROJECT_ROOT / '.cache' / 'ms-playwright'))


async def browser_available():
    configure_browser_path()
    try:
        from playwright.async_api import async_playwright
        # No browser is started and no network accessed during preflight.
        async with async_playwright() as p:
            return Path(p.chromium.executable_path).is_file()
    except Exception:
        return False


def distance_km(a, b):
    x, y = map(math.radians, a)
    u, v = map(math.radians, b)
    h = math.sin((u-x)/2)**2 + math.cos(x)*math.cos(u)*math.sin((v-y)/2)**2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def coordinates(raw):
    try:
        lat, lon, radius = map(float, raw.split(','))
    except (ValueError, AttributeError):
        raise ValueError('Google Maps requires a resolved location and radius.')
    if not all(map(math.isfinite, (lat, lon, radius))) or not (-85 <= lat <= 85 and -180 <= lon <= 180 and 1 <= radius <= 200):
        raise ValueError('Invalid Google Maps coordinates or radius.')
    return lat, lon, radius


def plan(queries):
    """Bounded 3x3 coverage; it improves coverage, never promises completeness."""
    out = []
    for q in queries:
        if not 1 <= q.limit <= MAX_RESULTS:
            raise ValueError('Google Maps allows 1–200 results per search section.')
        if q.maps_mode not in ('quick', 'grid') or q.maps_filter not in ('all', 'website', 'no_website', 'phone'):
            raise ValueError('Invalid Google Maps search options.')
        if not q.location and not q.coordinate:
            raise ValueError('Google Maps requires a specific location.')
        if q.maps_mode == 'quick':
            out.append(q)
        else:
            # At estimate time place names may not yet be geocoded. Keep the
            # same unit count, without doing a network request in the planner.
            center = coordinates(q.coordinate) if q.coordinate else None
            for row in (-1, 0, 1):
                for col in (-1, 0, 1):
                    coordinate = q.coordinate
                    if center:
                        lat, lon, radius = center
                        lat += row * radius * .6 / 111.32
                        lon += col * radius * .6 / (111.32 * math.cos(math.radians(center[0])))
                        if not -180 <= lon <= 180 or not -85 <= lat <= 85:
                            raise ValueError('Search grid crosses supported coordinate bounds.')
                        coordinate = f'{lat},{lon},{radius}'
                    out.append(replace(q, coordinate=coordinate, maps_origin=q.coordinate,
                                       maps_cell=f'{row},{col}'))
    if len(out) > MAX_UNITS:
        raise ValueError('Google Maps allows at most 100 search sections. Narrow the search.')
    return out


def safe_maps_url(url):
    try:
        p = urlparse(url)
        return p.scheme == 'https' and p.hostname == 'www.google.com' and p.path.startswith('/maps/') and not p.username and not p.password
    except ValueError:
        return False


def place_key(url):
    if not safe_maps_url(url):
        return ''
    p = urlparse(url)
    cid = parse_qs(p.query).get('cid', [''])[0]
    match = re.search(r'!1s([^!/?&]+)', url)
    token = cid if cid.isdigit() else match.group(1) if match else ''
    return 'google_maps:' + (token or hashlib.sha256((p.path+'?'+p.query).encode()).hexdigest())


def place_coordinates(url):
    # !3d/!4d denote the place; @lat,lng is only the map viewport.
    match = re.search(r'!3d(-?[\d.]+)!4d(-?[\d.]+)', url)
    if not match:
        return None
    lat, lon = map(float, match.groups())
    return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 else None


def build_business(raw, url, query):
    from harvey.collectors.discover import Business, normalize_domain
    if not safe_maps_url(url) or not raw.get('name') or not raw.get('panel'):
        return None
    point = place_coordinates(url)
    origin = coordinates(query.maps_origin or query.coordinate)
    # A strict radius cannot be confirmed from a viewport or unknown point.
    if point is None or distance_km(origin[:2], point) > origin[2]:
        return None
    website = raw.get('website') or ''
    try:
        parsed = urlparse(website)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
            website = ''
    except ValueError:
        website = ''
    phone = re.sub(r'^(Phone|Telefon):\s*', '', raw.get('phone') or '', flags=re.I)
    if query.maps_filter == 'website' and not website or query.maps_filter == 'no_website' and website or query.maps_filter == 'phone' and not phone:
        return None
    rating = raw.get('rating') or ''
    match = re.search(r'(\d[.,]\d)', rating)
    rating_value = float(match.group(1).replace(',', '.')) if match else None
    if rating_value is not None and not 0 <= rating_value <= 5:
        rating_value = None
    return Business(rating=rating_value, name=raw['name'].strip(), website=website, domain=normalize_domain(website),
                    phone=phone, address=raw.get('address') or '', location=raw.get('address') or query.location,
                    category=raw.get('category') or query.term, has_website=bool(website),
                    external_id=place_key(url), source_url=url, provider='google_maps')


EXTRACT = """() => {
 const panel = document.querySelector('[role="main"][aria-label]');
 const root = panel || document;
 const text = s => root.querySelector(s)?.textContent?.trim() || '';
 return {panel:!!panel, name:text('h1'),
 website:root.querySelector('a[data-item-id="authority"]')?.href || '',
 phone:root.querySelector('[data-item-id^="phone:"]')?.getAttribute('aria-label') || '',
 address:text('[data-item-id="address"] .Io6YTe') || text('[data-item-id="address"]'),
 category:text('button[jsaction*="category"]'), rating:root.querySelector('[role="img"][aria-label*="Stern"], [role="img"][aria-label*="star"]')?.getAttribute('aria-label') || ''};
}"""


class MapsInterrupted(RuntimeError):
    pass


async def check_page(page):
    if 'sorry' in page.url or await page.locator('iframe[src*="recaptcha"], form[action*="sorry"]').count():
        raise MapsInterrupted('Google Maps blocked the request. Search paused; try again later.')
    if 'consent.google.' in page.url:
        # No automatic acceptance of terms/cookies or account sign-in.
        reject = page.get_by_role('button', name=re.compile(r'Reject all|Alle ablehnen', re.I))
        if await reject.count():
            await reject.first.click()
            await page.wait_for_load_state('domcontentloaded')
        else:
            raise MapsInterrupted('Google Maps consent requires attention. Search paused.')


async def fetch(query, state, on_progress=None):
    from harvey.collectors.discover import Business
    configure_browser_path()
    from playwright.async_api import async_playwright
    coordinates(query.coordinate)
    fingerprint = {k:v for k,v in asdict(query).items() if k != 'maps_resume'}
    cache_key = 'maps_checkpoint:' + hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
    saved = await state.get_setting(cache_key) if query.maps_resume else None
    try:
        cache = json.loads(saved) if saved else {}
    except (ValueError, TypeError):
        cache = {}
    records = cache.get('records', [])
    done = set(cache.get('done', []))
    links = cache.get('links', [])
    async def persist(complete=False):
        await state.set_setting(cache_key, json.dumps({'records':records, 'done':sorted(done), 'links':links, 'complete':complete}))
    async def paused():
        if await state.get_setting('discovery_paused'):
            await persist()
            raise MapsInterrupted('Search paused. Saved sections can be resumed.')
    if cache.get('complete'):
        return [Business(**row) for row in records]
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception as exc:
            raise RuntimeError('Chromium is unavailable. Run bash scripts/install-maps-browser.sh.') from exc
        try:
            context = await browser.new_context(locale='de-DE', accept_downloads=False)
            async def route_request(route):
                host = urlparse(route.request.url).hostname or ''
                if any(host == d or host.endswith('.'+d) for d in ('google.com','google.de','gstatic.com','googleusercontent.com')):
                    await route.continue_()
                else:
                    await route.abort()
            await context.route('**/*', route_request)
            page = await context.new_page()
            page.set_default_timeout(12000)
            lat, lon, radius = coordinates(query.coordinate)
            zoom = max(8, min(15, round(14-math.log2(max(1,radius/3)))))
            if not links:
                await paused()
                url = f'https://www.google.com/maps/search/{quote(query.keyword(), safe="")}/@{lat},{lon},{zoom}z?hl=de'
                await page.goto(url, wait_until='domcontentloaded', timeout=45000)
                await check_page(page)
                try:
                    await page.locator('a[href*="/maps/place/"], [role="main"][aria-label] h1').first.wait_for(timeout=15000)
                except Exception as exc:
                    await check_page(page)
                    raise RuntimeError('Google Maps returned no readable results. The page layout may have changed.') from exc
                stagnant = 0
                for _ in range(30):
                    await paused()
                    await check_page(page)
                    found = await page.locator('a[href*="/maps/place/"]').evaluate_all('(els) => els.map(el => el.href)')
                    previous = len(links)
                    links = list(dict.fromkeys(links + [u for u in found if safe_maps_url(u)]))[:query.limit]
                    if not links and safe_maps_url(page.url) and '/maps/place/' in page.url:
                        links = [page.url]
                    stagnant = stagnant + 1 if len(links) == previous else 0
                    if len(links) >= query.limit or stagnant >= 3:
                        break
                    feed = page.locator('[role="feed"]')
                    if not await feed.count():
                        break
                    await feed.evaluate('(el) => el.scrollBy(0, el.clientHeight)')
                    await asyncio.sleep(1.5)
                await persist()
            detail = await context.new_page()
            detail.set_default_timeout(12000)
            for url in links:
                await paused()
                if url in done:
                    continue
                if on_progress:
                    await on_progress({'current': f'{query.keyword()} · {len(done)}/{len(links)}'})
                await detail.goto(url, wait_until='domcontentloaded', timeout=45000)
                await check_page(detail)
                await detail.locator('[role="main"][aria-label] h1').first.wait_for(timeout=15000)
                raw = await detail.evaluate(EXTRACT)
                business = build_business(raw, detail.url, query)
                if business:
                    records.append(asdict(business))
                done.add(url)
                await persist()
                await asyncio.sleep(1.5)
            await persist(True)
            return [Business(**row) for row in records]
        finally:
            await browser.close()
