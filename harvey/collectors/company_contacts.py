"""Public company inboxes with evidence, separate from personal lead records.

No guessed address patterns, SMTP probes, contact creation or sending.
Quick lookup reads a homepage and at most two contact/legal pages; thorough
lookup reads at most six subpages. Browser rendering is bounded to one/two
pages only when no relevant address was found.
"""
import asyncio
from functools import lru_cache
from html import unescape
from html.parser import HTMLParser
import ipaddress
import re
import socket
from urllib.parse import unquote, urljoin, urlparse, parse_qs, urlencode

import httpx
import extruct
from email_validator import validate_email, EmailNotValidError, caching_resolver
from dns.resolver import LRUCache
from harvey.email_checks import normalize_public_email

EMAIL = re.compile(r"[\w.!#$%&'*+/=?^_`{|}~-]+@[\w-]+(?:\.[\w-]+)+", re.I)


# Kept as a compatibility import for collectors, manual contacts and existing callers.
normalize_email = normalize_public_email


def valid_email(value):
    return normalize_email(str(value)) is not None


# Explicit markers only: avoid turning ordinary prose into invented addresses.
_AT = re.compile(r"\s*(?:\[at\]|\(at\)|\{at\})\s*", re.I)
_DOT = re.compile(r"\s*(?:\[dot\]|\(dot\)|\{dot\}|\[punkt\]|\(punkt\))\s*", re.I)


def _structured_email_values(html, source):
    try:
        data = extruct.extract(html, base_url=source or None,
                               syntaxes=['json-ld', 'microdata'], errors='ignore')
    except (ValueError, TypeError, RecursionError):
        return []
    values, pending = [], [data]
    # Read only explicitly declared email properties, never arbitrary script strings.
    for _ in range(10000):
        if not pending:
            break
        node = pending.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                if key.rsplit('/', 1)[-1].rsplit('#', 1)[-1].lower() == 'email':
                    values.extend(value if isinstance(value, list) else [value])
                elif isinstance(value, (dict, list)):
                    pending.append(value)
        elif isinstance(node, list):
            pending.extend(node)
    return [unquote(value.removeprefix('mailto:').split('?', 1)[0])
            for value in values if isinstance(value, str)]


class _VisibleContactHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links = [], []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'a' and not self.hidden:
            href = dict(attrs).get('href', '')
            self.links.append(href)
            if href.lower().startswith('mailto:'):
                self.text.append(unquote(href[7:].split('?', 1)[0]))

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, text):
        if not self.hidden:
            self.text.append(text)


def extract_public_emails(html, source=''):
    parser = _VisibleContactHTML()
    parser.feed(html)
    text = unescape(' '.join(parser.text))
    text = _DOT.sub('.', _AT.sub('@', text))
    candidates = EMAIL.findall(text) + _structured_email_values(html, source)
    return list(dict.fromkeys(normalized for email in candidates
                              if (normalized := normalize_email(email)) and public_email_candidate(normalized)))[:20]


def contact_page_links(html, source, domain, mode='quick'):
    """Actual navigation before fallback paths; never leave the company host."""
    from bs4 import BeautifulSoup
    if mode not in ('quick', 'thorough'):
        raise ValueError('Invalid email search mode')
    soup = BeautifulSoup(html, 'html.parser')
    ranked = []
    for anchor in soup.find_all('a', href=True):
        url = urljoin(source, anchor['href']).split('#', 1)[0]
        try:
            parsed = urlparse(url)
        except ValueError:
            continue
        if parsed.scheme not in ('http', 'https') or parsed.hostname not in (domain, 'www.' + domain) or parsed.username or parsed.password:
            continue
        label = parsed.path + ' ' + anchor.get_text(' ', strip=True)
        if re.search(r'kontakt|contact', label, re.I): rank = 0
        elif re.search(r'impressum|imprint|legal', label, re.I): rank = 1
        elif mode == 'thorough' and re.search(r'about|über.uns|ueber.uns|team|ansprechpartner', label, re.I): rank = 2
        else: continue
        ranked.append((rank, url))
    links = [url for _, url in sorted(ranked, key=lambda pair: pair[0])]
    paths = ('/kontakt', '/impressum') if mode == 'quick' else ('/kontakt', '/contact', '/contact-us', '/impressum', '/about', '/about-us')
    links.extend(urljoin(source, path) for path in paths)
    return list(dict.fromkeys(links))[:2 if mode == 'quick' else 6]


def public_email_candidate(email):
    """Extraction-only noise rules; manual address validation stays unchanged."""
    local, _, host = email.casefold().partition('@')
    technical = ('sentry.io', 'wixpress.com', 'schema.org', 'w3.org')
    return not (any(host == d or host.endswith('.' + d) for d in technical) or
                host.endswith(('.css', '.js', '.ico', '.woff', '.woff2', '.ttf', '.mp4', '.pdf', '.gif')) or
                re.fullmatch(r'[0-9a-f]{16,}', local))


def social_profile_links(html, source):
    """Only explicit website links, no platform crawling or inferred profiles."""
    from bs4 import BeautifulSoup
    networks = {'facebook.com':'Facebook','fb.com':'Facebook','instagram.com':'Instagram',
                'linkedin.com':'LinkedIn','tiktok.com':'TikTok','youtube.com':'YouTube'}
    found = {}
    for anchor in BeautifulSoup(html, 'html.parser').find_all('a', href=True):
        url = urljoin(source, anchor['href'])
        if len(url) > 2048: continue
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or '').lower().removeprefix('www.')
            if parsed.scheme not in ('http','https') or parsed.username or parsed.password or parsed.port not in (None,80,443): continue
        except ValueError: continue
        network = next((label for base,label in networks.items() if host == base or host.endswith('.'+base)), None)
        path = parsed.path.rstrip('/')
        if not network or not path or re.search(r'/(?:share|sharer|intent|plugins|login|signup|help|legal|privacy)(?:[/.]|$)', path, re.I): continue
        if host.endswith('youtube.com') and not (path.startswith('/@') or path.startswith('/channel/') or path.startswith('/c/')): continue
        if re.search(r'/(?:p|reel|reels|posts|watch|videos|feed|groups|dialog|l\.php)(?:/|$)',path,re.I): continue
        if network == 'TikTok' and not re.fullmatch(r'/@[^/]+',path): continue
        profile_query = ''
        if network == 'Facebook' and path == '/profile.php':
            ident = parse_qs(parsed.query).get('id',[''])[0]
            if not ident.isdigit(): continue
            profile_query = urlencode({'id':ident})
        clean = parsed._replace(query=profile_query, fragment='').geturl()
        found.setdefault(clean, {'network':network,'url':clean,'source_url':source})
    return list(found.values())[:12]


def official_contact_emails(html, source, domain, company_name):
    """Require visible owner/contact evidence for a different mail domain.

    No domain similarity guesses: names in email addresses are not ownership
    evidence, and agency/privacy-provider attribution blocks stay excluded.
    """
    from bs4 import BeautifulSoup
    if not html or urlparse(source).hostname not in (domain, 'www.' + domain):
        return set()
    generic = {'gmbh', 'company', 'limited', 'unternehmen', 'bauunternehmen',
               'bauunternehmung', 'firma', 'service', 'services', 'praxis', 'practice'}
    names = [word for word in re.findall(r'[^\W\d_]{4,}', company_name.casefold()) if word not in generic]
    if not names:
        return set()
    soup = BeautifulSoup(html, 'html.parser')
    for hidden in soup(['script', 'style', 'noscript', 'template']):
        hidden.decompose()
    attribution = re.compile(r'webdesign|webagentur|website\s+(?:by|von)|design\s+(?:by|von)|'
                             r'erstellt\s+(?:durch|von)|created\s+by|powered\s+by|'
                             r'technische\s+umsetzung|datenschutzbeauftrag', re.I)
    contact = re.compile(r'kontakt|contact|impressum|imprint|e-?mail|mail\s*:|telefon|tel[.:]', re.I)
    legal_page = bool(re.search(r'impressum|imprint|kontakt|contact', urlparse(source).path, re.I))
    accepted = set()
    nodes = [node.parent for node in soup.find_all(string=lambda value: value and ('@' in value or re.search(r'\[at\]|\(at\)', value, re.I)))]
    nodes.extend(soup.select('a[href^="mailto:"]'))
    for node in nodes:
        for _ in range(5):
            if node is None or node.name in ('body', 'html', 'main', '[document]'):
                break
            text = node.get_text(' ', strip=True)
            if len(text) > 2000:
                break
            if attribution.search(text):
                break
            # Do not count the address itself as evidence of the company name.
            owner_text = EMAIL.sub('', _DOT.sub('.', _AT.sub('@', text))).casefold()
            owner = any(re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', owner_text) for name in names)
            if owner and (legal_page or contact.search(text)):
                accepted.update(extract_public_emails(str(node), source))
                break
            node = node.parent
    return accepted


def relevant_company_emails(emails, domain, *, html='', source='', company_name=''):
    """Avoid attributing a web agency's footer address to the company."""
    domain = domain.lower().removeprefix('www.').encode('idna').decode('ascii')
    emails = [email for email in emails if normalize_email(email)]
    def email_domain(email):
        return email.rsplit('@', 1)[-1].encode('idna').decode('ascii')
    mailboxes = {'gmail.com', 'googlemail.com', 'gmx.de', 'gmx.net', 'web.de',
                 'outlook.com', 'hotmail.com', 't-online.de', 'icloud.com', 'yahoo.com'}
    contextual = official_contact_emails(html, source, domain, company_name)
    return [email for email in emails if email in contextual or email_domain(email) in mailboxes or
            email_domain(email) == domain or email_domain(email).endswith('.' + domain)]


async def _public_company_url(url, domain):
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if (parsed.scheme not in ('http', 'https') or parsed.username or parsed.password or
            parsed.port not in (None, 80, 443) or host not in (domain, 'www.' + domain)):
        return False
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, None, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)
    except (OSError, ValueError):
        return False


async def render_contact_page(url, domain):
    """One bounded browser fallback; all network traffic passes the same host guard."""
    from playwright.async_api import async_playwright, Error as BrowserError
    async def render():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                context = await browser.new_context(service_workers='block', accept_downloads=False)
                # Prevent browser network channels that do not go through HTTP routing.
                await context.add_init_script("window.WebSocket=undefined;window.RTCPeerConnection=undefined;")
                await context.route_web_socket('**/*', lambda ws: ws.close())
                count = 0
                async with httpx.AsyncClient(timeout=2, follow_redirects=False) as client:
                    async def route_request(route):
                        nonlocal count
                        request = route.request
                        count += 1
                        if (count > 20 or request.method != 'GET' or
                                request.resource_type not in ('document', 'script', 'stylesheet', 'xhr', 'fetch') or
                                not await _public_company_url(request.url, domain)):
                            await route.abort()
                            return
                        try:
                            async with client.stream('GET', request.url) as response:
                                body = bytearray()
                                async for chunk in response.aiter_bytes():
                                    body.extend(chunk)
                                    if len(body) > 1_000_000:
                                        await route.abort()
                                        return
                                headers = {key: value for key, value in response.headers.items()
                                           if key.lower() not in ('content-encoding', 'content-length', 'transfer-encoding')}
                                await route.fulfill(status=response.status_code, headers=headers, body=bytes(body))
                        except (httpx.HTTPError, ValueError):
                            await route.abort()
                    await context.route('**/*', route_request)
                    page = await context.new_page()
                    await page.goto(url, wait_until='networkidle', timeout=4000)
                    return (await page.content())[:1_000_000], page.url
            finally:
                await browser.close()
    try:
        return await asyncio.wait_for(render(), timeout=6)
    except (BrowserError, TimeoutError, OSError):
        # A missing browser installation must never break ordinary HTML lookup.
        return '', url


@lru_cache(maxsize=1)
def domain_dns_resolver():
    # dnspython's LRU cache is thread-safe and honors DNS expiry, including negative answers.
    # Timeouts are not converted into negative results or cached as mailbox failures.
    return caching_resolver(timeout=2, cache=LRUCache(max_size=1024))


async def check_email_domain(email):
    """Bounded DNS-only validation. Does not contact SMTP or prove a mailbox exists."""
    def check():
        try:
            result = validate_email(email, check_deliverability=True, dns_resolver=domain_dns_resolver())
            return 'mail_domain_present' if getattr(result, 'mx', None) else 'unknown'
        except EmailNotValidError as error:
            # Syntax was already checked; this is domain-level evidence only.
            from email_validator import EmailUndeliverableError
            return 'no_mail_domain' if isinstance(error, EmailUndeliverableError) else 'unknown'
    try:
        return await asyncio.wait_for(asyncio.to_thread(check), timeout=3)
    except (TimeoutError, OSError):
        return 'unknown'


def mailbox_kind(email):
    local = email.split('@', 1)[0].split('+', 1)[0]
    return 'role' if local in {'info', 'kontakt', 'contact', 'office', 'sales', 'support',
                              'hello', 'mail', 'service', 'verwaltung', 'buchhaltung'} else 'unspecified'


async def lookup_company_emails(company, state, mode='quick'):
    if mode not in ('quick', 'thorough'):
        raise ValueError('Invalid email search mode')
    domain = (company.domain or urlparse(company.website).hostname or '').lower().removeprefix('www.')
    if not domain:
        from harvey.lookup_diagnostics import diagnostic
        return {'status': 'no_website', 'found': 0, 'diagnostics':[diagnostic('lookup','no_website')]}
    from harvey.lookup_diagnostics import diagnostic
    diagnostics=[]
    visited, found, reachable = set(), set(), False
    async with httpx.AsyncClient(timeout=6 if mode == 'thorough' else 10, follow_redirects=False,
                                 headers={'User-Agent': 'Siveron public contact lookup'}) as client:
        from harvey.collectors.public_pages import PublicPageReader
        from harvey.collectors.structured_company import save_structured_fields
        reader = PublicPageReader(client, lambda url: _public_company_url(url, domain))
        async def safe_read(url):
            nonlocal reachable
            page = await reader.read(url)
            diagnostics.extend(page.diagnostics)
            reachable = reachable or bool(page.html)
            await save_structured_fields(state, company, page.html, page.url)
            return page.html, page.url

        site = company.website or f'https://{domain}'
        html, source = await safe_read(site)
        if not html:
            host = ('www.' + domain) if urlparse(site).hostname == domain else domain
            html, source = await safe_read(f'https://{host}')
        pages = [(html, source)]
        def relevant(body, url):
            return relevant_company_emails(extract_public_emails(body, url), domain,
                                           html=body, source=url, company_name=company.name)
        evidence = [(source, relevant(html, source))]
        # Quick stops as soon as an official address is available; thorough
        # reads the remaining selected sections to find additional mailboxes.
        if html and (mode == 'thorough' or not evidence[0][1]):
            for link in contact_page_links(html, source, domain, mode):
                body, url = await safe_read(link)
                pages.append((body,url))
                emails = relevant(body,url)
                evidence.append((url,emails))
                if emails and mode == 'quick': break
        if reachable and not any(emails for _, emails in evidence):
            targets = [(body,url) for body,url in pages if body]
            if mode == 'quick': targets = targets[-1:]
            else: targets = targets[:2]
            for _,target in targets:
                rendered, url = await render_contact_page(target, domain)
                if not rendered:diagnostics.append(diagnostic('browser','browser_unavailable',url,retryable=True))
                await save_structured_fields(state, company, rendered, url)
                pages.append((rendered,url))
                emails = relevant(rendered,url)
                evidence.append((url,emails))
                if emails: break
        profiles = {}
        for body,url in pages:
            for profile in social_profile_links(body,url):
                profiles.setdefault(profile['url'],profile)
        if profiles:
            await state.save_company_social_profiles(company.id, list(profiles.values())[:12])
        by_domain = {email.rsplit('@', 1)[-1]: email for _, emails in evidence for email in emails}
        tasks = {domain: asyncio.create_task(check_email_domain(email)) for domain, email in by_domain.items()}
        domain_checks = {}
        if tasks:
            # DNS evidence is optional: never lose found addresses due to slow DNS.
            done, pending = await asyncio.wait(tasks.values(), timeout=3)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for mail_domain, task in tasks.items():
                domain_checks[mail_domain] = task.result() if task in done and not task.exception() else 'unknown'
        for source, emails in evidence:
            if emails:
                checks = {email: {'syntax': 'valid', 'domain': domain_checks[email.rsplit('@', 1)[-1]],
                                  'kind': mailbox_kind(email),
                                  'association': 'official_contact_block' if email not in relevant_company_emails([email], domain) else 'website_domain_or_mailbox'} for email in emails}
                await state.save_public_company_emails(company.id, emails, source, checks)
                found.update(emails)
    return {'status': 'found' if found else 'not_found' if reachable else 'unreachable',
            'found': len(found), 'diagnostics': diagnostics[:23]+[diagnostic('extraction','found' if found else 'no_email_in_checked_pages' if reachable else 'unreachable',source)]}
