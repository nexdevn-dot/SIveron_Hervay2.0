"""Bounded official-site person discovery. Candidates require explicit adoption."""
import hashlib
import re
from urllib.parse import urljoin, urlparse

import extruct
import httpx
from bs4 import BeautifulSoup

from harvey.collectors.company_contacts import _public_company_url, normalize_email, relevant_company_emails, mailbox_kind, extract_public_emails
from harvey.collectors.profile import ProfileCollector, NON_NAME_WORDS


def extract_people(html, source, domain):
    """Only explicit Person entities or conservative name/role blocks; no email guessing."""
    found = []
    try:
        pending = [extruct.extract(html, base_url=source, syntaxes=['json-ld', 'microdata'], errors='ignore')]
    except (ValueError, TypeError, RecursionError):
        pending = []
    def scalar(value):
        if isinstance(value, list):
            value = value[0] if value else ''
        return value.strip()[:200] if isinstance(value, str) else ''
    for _ in range(10000):
        if not pending:
            break
        node = pending.pop()
        if isinstance(node, list):
            pending.extend(node)
        elif isinstance(node, dict):
            types = node.get('@type', node.get('type', []))
            types = types if isinstance(types, list) else [types]
            if any(str(t).rstrip('/').rsplit('/', 1)[-1].rsplit('#', 1)[-1] == 'Person' for t in types):
                props = node.get('properties', node)
                name = scalar(props.get('name', ''))
                first, last = scalar(props.get('givenName', '')), scalar(props.get('familyName', ''))
                if not (first and last) and len(name.split()) >= 2:
                    first, last = name.split(' ', 1)
                if first and last and not re.search(r'[@<>\d]', first + last):
                    email = normalize_email(scalar(props.get('email', '')).removeprefix('mailto:')) or ''
                    if email and (mailbox_kind(email) == 'role' or not relevant_company_emails([email], domain)):
                        email = ''
                    found.append(dict(first_name=first, last_name=last, title=scalar(props.get('jobTitle', '')),
                                      email=email, phone=scalar(props.get('telephone', ''))))
            pending.extend(v for v in node.values() if isinstance(v, (dict, list)))
    soup = BeautifulSoup(html, 'html.parser')
    for unwanted in soup(['script', 'style', 'nav', 'footer', 'header']):
        unwanted.decompose()
    role = re.compile(r'\b(geschäftsführ(?:er(?:in)?|ung)|geschaeftsfuehrer|inhaber(?:in)?|gründer(?:in)?|gruender|vorstand|prokurist(?:in)?|(?:vertriebs|team|bereichs|personal|projekt|praxis)leit(?:er(?:in)?|ung)|ansprechpartner(?:in)?|arzt|ärztin|zahnarzt|zahnärztin|leiter(?:in)?|ceo|cfo|cto|owner|founder|director|manager)\b', re.I)
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'strong']):
        name = heading.get_text(' ', strip=True)
        name = re.sub(r'^(?:(?:Prof|Dr)\.\s*|med\.\s*)+', '', name)
        parts = name.split()
        non_names = {'unser', 'unsere', 'unserem', 'team', 'kontakt', 'geschäftsführung', 'geschaeftsfuehrung', 'unternehmen', 'über', 'uns', 'die', 'ihre', 'ansprechpartner', 'mehr', 'erfahren', 'herzlich', 'willkommen', 'das', 'der', 'ein', 'eine', 'jetzt', 'online', 'termin', 'aufnehmen', 'anfragen'} | NON_NAME_WORDS
        if not parts or not parts[0][0].isupper() or not parts[-1][0].isupper() or any(p.casefold() in non_names for p in parts):
            continue
        if not 2 <= len(parts) <= 5 or any(not re.fullmatch(r"[^\W\d_][^\W\d_’'\-]*", token, re.UNICODE) for token in parts):
            continue
        # WordPress cards often wrap the name in its own paragraph. Climb only
        # small, single-name blocks; never borrow a role/email from a whole team.
        card = heading.parent
        match = None
        for _ in range(3):
            if card is None or len(card.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'strong'])) != 1:
                break
            text = card.get_text(' ', strip=True)
            if len(text) > 600:
                break
            after = text.split(heading.get_text(' ', strip=True), 1)[-1].strip()
            match = role.search(after[:120])
            if match:
                break
            card = card.parent
        if not match:
            continue
        title = match.group(0)
        sibling = heading.find_next_sibling()
        if sibling is None and heading.parent is not card:
            sibling = heading.parent.find_next_sibling()
        if sibling:
            role_text=sibling.get_text(' ',strip=True)
            if len(role_text)<=160 and role.search(role_text):title=role_text
        emails = extract_public_emails(str(card), source)
        emails = [e for e in emails if e and mailbox_kind(e) != 'role' and relevant_company_emails([e], domain)]
        phones = [a['href'][4:] for a in card.select('a[href^="tel:"]')]
        found.append(dict(first_name=parts[0], last_name=' '.join(parts[1:]), title=title,
                          email=emails[0] if len(set(emails)) == 1 else '',
                          phone=phones[0][:80] if len(set(phones)) == 1 else ''))
    # Keep email/phone empty here: a nearby mailbox may belong to a different person.
    found.extend(ProfileCollector(None).detect_people(html))
    unique = {}
    for person in found:
        key = (person['first_name'].casefold(), person['last_name'].casefold())
        unique.setdefault(key, {k: person.get(k, '') for k in ('first_name', 'last_name', 'title', 'email', 'phone')})
    return list(unique.values())[:30]


async def lookup_company_people(company, state, include_candidate_ids=False):
    domain = (company.domain or urlparse(company.website).hostname or '').lower().removeprefix('www.')
    if not domain:
        return {'status': 'no_website', 'found': 0}
    visited, candidates, reachable = set(), {}, False
    async with httpx.AsyncClient(timeout=5, follow_redirects=False,
                                 headers={'User-Agent': 'Siveron public person lookup'}) as client:
        from harvey.collectors.public_pages import PublicPageReader
        from harvey.collectors.structured_company import save_structured_fields
        reader = PublicPageReader(client, lambda url: _public_company_url(url, domain))
        async def read(url):
            nonlocal reachable
            page = await reader.read(url)
            reachable = reachable or bool(page.html)
            await save_structured_fields(state, company, page.html, page.url)
            return page.html, page.url
        html, source = await read(company.website or f'https://{domain}')
        if not html:
            html, source = await read(f'https://www.{domain}')
        links = []
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            for anchor in soup.find_all('a', href=True):
                url = urljoin(source, anchor['href']).split('#')[0]
                if re.search(r'team|über.uns|ueber.uns|about|ansprech|geschäfts|geschaefts|kontakt|contact|impressum',
                             urlparse(url).path + ' ' + anchor.get_text(' ', strip=True), re.I):
                    links.append(url)
        links.extend(urljoin(source, path) for path in ('/team', '/ueber-uns', '/kontakt', '/impressum'))
        pages = [(html, source)]
        for link in list(dict.fromkeys(links))[:4]:
            pages.append(await read(link))
        for body, url in pages:
            for person in extract_people(body, url, domain):
                key = hashlib.sha256((company.id + '\0' + person['first_name'].casefold() + '\0' + person['last_name'].casefold()).encode()).hexdigest()[:32]
                if key not in candidates:
                    candidates[key]=dict(person,source_url=url)
                elif not candidates[key].get('title') and person.get('title'):
                    # Keep fields together with their actual page evidence.
                    candidates[key]=dict(person,source_url=url)
    async with state._connect() as db:
        for key, person in candidates.items():
            await db.execute('''INSERT INTO person_candidates
                (id, company_id, first_name, last_name, title, email, phone, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,email=excluded.email,phone=excluded.phone,source_url=excluded.source_url,found_at=CURRENT_TIMESTAMP WHERE person_candidates.status='pending' ''',
                (key, company.id, person['first_name'], person['last_name'], person['title'],
                 person['email'], person['phone'], person['source_url']))
        await db.commit()
    result={'status': 'found' if candidates else 'not_found' if reachable else 'unreachable', 'found': len(candidates)}
    if include_candidate_ids:result['candidate_ids']=list(candidates)
    return result
