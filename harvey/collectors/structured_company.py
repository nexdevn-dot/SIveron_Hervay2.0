"""Conservative structured organization evidence, always reviewed before adoption."""
import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit

import extruct
from harvey.lookup_diagnostics import diagnostic

ORG_TYPES = {'Organization', 'LocalBusiness', 'Corporation', 'ProfessionalService',
             'MedicalBusiness', 'HomeAndConstructionBusiness', 'GeneralContractor',
             'Store', 'LegalService', 'Dentist', 'MedicalClinic', 'RealEstateAgent',
             'AutoRepair', 'Restaurant', 'Hotel', 'LodgingBusiness'}


def extract_company_fields(html, source, domain, company_name):
    try:
        data = extruct.extract(html, base_url=source, syntaxes=['json-ld', 'microdata'], errors='ignore')
    except (ValueError, TypeError, RecursionError):
        return []
    nodes, pending = [], [data]
    for _ in range(5000):
        if not pending:
            break
        value = pending.pop()
        if isinstance(value, list):
            pending.extend(value[:1000])
        elif isinstance(value, dict):
            nodes.append(value)
            pending.extend(v for v in value.values() if isinstance(v, (dict, list)))
    def identifier(value):
        try:
            return urljoin(source, value) if isinstance(value, str) else ''
        except ValueError:
            return ''
    index, ambiguous = {}, set()
    for node in nodes:
        key = node.get('@id', node.get('id'))
        if isinstance(key, str):
            full = identifier(key)
            # A reference is not another declaration. Conflicting full declarations are skipped.
            if full in index and len(node)>1 and len(index[full])>1 and node!=index[full]:
                ambiguous.add(full)
            elif full not in index or len(node)>len(index[full]):
                index[full]=node
    def resolve(value):
        if isinstance(value, dict):
            key = value.get('@id', value.get('id'))
            full = identifier(key)
            if full in ambiguous:
                return {}
            target = index.get(full)
            return target or value
        return value
    def props(value):
        value = resolve(value)
        result = value.get('properties', value) if isinstance(value, dict) else {}
        return result if isinstance(result, dict) else {}
    def scalars(value):
        result, stack = [], [value]
        for _ in range(1000):
            if not stack:
                break
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(reversed(item[:30]))
            elif isinstance(item, str) and item.strip():
                result.append(item.strip()[:500].encode('utf-8', errors='replace').decode('utf-8'))
        return result
    def first(value):
        values = scalars(value)
        return values[0] if values else ''
    def norm(value):
        return re.sub(r'\W+', '', value.casefold())
    def same_site(value):
        try:
            return (urlsplit(urljoin(source,value)).hostname or '').lower().removeprefix('www.') == domain
        except ValueError:
            return False
    clean_source = diagnostic('extraction', 'found', source)['source']
    found = {}
    for node in nodes:
        types = scalars(node.get('@type', node.get('type', [])))
        if not any(t.rstrip('/').rsplit('/', 1)[-1].rsplit('#', 1)[-1] in ORG_TYPES for t in types):
            continue
        p = props(node)
        if not p:
            continue
        name = first(p.get('name', ''))
        urls = scalars(p.get('url', []))
        same_host = any(same_site(u) for u in urls)
        same_name = bool(name and company_name and norm(name) == norm(company_name))
        if not (same_name or same_host):
            continue
        entity = first(node.get('@id', node.get('id', ''))) or name or 'Organization'
        def add(field, value, label=''):
            value = value.strip()[:500]
            if not value:
                return
            key = hashlib.sha256(json.dumps([field, value, clean_source, entity, label], ensure_ascii=False).encode()).hexdigest()[:32]
            found[key] = dict(id=key, field=field, value=value, source_url=clean_source,
                              entity=name or entity, contact_label=label, method='extruct')
        def contacts(p, label=''):
            for phone in scalars(p.get('telephone', [])):
                if 6 <= len(re.sub(r'\D', '', phone)) <= 20:
                    add('phone', phone, label)
            from harvey.collectors.company_contacts import normalize_email
            for email in scalars(p.get('email', [])):
                address = normalize_email(email.removeprefix('mailto:').split('?', 1)[0])
                if address:
                    add('email', address, label)
        contacts(p)
        addresses = p.get('address', [])
        for address in addresses if isinstance(addresses, list) else [addresses]:
            a = props(address)
            country = a.get('addressCountry', '')
            if isinstance(country, dict):
                country = props(country).get('name', '')
            text = ', '.join(filter(None, [first(a.get('streetAddress', '')),
                ' '.join(filter(None, [first(a.get('postalCode', '')), first(a.get('addressLocality', ''))])),
                first(a.get('addressRegion', '')), first(country)]))
            if text:
                add('location', text)
        points = p.get('contactPoint', [])
        for point in points if isinstance(points, list) else [points]:
            c = props(point)
            contacts(c, first(c.get('contactType', '')))
    return list(found.values())[:40]


async def save_structured_fields(state, company, html, source):
    if not html:
        return
    domain = (company.domain or urlsplit(company.website).hostname or '').lower().removeprefix('www.')
    fields = extract_company_fields(html, source, domain, company.name)
    if fields:
        async with state._connect() as db:
            for item in fields:
                key = hashlib.sha256((company.id + item['id']).encode()).hexdigest()[:32]
                await db.execute('''INSERT INTO company_field_candidates
                    (id,company_id,field,value,source_url,entity,contact_label,method)
                    VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET checked_at=CURRENT_TIMESTAMP''',
                    (key, company.id, item['field'], item['value'], item['source_url'],
                     item['entity'], item['contact_label'], item['method']))
            await db.commit()
