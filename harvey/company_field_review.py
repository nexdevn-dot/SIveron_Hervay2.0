"""Explicit field adoption without contact creation, verification or send changes."""
import aiosqlite
from fastapi import Request
from fastapi.responses import JSONResponse


def install_field_review_routes(app, state_factory):
    @app.post('/api/company-field-candidates/{candidate_id}/review')
    async def review(candidate_id: str, request: Request):
        try:
            body = await request.json()
            if not isinstance(body, dict) or body.get('action') not in ('accept', 'dismiss'):
                raise ValueError()
            expected = body.get('expected_value')
            if not isinstance(expected, str) or len(expected) > 2000:
                raise ValueError()
        except (ValueError, TypeError):
            return JSONResponse({'error':'Invalid review'}, status_code=422)
        state = state_factory()
        await state.init_db()
        async with state._connect() as db:
            db.row_factory = aiosqlite.Row
            await db.execute('BEGIN IMMEDIATE')
            row = await (await db.execute('''SELECT f.*,c.phone AS current_phone,c.location AS current_location
                FROM company_field_candidates f JOIN companies c ON c.id=f.company_id
                WHERE f.id=? AND c.removed_at IS NULL''', (candidate_id,))).fetchone()
            if not row:
                return JSONResponse({'error':'Candidate unavailable'}, status_code=404)
            d = dict(row)
            status = 'accepted' if body['action']=='accept' else 'dismissed'
            if d['status'] != 'pending':
                return JSONResponse({'error':'Already reviewed; reopen profile'}, status_code=409)
            field = d['field']
            if field not in ('phone', 'location', 'email'):
                return JSONResponse({'error':'Unsupported field'}, status_code=422)
            if status == 'accepted':
                current = (d['current_'+field] or '') if field in ('phone','location') else ''
                if current != expected:
                    return JSONResponse({'error':'Value changed; reopen profile'}, status_code=409)
                if field in ('phone', 'location'):
                    await db.execute(f'UPDATE companies SET {field}=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', (d['value'], d['company_id']))
                else:
                    from harvey.collectors.company_contacts import normalize_email
                    email = normalize_email(d['value'])
                    if not email:
                        return JSONResponse({'error':'Email invalid'}, status_code=422)
                    await db.execute('''INSERT INTO company_public_emails(company_id,email,source_url)
                        VALUES (?,?,?) ON CONFLICT(company_id,email) DO NOTHING''',
                        (d['company_id'], email, d['source_url']))
            await db.execute('UPDATE company_field_candidates SET status=? WHERE id=?', (status,candidate_id))
            await db.commit()
        return {'status':status,'company_id':d['company_id']}
