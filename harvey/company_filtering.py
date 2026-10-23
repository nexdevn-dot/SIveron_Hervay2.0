"""Server-side company filters and disjunctive facets. No browser SQL."""
import aiosqlite
from harvey.collectors.company_contacts import valid_email

BINARY = ('email','website','phone','people','profiles')
FIELDS = ('q','locations','industries',*BINARY,'source')
PERSON = "p.company_id=c.id AND p.id NOT IN (SELECT prospect_id FROM contact_trash)"
EXPRESSIONS = {
    'email': f"(EXISTS(SELECT 1 FROM company_public_emails e WHERE e.company_id=c.id AND valid_company_email(e.email)) OR EXISTS(SELECT 1 FROM prospects p WHERE {PERSON} AND valid_company_email(p.email) AND COALESCE(p.email_status,'')!='invalid'))",
    'website': "(TRIM(COALESCE(c.website,''))!='' OR TRIM(COALESCE(c.domain,''))!='')",
    'phone': f"(TRIM(COALESCE(c.phone,''))!='' OR EXISTS(SELECT 1 FROM prospects p WHERE {PERSON} AND TRIM(COALESCE(p.phone,''))!=''))",
    'people': f"EXISTS(SELECT 1 FROM prospects p WHERE {PERSON} AND p.contact_type='person' AND TRIM(COALESCE(p.first_name,'')||COALESCE(p.last_name,''))!='')",
    'profiles': "EXISTS(SELECT 1 FROM company_social_profiles s WHERE s.company_id=c.id)",
}


def validate_filters(raw):
    if not isinstance(raw,dict) or set(raw)-set(FIELDS):
        raise ValueError('Invalid company filters')
    result = {}
    for key in FIELDS:
        value=raw.get(key,[] if key in ('locations','industries') else '')
        if key in ('locations','industries'):
            if not isinstance(value,list) or len(value)>50 or any(not isinstance(v,str) or not v.strip() or len(v)>1000 for v in value):
                raise ValueError('Choose at most 50 locations or industries')
            result[key]=list(dict.fromkeys(value))
        else:
            if not isinstance(value,str) or len(value)>(200 if key=='q' else 1000):
                raise ValueError('Invalid company filter value')
            if key in BINARY and value not in ('','with','without'):
                raise ValueError('Invalid company filter value')
            result[key]=value.strip()
    return result


def where(filters, exclude=None):
    clauses=['c.removed_at IS NULL']; params=[]
    for key,value in filters.items():
        if key==exclude or not value: continue
        if key=='q':
            columns=('c.name','c.domain','c.industry','c.location','c.phone')
            terms=[f'company_contains({c},?)' for c in columns]
            params.extend([value]*len(columns))
            terms += ["EXISTS(SELECT 1 FROM company_public_emails e WHERE e.company_id=c.id AND valid_company_email(e.email) AND company_contains(e.email,?))",
                      f"EXISTS(SELECT 1 FROM prospects p WHERE {PERSON} AND valid_company_email(p.email) AND COALESCE(p.email_status,'')!='invalid' AND company_contains(p.email,?))"]
            params.extend([value,value]);clauses.append('('+' OR '.join(terms)+')')
        elif key in ('locations','industries'):
            column='location' if key=='locations' else 'industry'
            clauses.append(f"c.{column} IN ({','.join('?' for _ in value)})");params.extend(value)
        elif key in BINARY:
            clauses.append(('NOT ' if value=='without' else '')+'('+EXPRESSIONS[key]+')')
        elif key=='source':
            clauses.append('c.source=?');params.append(value)
    return ' WHERE '+' AND '.join(clauses),params


async def page_data(path, page, filters):
    async with aiosqlite.connect(str(path)) as db:
        db.row_factory=aiosqlite.Row
        await db.create_function('valid_company_email',1,lambda v:int(valid_email(v or '')),deterministic=True)
        await db.create_function('company_contains',2,lambda value,needle:int(needle.casefold() in (value or '').casefold()),deterministic=True)
        await db.execute('BEGIN')
        clause,params=where(filters)
        total=(await (await db.execute('SELECT COUNT(*) FROM companies c'+clause,params)).fetchone())[0]
        pages=max(1,(total+29)//30);page=min(page,pages)
        rows=await (await db.execute(
            'SELECT c.*, (SELECT COUNT(*) FROM prospects p WHERE '+PERSON+') AS contact_count FROM companies c'+clause+
            ' ORDER BY c.created_at DESC,c.id ASC LIMIT 30 OFFSET ?',(*params,(page-1)*30))).fetchall()
        facets={};options={}
        for key,column in (('locations','location'),('industries','industry'),('source','source')):
            # Options span the inventory; counts honour all OTHER filters.
            values=[r[0] for r in await (await db.execute(f"SELECT DISTINCT {column} FROM companies WHERE removed_at IS NULL AND TRIM(COALESCE({column},''))!='' ORDER BY {column} COLLATE NOCASE")).fetchall()]
            clause,params=where(filters,key)
            counts={r[0]:r[1] for r in await (await db.execute(f'SELECT c.{column},COUNT(*) FROM companies c'+clause+f' GROUP BY c.{column}',params)).fetchall()}
            facets[key]=[{'value':v,'count':counts.get(v,0)} for v in values]
            if column != 'source': options[column]=values
        for key in BINARY:
            clause,params=where(filters,key)
            row=await (await db.execute('SELECT COUNT(*),COALESCE(SUM(CASE WHEN '+EXPRESSIONS[key]+' THEN 1 ELSE 0 END),0) FROM companies c'+clause,params)).fetchone()
            facets[key]={'with':row[1],'without':row[0]-row[1]}
        return {'items':[dict(r) for r in rows],'total':total,'page':page,'page_size':30,'pages':pages,'filters':options,'facets':facets}
