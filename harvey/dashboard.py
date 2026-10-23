"""Siveron Dashboard — local web UI to set up, control, and monitor Siveron."""

import asyncio
import json
import logging
import math
import os
import signal
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

import aiosqlite
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import (
    HTMLResponse, JSONResponse, PlainTextResponse, Response,
)

logger = logging.getLogger("harvey.dashboard")

from harvey.paths import PROJECT_ROOT  # noqa: E402
DB_PATH = PROJECT_ROOT / "data" / "harvey.db"
ENV_FILE = PROJECT_ROOT / ".env"
CONFIG_FILE = PROJECT_ROOT / "harvey.yaml"
PID_FILE = PROJECT_ROOT / "data" / "harvey.pid"
LOG_FILE = PROJECT_ROOT / "data" / "harvey.log"


def _resolve_config_file() -> Path:
    """harvey.local.yaml wins when present — same resolution as config.py's
    loader, so the dashboard doesn't judge setup complete against the
    tracked harvey.yaml template while the real trained config sits in the
    gitignored local override."""
    from harvey.config import _find_config_file, ConfigFileNotFoundError
    try:
        return Path(_find_config_file())
    except ConfigFileNotFoundError:
        return CONFIG_FILE

app = FastAPI(title="Siveron Dashboard")

# Siveron process tracking
_harvey_process: subprocess.Popen | None = None
_harvey_started_at: datetime | None = None
_env_lock = asyncio.Lock()


# ── Helpers ──


async def query_db(sql: str, params: tuple = ()) -> list[dict]:
    """Run a query and return results as list of dicts.

    Never raises: a missing DB file, missing table, or malformed schema
    returns [] so no dashboard route can 500 on an empty install.
    """
    if not DB_PATH.exists():
        return []
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("query_db failed (%s): %s", sql.split(None, 4)[:4], e)
        return []


def _mask_key(key: str) -> str:
    """Mask an API key for display: show first 4 and last 4 chars."""
    if not key or len(key) < 10:
        return "****" if key else ""
    return key[:4] + "****" + key[-4:]


def _read_env_file() -> dict[str, str]:
    """Read .env file and return as dict."""
    env_vars = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()
    return env_vars


def _write_env_file(updates: dict[str, str]):
    """Update .env file with new values, preserving existing entries."""
    existing = _read_env_file()
    existing.update(updates)
    lines = [f"{k}={v}" for k, v in existing.items()]
    ENV_FILE.write_text("\n".join(lines) + "\n")
    load_dotenv(str(ENV_FILE), override=True)


def _check_harvey_pid() -> int | None:
    """Check if there's a running Siveron process from a PID file."""
    global _harvey_process, _harvey_started_at
    if _harvey_process and _harvey_process.poll() is None:
        return _harvey_process.pid
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            PID_FILE.unlink(missing_ok=True)
    return None


# ── Setup Status ──


@app.get("/api/setup-status")
async def get_setup_status():
    """Check what's configured and what still needs setup."""
    checks = []

    # 1. Venv
    checks.append({
        "id": "venv", "label": "Python virtual environment",
        "done": (PROJECT_ROOT / ".venv").is_dir(),
        "required": True,
        "help": "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -e .",
    })

    # 2. Env file
    env_vars = _read_env_file()
    env_exists = ENV_FILE.exists() and bool(env_vars)
    checks.append({
        "id": "env_file", "label": "Environment file (.env)",
        "done": env_exists,
        "required": True,
        "help": "Go to the Settings tab to enter your API keys.",
    })

    # 3. Email provider configured (matches channels.email.provider)
    provider = _current_provider()

    def _has(*keys):
        return all((env_vars.get(k, "") or os.getenv(k, "")).strip() for k in keys)

    if provider == "gmail":
        provider_done = _has("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET") and \
            (PROJECT_ROOT / "data" / "gmail_token.json").is_file()
        provider_help = ("Set GMAIL_CLIENT_ID/SECRET in Settings, then run "
                         "'harvey gmail auth' in your terminal.")
    elif provider == "smtp":
        provider_done = _has("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD")
        provider_help = "Enter your SMTP host, username, and password in Settings."
    else:
        instantly_key = env_vars.get("INSTANTLY_API_KEY", "") or os.getenv("INSTANTLY_API_KEY", "")
        provider_done = bool(instantly_key) and instantly_key != "your_instantly_api_key_here"
        provider_help = "Enter your Instantly API key in Settings."
    checks.append({
        "id": "email_provider", "label": f"Email provider configured ({provider})",
        "done": provider_done,
        "required": True,
        "help": provider_help,
    })

    # 4. Optional automatic email verification; manual campaigns need no key.
    verifier_set = _has("REOON_API_KEY") or _has("ZEROBOUNCE_API_KEY") or _has("HUNTER_API_KEY")
    checks.append({
        "id": "verifier", "label": "Email verification key",
        "done": verifier_set,
        "required": False,
        "help": "Optional automatic verification. Contacts with an email can be prepared "
                "for a manual campaign and explicitly approved in the Outbox without a verification key.",
    })

    # 5. Config valid
    config_valid = False
    config_path = _resolve_config_file()
    if config_path.exists():
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f)
            company = cfg.get("persona", {}).get("company", "")
            product = cfg.get("product", {}).get("name", "")
            config_valid = company not in ("Your Company", "") and product not in ("Your Product", "")
        except Exception:
            pass
    checks.append({
        "id": "config", "label": f"Siveron configured ({config_path.name})",
        "done": config_valid,
        "required": True,
        "help": "Train Siveron on your product. Use the trainer or set up manually through Claude.",
    })

    # 6. Product trained
    product_trained = (PROJECT_ROOT / "skills" / "product_knowledge.md").exists()
    checks.append({
        "id": "product_trained", "label": "Product knowledge trained",
        "done": product_trained,
        "required": True,
        "help": "Run: harvey train https://yourwebsite.com (or set up through Claude).",
    })

    # 7. LinkedIn (optional)
    linkedin_email = env_vars.get("LINKEDIN_EMAIL", "") or os.getenv("LINKEDIN_EMAIL", "")
    linkedin_pass = env_vars.get("LINKEDIN_PASSWORD", "") or os.getenv("LINKEDIN_PASSWORD", "")
    checks.append({
        "id": "linkedin", "label": "LinkedIn credentials",
        "done": bool(linkedin_email) and bool(linkedin_pass),
        "required": False,
        "help": "Optional. Enter your LinkedIn credentials in Settings to enable LinkedIn prospecting.",
    })

    # 8. Cloudflare (optional)
    cf_id = env_vars.get("CLOUDFLARE_ACCOUNT_ID", "") or os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    cf_token = env_vars.get("CLOUDFLARE_API_TOKEN", "") or os.getenv("CLOUDFLARE_API_TOKEN", "")
    checks.append({
        "id": "cloudflare", "label": "Cloudflare deep crawling",
        "done": bool(cf_id) and bool(cf_token),
        "required": False,
        "help": "Optional. For JavaScript-rendered website crawling during training.",
    })

    required_checks = [c for c in checks if c["required"]]
    completed_required = sum(1 for c in required_checks if c["done"])

    return {
        "checks": checks,
        "completed": completed_required,
        "total_required": len(required_checks),
        "percent": int(completed_required / len(required_checks) * 100) if required_checks else 0,
    }


# ── Settings ──


def _current_provider() -> str:
    """Read channels.email.provider from the active config (best-effort)."""
    try:
        with open(_resolve_config_file()) as f:
            cfg = yaml.safe_load(f) or {}
        return ((cfg.get("channels") or {}).get("email") or {}).get("provider", "instantly")
    except Exception:
        return "instantly"


@app.get("/api/settings")
async def get_settings():
    """Get current settings — presence flags only for secrets, never raw values."""
    env_vars = _read_env_file()
    all_keys = [
        "INSTANTLY_API_KEY", "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD",
        "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN",
        "GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET",
        "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD",
        "IMAP_HOST", "IMAP_PORT", "IMAP_USERNAME", "IMAP_PASSWORD",
        "REOON_API_KEY", "ZEROBOUNCE_API_KEY", "HUNTER_API_KEY",
        "GEOAPIFY_API_KEY", "SERPAPI_API_KEY",
    ]
    for key in all_keys:
        if key not in env_vars:
            env_vars[key] = os.getenv(key, "")

    def is_set(k):
        return bool((env_vars.get(k) or "").strip())

    # Gmail is authorized once harvey gmail auth has stored a token file.
    gmail_token = (PROJECT_ROOT / "data" / "gmail_token.json").is_file()

    return {
        "provider": _current_provider(),
        # Non-secret values echo back so fields repopulate; secrets are
        # presence-only so keys never leave the box.
        "instantly_api_key_set": is_set("INSTANTLY_API_KEY"),
        "linkedin_email": env_vars.get("LINKEDIN_EMAIL", ""),
        "linkedin_password_set": is_set("LINKEDIN_PASSWORD"),
        "cloudflare_account_id": env_vars.get("CLOUDFLARE_ACCOUNT_ID", ""),
        "cloudflare_api_token_set": is_set("CLOUDFLARE_API_TOKEN"),
        "gmail_client_id": env_vars.get("GMAIL_CLIENT_ID", ""),
        "gmail_client_secret_set": is_set("GMAIL_CLIENT_SECRET"),
        "gmail_authorized": gmail_token,
        "smtp_host": env_vars.get("SMTP_HOST", ""),
        "smtp_port": env_vars.get("SMTP_PORT", ""),
        "smtp_username": env_vars.get("SMTP_USERNAME", ""),
        "smtp_password_set": is_set("SMTP_PASSWORD"),
        "imap_host": env_vars.get("IMAP_HOST", ""),
        "imap_port": env_vars.get("IMAP_PORT", ""),
        "imap_username": env_vars.get("IMAP_USERNAME", ""),
        "imap_password_set": is_set("IMAP_PASSWORD"),
        "reoon_api_key_set": is_set("REOON_API_KEY"),
        "zerobounce_api_key_set": is_set("ZEROBOUNCE_API_KEY"),
        "hunter_api_key_set": is_set("HUNTER_API_KEY"),
        "geoapify_api_key_set": is_set("GEOAPIFY_API_KEY"),
        "serpapi_api_key_set": is_set("SERPAPI_API_KEY"),
    }


@app.post("/api/settings/env")
async def save_env_settings(request: Request):
    """Save environment variables to .env file."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"success": False, "message": "Invalid request body."}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({"success": False, "message": "Invalid request body."}, status_code=400)
    async with _env_lock:
        updates = {}
        for key in ["INSTANTLY_API_KEY", "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD",
                     "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN",
                     "GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET",
                     "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD",
                     "IMAP_HOST", "IMAP_PORT", "IMAP_USERNAME", "IMAP_PASSWORD",
                     "REOON_API_KEY", "ZEROBOUNCE_API_KEY", "HUNTER_API_KEY",
                     "GEOAPIFY_API_KEY", "SERPAPI_API_KEY", "SERPER_API_KEY"]:
            if key in data and data[key] is not None:
                # Strip newlines so a crafted value can't inject extra .env entries
                updates[key] = str(data[key]).replace("\n", " ").replace("\r", " ").strip()
        if updates:
            try:
                _write_env_file(updates)
            except Exception as e:
                logger.warning("Failed to write .env: %s", e)
                return {"success": False, "message": "Could not write .env file."}
    return {"success": True}


@app.post("/api/settings/test-instantly")
async def test_instantly(request: Request):
    """Test an Instantly API key."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    api_key = str(data.get("api_key", "") or "")
    if not api_key:
        return {"success": False, "message": "No API key provided."}
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.instantly.ai/api/v2/accounts",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 200:
                return {"success": True, "message": "Connected to Instantly."}
            else:
                return {"success": False, "message": f"API returned {resp.status_code}. Check your key."}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


# ── Companies ──


@app.get("/api/companies")
async def get_companies():
    """Companies plus known contact details; reading never crawls sites."""
    state = _state()
    await state.init_db()
    rows = await query_db("""
        SELECT c.*,
            (SELECT COUNT(*) FROM prospects p WHERE p.company_id = c.id AND p.id NOT IN (SELECT prospect_id FROM contact_trash)) as contact_count
        FROM companies c WHERE c.removed_at IS NULL ORDER BY c.created_at DESC LIMIT 200
    """)
    return await _company_contact_details(rows)


async def _company_contact_details(rows, include_validation=False):
    """Attach the same known, valid addresses to list and paginated views."""
    if not rows:
        return rows
    from harvey.collectors.company_contacts import valid_email
    by_id = {row['id']: row for row in rows}
    for row in rows:
        row['contact_emails'], row['contact_phones'], row['social_profiles'] = [], [], []
        if row.get('phone'):
            row['contact_phones'].append(row['phone'])
    placeholders = ','.join('?' for _ in rows)
    people = await query_db(
        f"SELECT company_id, email, email_status, email_verified, source_url, phone "
        f"FROM prospects WHERE id NOT IN (SELECT prospect_id FROM contact_trash) AND company_id IN ({placeholders}) "
        f"ORDER BY (email_verified = 1 OR email_status = 'verified') DESC, score DESC",
        tuple(by_id))
    public = await query_db(
        f"SELECT company_id, email, source_url, found_at, checked_at, validation_json FROM company_public_emails WHERE company_id IN ({placeholders})",
        tuple(by_id))
    socials = await query_db(f"SELECT company_id,url,network,source_url FROM company_social_profiles WHERE company_id IN ({placeholders})", tuple(by_id))
    for profile in socials:
        by_id[profile['company_id']]['social_profiles'].append(profile)
    for item in people + public:
        row = by_id[item['company_id']]
        email = (item.get('email') or '').strip().lower()
        if valid_email(email) and item.get('email_status') != 'invalid':
            status = 'verified' if item.get('email_verified') else item.get('email_status') or 'unverified'
            if not any(entry['email'] == email for entry in row['contact_emails']):
                entry = {'email': email, 'status': status, 'source_url': item.get('source_url') or ''}
                if include_validation:
                    entry.update(found_at=item.get('found_at'), checked_at=item.get('checked_at'),
                                 validation=json.loads(item.get('validation_json') or '{}'))
                row['contact_emails'].append(entry)
        if item.get('phone') and item['phone'] not in row['contact_phones']:
            row['contact_phones'].append(item['phone'])
    return rows


@app.get('/api/companies/page')
async def get_company_page(
    page: int = Query(1, ge=1), q: str = Query('', max_length=200),
    location: str = Query('', max_length=300), industry: str = Query('', max_length=1000),
    locations: list[str] = Query(default=[]), industries: list[str] = Query(default=[]),
    email: str = Query('', pattern='^(|with|without)$'),
    website: str = Query('', pattern='^(|with|without)$'),
    phone: str = Query('', pattern='^(|with|without)$'),
    people: str = Query('', pattern='^(|with|without)$'),
    profiles: str = Query('', pattern='^(|with|without)$'),
    source: str = Query('', max_length=1000),
):
    from harvey.company_filtering import validate_filters, page_data
    try:
        filters=validate_filters({'q':q,'locations':locations or ([location] if location else []),
            'industries':industries or ([industry] if industry else []),
            'email':email,'website':website,'phone':phone,'people':people,'profiles':profiles,'source':source})
    except ValueError as exc:
        return JSONResponse({'error':str(exc)},status_code=422)
    state=_state(); await state.init_db()
    data=await page_data(DB_PATH,page,filters)
    data['items']=await _company_contact_details(data['items'],include_validation=True)
    return data


@app.get('/api/company-filter-views')
async def get_company_filter_views():
    state=_state(); await state.init_db()
    async with state._connect() as db:
        db.row_factory=aiosqlite.Row
        rows=await (await db.execute('SELECT id,name,filters_json FROM company_filter_views ORDER BY name COLLATE NOCASE,id')).fetchall()
    return [{'id':r['id'],'name':r['name'],'filters':json.loads(r['filters_json'])} for r in rows]


@app.post('/api/company-filter-views')
async def save_company_filter_view(request: Request):
    from harvey.company_filtering import validate_filters
    try:
        body=await request.json()
        name=body.get('name') if isinstance(body,dict) else None
        if not isinstance(name,str) or not 1 <= len(name.strip()) <= 60:
            raise ValueError('View name must contain 1–60 characters')
        filters=validate_filters(body.get('filters'))
    except (ValueError,TypeError) as exc:
        return JSONResponse({'error':str(exc)},status_code=422)
    state=_state();await state.init_db();ident=uuid.uuid4().hex
    async with state._connect() as db:
        await db.execute('BEGIN IMMEDIATE')
        if (await (await db.execute('SELECT COUNT(*) FROM company_filter_views')).fetchone())[0]>=30:
            return JSONResponse({'error':'At most 30 saved views are allowed'},status_code=422)
        duplicate=await (await db.execute('SELECT id FROM company_filter_views WHERE name=? COLLATE NOCASE',(name.strip(),))).fetchone()
        if duplicate:
            return JSONResponse({'error':'A view with this name already exists'},status_code=409)
        await db.execute('INSERT INTO company_filter_views(id,name,filters_json) VALUES(?,?,?)',(ident,name.strip(),json.dumps(filters)))
        await db.commit()
    return {'id':ident,'name':name.strip(),'filters':filters}


@app.delete('/api/company-filter-views/{view_id}')
async def delete_company_filter_view(view_id: str):
    state=_state();await state.init_db()
    async with state._connect() as db:
        cursor=await db.execute('DELETE FROM company_filter_views WHERE id=?',(view_id,))
        await db.commit()
    return JSONResponse({'success':True}) if cursor.rowcount else JSONResponse({'error':'View not found'},status_code=404)


@app.get('/api/companies/{company_id}/profile')
async def get_company_profile(company_id: str):
    """Read an exact stored company; never triggers research or modifies selection."""
    state = _state()
    await state.init_db()
    rows = await query_db('SELECT * FROM companies WHERE id=? AND removed_at IS NULL', (company_id,))
    if not rows:
        return JSONResponse({'error': 'Company unavailable'}, status_code=404)
    company = (await _company_contact_details(rows, include_validation=True))[0]
    contacts = await get_company_contacts(company_id)
    candidates = await query_db("SELECT * FROM company_field_candidates WHERE company_id=? AND status='pending' ORDER BY checked_at DESC,id LIMIT 100", (company_id,))
    for item in candidates:
        item['current_value'] = (company.get(item['field']) or '') if item['field'] in ('phone','location') else ''
    candidates = [item for item in candidates if item['value'] != item['current_value']]
    return {'company': company, 'contacts': contacts, 'field_candidates': candidates}


@app.post('/api/companies/remove-selected')
async def remove_selected_companies(request: Request):
    try:
        body = await request.json()
        ids = body.get('company_ids') if isinstance(body, dict) else None
        if not isinstance(ids, list) or not 1 <= len(ids) <= 1000 or any(not isinstance(i, str) or not i.strip() or len(i) > 100 for i in ids):
            raise ValueError()
    except (ValueError, TypeError):
        return JSONResponse({'error': 'Choose between 1 and 1000 company IDs'}, status_code=422)
    if _company_contact_lookups:
        return JSONResponse({'status': 'busy', 'removed': 0}, status_code=409)
    state = _state()
    await state.init_db()
    result = await state.remove_selected_companies(list(dict.fromkeys(ids)))
    return JSONResponse(result, status_code=409 if result['status'] == 'busy' else 200)


@app.post('/api/companies/cleanup')
async def cleanup_companies(request: Request):
    company_ids = None
    if await request.body():
        try:
            payload = await request.json()
            if not isinstance(payload, dict) or set(payload) != {'company_ids'}:
                raise ValueError()
            company_ids = payload['company_ids']
            if not isinstance(company_ids, list) or not 1 <= len(company_ids) <= 1000 or any(not isinstance(cid, str) or not cid or len(cid)>100 for cid in company_ids):
                raise ValueError()
            company_ids = list(dict.fromkeys(company_ids))
        except (ValueError, TypeError):
            return JSONResponse({'error':'Invalid company selection'}, status_code=422)
    state = _state()
    await state.init_db()
    if _company_contact_lookups:
        return JSONResponse({'status': 'busy', 'removed': 0}, status_code=409)
    result = await state.cleanup_unreachable_companies(company_ids)
    return JSONResponse(result, status_code=409 if result['status'] == 'busy' else 200)


@app.post('/api/companies/cleanup/{batch_id}/restore')
async def restore_company_cleanup(batch_id: str):
    if len(batch_id) != 32 or any(char not in '0123456789abcdef' for char in batch_id):
        return JSONResponse({'error': 'Invalid cleanup batch'}, status_code=422)
    state = _state()
    await state.init_db()
    return {'restored': await state.restore_company_cleanup(batch_id)}


_company_contact_lookups = set()


_contact_jobs = None


def _company_email_jobs():
    global _contact_jobs
    from harvey.collectors.contact_jobs import ContactJobs
    if _contact_jobs is None or str(_contact_jobs.state.db_path) != str(DB_PATH):
        _contact_jobs = ContactJobs(_state())
    return _contact_jobs


@app.post('/api/company-email-jobs')
async def create_company_email_job(request: Request):
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse({'error': 'Invalid JSON'}, status_code=422)
    ids = payload.get('company_ids') if isinstance(payload, dict) else None
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 1000 or
            any(not isinstance(value, str) or not value or len(value) > 100 for value in ids)):
        return JSONResponse({'error': 'Choose between 1 and 1000 companies'}, status_code=422)
    service = _company_email_jobs()
    await service.state.init_db()
    for company_id in set(ids):
        if not await service.state.get_company(company_id):
            return JSONResponse({'error': 'Company not found'}, status_code=404)
    mode = payload.get('mode','quick')
    if mode not in ('quick','thorough'):
        return JSONResponse({'error':'Invalid email search mode'}, status_code=422)
    job_id = await service.create(ids, mode=mode)
    if job_id is None:
        return JSONResponse({'error': 'A public email search is already running'}, status_code=409)
    return await service.snapshot(job_id)


@app.post('/api/company-email-jobs/{job_id}/retry')
async def retry_company_email_job(job_id:str):
    service=_company_email_jobs()
    await service.state.init_db()
    if not await service.retry(job_id):
        return JSONResponse({'error':'No retry available. Wait 60 seconds; only transient failures from a completed job can retry, up to two times.'},status_code=409)
    return await service.snapshot(job_id)


@app.get('/api/company-email-jobs/latest')
async def latest_company_email_job():
    return await _company_email_jobs().snapshot()


@app.post('/api/company-email-jobs/{job_id}/stop')
async def stop_company_email_job(job_id: str):
    service = _company_email_jobs()
    if not await service.snapshot(job_id):
        return JSONResponse({'error': 'Job not found'}, status_code=404)
    await service.stop(job_id)
    return await service.snapshot(job_id)


@app.post('/api/companies/{company_id}/lookup-contacts')
async def lookup_company_contacts(company_id: str, request: Request):
    """Explicit bounded website lookup; no verification, contacts or sending."""
    if company_id in _company_contact_lookups or len(_company_contact_lookups) >= 3:
        return JSONResponse({'status': 'busy'}, status_code=409)
    state = _state()
    await state.init_db()
    company = await state.get_company(company_id)
    if company is None:
        return JSONResponse({'status': 'not_found'}, status_code=404)
    from harvey.collectors.company_contacts import lookup_company_emails
    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    mode = payload.get('mode','quick') if isinstance(payload,dict) else None
    if mode not in ('quick','thorough'):
        return JSONResponse({'error':'Invalid email search mode'},status_code=422)
    _company_contact_lookups.add(company_id)
    try:
        return await asyncio.wait_for(lookup_company_emails(company, state, **({'mode':mode} if mode != 'quick' else {})), timeout=80 if mode == 'thorough' else 25)
    except Exception as error:
        logger.info('Company contact lookup unavailable for company %s', company_id)
        from harvey.lookup_diagnostics import diagnostic
        return {'status':'unreachable','found':0,'diagnostics':[diagnostic('lookup','timeout' if isinstance(error,TimeoutError) else 'lookup_failed',retryable=True)]}
    finally:
        _company_contact_lookups.discard(company_id)


@app.get("/api/companies/{company_id}/contacts")
async def get_company_contacts(company_id: str):
    """Get all contacts for a specific company."""
    rows = await query_db(
        "SELECT * FROM prospects WHERE company_id = ? AND id NOT IN (SELECT prospect_id FROM contact_trash) ORDER BY score DESC",
        (company_id,),
    )
    return rows


# Explicit person discovery and contact creation, independent of agent prospecting.
_people_jobs = None


def _company_people_jobs():
    global _people_jobs
    from harvey.collectors.contact_jobs import ContactJobs
    if _people_jobs is None or str(_people_jobs.state.db_path) != str(DB_PATH):
        _people_jobs = ContactJobs(_state(), kind='people')
    return _people_jobs


@app.post('/api/company-people-jobs')
async def create_company_people_job(request: Request):
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse({'error': 'Ungültige Anfrage.'}, status_code=422)
    ids = payload.get('company_ids') if isinstance(payload, dict) else None
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 1000 or
            any(not isinstance(v, str) or not v or len(v) > 100 for v in ids)):
        return JSONResponse({'error': 'Bitte 1 bis 1000 Unternehmen auswählen.'}, status_code=422)
    service = _company_people_jobs()
    await service.state.init_db()
    async with service.state._connect() as db:
        for company_id in set(ids):
            row = await (await db.execute('SELECT id FROM companies WHERE id=? AND removed_at IS NULL', (company_id,))).fetchone()
            if not row:
                return JSONResponse({'error': 'Ein Unternehmen ist nicht mehr verfügbar.'}, status_code=404)
    chosen = payload.get('decision_makers')
    if chosen is not None:
        try:
            from harvey.decision_makers import criteria
            chosen=criteria(chosen)
        except (ValueError,TypeError):
            return JSONResponse({'error':'Bitte gültige Zielrollen auswählen.'},status_code=422)
    job_id = await service.create(ids,people_criteria=chosen)
    if not job_id:
        return JSONResponse({'error': 'Es läuft bereits eine Suche nach Ansprechpersonen.'}, status_code=409)
    return await service.snapshot(job_id)


@app.get('/api/company-people-jobs/latest')
async def latest_company_people_job():
    return await _company_people_jobs().snapshot()


@app.post('/api/company-people-jobs/{job_id}/stop')
async def stop_company_people_job(job_id: str):
    service = _company_people_jobs()
    if not await service.snapshot(job_id):
        return JSONResponse({'error': 'Suche nicht gefunden.'}, status_code=404)
    await service.stop(job_id)
    return await service.snapshot(job_id)


@app.get('/api/person-candidates')
async def get_person_candidates(job_id: str = '', company_id: str = ''):
    state = _state()
    await state.init_db()
    return await query_db('''SELECT p.*, c.name AS company FROM person_candidates p
        JOIN companies c ON c.id=p.company_id WHERE p.status='pending' AND c.removed_at IS NULL
        AND (?='' OR p.company_id=?) AND (?='' OR EXISTS
          (SELECT 1 FROM company_people_job_items j WHERE j.company_id=p.company_id AND j.job_id=?))
        ORDER BY p.found_at DESC, p.id''', (company_id, company_id, job_id, job_id))


@app.post('/api/contacts')
async def add_manual_contact(request: Request):
    return await _save_explicit_contact(request)


@app.post('/api/person-candidates/{candidate_id}/accept')
async def accept_person_candidate(candidate_id: str, request: Request):
    return await _save_explicit_contact(request, candidate_id)


async def _save_explicit_contact(request, candidate_id=None):
    from harvey.contacts import create_contact, ContactError
    state = _state()
    await state.init_db()
    try:
        payload = await request.json()
        return await create_contact(state, payload, candidate_id)
    except (ValueError, ContactError) as error:
        return JSONResponse({'error': str(error)}, status_code=422)


@app.post('/api/person-candidates/{candidate_id}/dismiss')
async def dismiss_person_candidate(candidate_id: str):
    state = _state()
    await state.init_db()
    async with state._connect() as db:
        cursor = await db.execute("UPDATE person_candidates SET status='dismissed' WHERE id=? AND status='pending'", (candidate_id,))
        await db.commit()
    return {'dismissed': bool(cursor.rowcount)}


@app.get('/api/contact-company-options')
async def contact_company_options(q: str = Query('', max_length=200)):
    state = _state()
    await state.init_db()
    return await query_db('''SELECT id, name, phone, website FROM companies
        WHERE removed_at IS NULL AND instr(lower(name), lower(?)) > 0
        ORDER BY name COLLATE NOCASE LIMIT 100''', (q,))


# ── Feedback ──


@app.post("/api/feedback")
async def add_feedback(request: Request):
    """Add a comment/feedback on any entity."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    entity_type = str(data.get("entity_type", "") or "")[:50]
    entity_id = str(data.get("entity_id", "") or "")[:100]
    comment = str(data.get("comment", "") or "").strip()[:4000]
    if not comment:
        return {"success": False, "message": "Comment is required."}
    feedback_id = uuid.uuid4().hex[:12]
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            # Ensure the table exists so feedback works even on a fresh install
            await db.execute(
                """CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT,
                    entity_id TEXT,
                    comment TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )"""
            )
            await db.execute(
                "INSERT INTO feedback (id, entity_type, entity_id, comment) VALUES (?, ?, ?, ?)",
                (feedback_id, entity_type, entity_id, comment),
            )
            await db.commit()
    except Exception as e:
        logger.warning("Failed to save feedback: %s", e)
        return {"success": False, "message": "Could not save feedback."}
    return {"success": True, "id": feedback_id}


@app.get("/api/feedback/{entity_type}/{entity_id}")
async def get_feedback(entity_type: str, entity_id: str):
    """Get feedback for an entity."""
    rows = await query_db(
        "SELECT * FROM feedback WHERE entity_type = ? AND entity_id = ? ORDER BY created_at DESC",
        (entity_type, entity_id),
    )
    return rows


# ── Siveron Controls ──


@app.get("/api/harvey/status")
async def get_harvey_status():
    """Check if Siveron is currently running."""
    pid = _check_harvey_pid()
    started = _harvey_started_at.isoformat() if _harvey_started_at else None
    return {"running": pid is not None, "pid": pid, "started_at": started}


@app.post("/api/harvey/start")
async def start_harvey():
    """Start Siveron's heartbeat loop as a subprocess."""
    global _harvey_process, _harvey_started_at

    if _check_harvey_pid():
        return {"success": False, "message": "Siveron is already running."}

    # Ensure data dir exists
    (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)

    try:
        log_handle = open(LOG_FILE, "a")
        try:
            _harvey_process = subprocess.Popen(
                [sys.executable, "-m", "harvey", "run"],
                cwd=str(PROJECT_ROOT),
                stdout=log_handle,
                stderr=log_handle,
                start_new_session=True,
            )
        finally:
            # Child holds its own copies of the fds; don't leak ours.
            log_handle.close()
    except Exception as e:
        logger.warning("Failed to start Siveron: %s", e)
        return {"success": False, "message": f"Failed to start Siveron: {e}"}
    _harvey_started_at = datetime.now()

    # Write PID file
    try:
        PID_FILE.write_text(str(_harvey_process.pid))
    except OSError as e:
        logger.warning("Could not write PID file: %s", e)

    return {"success": True, "pid": _harvey_process.pid}


@app.post("/api/harvey/stop")
async def stop_harvey():
    """Stop the Siveron subprocess."""
    global _harvey_process, _harvey_started_at

    pid = _check_harvey_pid()
    if not pid:
        return {"success": False, "message": "Siveron is not running."}

    try:
        os.kill(pid, signal.SIGTERM)
        # Wait briefly for graceful shutdown
        for _ in range(10):
            try:
                os.kill(pid, 0)
                await asyncio.sleep(0.5)
            except ProcessLookupError:
                break
        else:
            # Force kill if still running
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    except (ProcessLookupError, PermissionError):
        pass

    _harvey_process = None
    _harvey_started_at = None
    PID_FILE.unlink(missing_ok=True)

    return {"success": True}


@app.get("/api/harvey/logs")
async def get_harvey_logs():
    """Get recent log lines."""
    if not LOG_FILE.exists():
        return {"lines": []}
    try:
        # Tail only the last 64KB so a huge log file never blocks the UI
        with open(LOG_FILE, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 65536))
            text = f.read().decode("utf-8", errors="replace")
        lines = text.strip().splitlines()[-100:]
        return {"lines": lines}
    except Exception:
        return {"lines": []}


# ── Pipeline Data (existing endpoints) ──


@app.get("/api/stats")
async def get_stats():
    """Pipeline overview stats."""
    try:
        prospects = await query_db(
            "SELECT status, COUNT(*) as count FROM prospects WHERE id NOT IN (SELECT prospect_id FROM contact_trash) GROUP BY status"
        )
        prospect_total = sum(r["count"] for r in prospects)
        prospect_map = {r["status"]: r["count"] for r in prospects}

        campaigns = await query_db(
            "SELECT status, COUNT(*) as count FROM campaigns GROUP BY status"
        )
        campaign_map = {r["status"]: r["count"] for r in campaigns}

        conversations = await query_db(
            "SELECT status, COUNT(*) as count FROM conversations GROUP BY status"
        )
        convo_map = {r["status"]: r["count"] for r in conversations}

        actions = await query_db("SELECT COUNT(*) as count FROM actions")
        action_count = actions[0]["count"] if actions else 0

        usage = await query_db(
            "SELECT claude_calls, codex_calls FROM usage_log WHERE date = date('now')"
        )
        usage_today = (usage[0]["claude_calls"] or 0) if usage else 0
        codex_today = (usage[0]["codex_calls"] or 0) if usage else 0

        return {
            "prospects": {"total": prospect_total, "by_status": prospect_map},
            "campaigns": {"total": sum(campaign_map.values()), "by_status": campaign_map},
            "conversations": {"total": sum(convo_map.values()), "by_status": convo_map},
            "actions_total": action_count,
            "claude_calls_today": usage_today,
            "codex_calls_today": codex_today,
            "brain_provider": _active_provider(),
            "brain_status": await _brain_status(),
        }
    except Exception as e:
        return {"error": str(e)}


_USAGE_SUM = (
    "COUNT(DISTINCT CASE WHEN session_id != '' THEN session_id ELSE id END) AS calls, "
    "COALESCE(SUM(input_tokens), 0) AS input_tokens, "
    "COALESCE(SUM(output_tokens), 0) AS output_tokens, "
    "COALESCE(SUM(cache_read_tokens), 0) AS cache_read_tokens, "
    "COALESCE(SUM(cache_creation_tokens), 0) AS cache_creation_tokens, "
    "ROUND(COALESCE(SUM(cost_usd), 0), 4) AS cost_usd"
)

_quota_clients: dict = {}


def _active_brain():
    """The brain config harvey.yaml selects (None if unreadable)."""
    try:
        from harvey.config import load_brain_config
        return load_brain_config()
    except Exception:
        return None


async def _brain_status() -> dict:
    """Last recorded brain health transition ({} if none): lets the
    dashboard say "Codex paused: <why>" instead of looking healthy."""
    from harvey.brain import BRAIN_STATUS_KEY, active_brain_status
    rows = await query_db("SELECT value FROM settings WHERE key = ?", (BRAIN_STATUS_KEY,))
    # Only the configured provider's health (a stale Codex pause isn't
    # Claude's).
    return active_brain_status(rows[0]["value"], _active_provider()) if rows else {}


def _active_provider() -> str:
    brain = _active_brain()
    return brain.provider if brain else ""


def _quota_client_for(provider: str, model: str = ""):
    """One cached quota reader per provider (and Codex model). Each reads
    only its own subscription, so a Claude gauge is never shown as Codex or
    vice versa, and Codex shows the bucket metering the configured model."""
    key = (provider, model if provider == "codex" else "")
    if key not in _quota_clients:
        if provider == "codex":
            from harvey.codex import CodexClient, CodexQuotaClient
            _quota_clients[key] = CodexQuotaClient(CodexClient(model=model))
        elif provider == "claude":
            from harvey.integrations.quota import QuotaClient
            _quota_clients[key] = QuotaClient()
        else:
            return None
    return _quota_clients[key]


@app.get("/api/usage")
async def get_usage(refresh: bool = False):
    """Token/cost accounting + live subscription quota for the Usage tab."""

    totals = {}
    for label, where in (
        ("today", "date(created_at) = date('now')"),
        ("week", "created_at >= datetime('now', '-7 days')"),
        ("month", "created_at >= datetime('now', '-30 days')"),
    ):
        rows = await query_db(f"SELECT {_USAGE_SUM} FROM usage_events WHERE {where}")
        totals[label] = rows[0] if rows else {}

    def grouped(expr, alias):
        return (
            f"SELECT {expr} AS {alias}, {_USAGE_SUM} FROM usage_events "
            f"WHERE created_at >= datetime('now', '-30 days') "
            f"GROUP BY {alias} ORDER BY output_tokens DESC LIMIT 25"
        )

    by_agent = await query_db(grouped("CASE WHEN agent = '' THEN 'other' ELSE agent END", "agent"))
    by_task = await query_db(grouped("CASE WHEN task = '' THEN 'other' ELSE task END", "task"))
    by_model = await query_db(grouped("CASE WHEN model = '' THEN 'unknown' ELSE model END", "model"))
    by_provider = await query_db(grouped("provider", "provider"))
    by_day = await query_db(
        f"SELECT date(created_at) AS day, {_USAGE_SUM} FROM usage_events "
        f"WHERE created_at >= datetime('now', '-30 days') "
        f"GROUP BY day ORDER BY day ASC"
    )

    brain = _active_brain()
    provider = brain.provider if brain else ""
    quota = None
    quota_checked_at = None
    try:
        client = _quota_client_for(provider, brain.model if brain else "")
        if client is not None:
            quota = await client.get_utilization(force=True) if refresh else await client.get_utilization()
            quota_checked_at = getattr(client, "checked_at", None)
    except Exception as e:
        logger.debug("Quota lookup failed: %s", e)

    return {
        "provider": provider,
        "quota": quota,
        "quota_checked_at": quota_checked_at,
        # Whose quota this is, even when it couldn't be read, so the UI shows
        # "unavailable" for the active provider instead of hiding the gauge.
        "quota_provider": provider,
        "quota_status": ("available" if quota else "unavailable") if provider else "",
        "by_provider": by_provider,
        "totals": totals,
        "by_day": by_day,
        "by_agent": by_agent,
        "by_task": by_task,
        "by_model": by_model,
    }


@app.get("/api/prospects")
async def get_prospects():
    rows = await query_db("SELECT * FROM prospects WHERE id NOT IN (SELECT prospect_id FROM contact_trash) ORDER BY created_at DESC LIMIT 200")
    return rows


def _state():
    from harvey.state import StateManager
    return StateManager(db_path=str(DB_PATH))


async def _delivery_assessment_context(state):
    from harvey.delivery_readiness import global_context,runtime_codes,utcnow,config_signature
    from harvey.config import load_config,load_env
    from harvey.integrations.mail_provider import get_mail_provider
    now=utcnow()
    try:
        config=load_config(str(_resolve_config_file()))
        context=await global_context(state,config,get_mail_provider(config,load_env()),now)
        runtime=runtime_codes(await state.get_setting('delivery_runtime'),_check_harvey_pid(),now,
            max(60,config.usage.heartbeat_interval_minutes*120+60),config_signature(config))
        return config,context,runtime
    except Exception:
        return None,{'codes':['config'],'remaining':None,'now':now},['runtime_unknown']


@app.get("/api/outbox")
async def get_outbox_api(campaign_id: str | None = Query(default=None, max_length=100), item_id:str|None=Query(default=None,max_length=100)):
    """Outbox queue + kill-switch state for the Outbox tab."""
    try:
        state = _state()
        await state.init_db()
        data = {
            "paused": await state.get_setting("sending_paused"),
            "pending": await state.get_outbox(status="pending_review", limit=100, campaign_id=campaign_id),
            "approved": await state.get_outbox(status="approved", limit=50, campaign_id=campaign_id),
            "sent": (await query_db(
                "SELECT * FROM outbox WHERE status = 'sent' " + ("AND campaign_id=? " if campaign_id is not None else "") +
                "ORDER BY sent_at DESC LIMIT 25", (campaign_id,) if campaign_id is not None else ())),
            "failed": (await query_db(
                "SELECT * FROM outbox WHERE status IN ('failed','rejected','cancelled') " + ("AND campaign_id=? " if campaign_id is not None else "") +
                "ORDER BY updated_at DESC LIMIT 25", (campaign_id,) if campaign_id is not None else ())),
        }
        if item_id is not None:
            rows=await query_db('SELECT * FROM outbox WHERE id=?'+(' AND campaign_id=?' if campaign_id is not None else ''),(item_id,campaign_id) if campaign_id is not None else (item_id,))
            for group,statuses in [('pending',{'pending_review'}),('approved',{'approved'}),('sent',{'sent'}),('failed',{'failed','rejected','cancelled'})]:
                data[group]=[r for r in rows if r['status'] in statuses]
            data['item_id']=item_id
        if campaign_id is not None:
            campaign = await query_db('SELECT name FROM campaigns WHERE id=?', (campaign_id,))
            data['campaign_id'] = campaign_id
            data['campaign_name'] = campaign[0]['name'] if campaign else campaign_id
        from harvey.delivery_readiness import assess_message,result
        config,context,runtime=await _delivery_assessment_context(state)
        now=context['now']
        for group in ('pending', 'approved', 'sent', 'failed'):
            for item in data[group]:
                if config is not None:
                    item['readiness'] = await assess_message(state, item, config, context, runtime=runtime)
                elif item['status'] == 'sent':
                    item['readiness'] = {'state':'sent','reasons':[],'earliest_at':None,'remaining_today':None}
                else:
                    codes = [item['status']] if item['status'] in ('failed','rejected','cancelled') else ['config','runtime_unknown'] + (['approval'] if item['status']=='pending_review' else [])
                    item['readiness'] = result(codes)
        data['readiness_checked_at'] = now.isoformat()+'Z'
        return data

    except Exception as e:
        return {"error": str(e)}


@app.post("/api/outbox/approve-all")
async def outbox_approve_all(campaign_id: str | None = Query(default=None, max_length=100)):
    try:
        state = _state()
        await state.init_db()
        n = await state.approve_outbox(campaign_id=campaign_id)
        return {"success": True, "approved": n}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.post("/api/outbox/{item_id}/approve")
async def outbox_approve(item_id: str):
    try:
        state = _state()
        await state.init_db()
        n = await state.approve_outbox(item_id)
        return {"success": bool(n)}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.post("/api/outbox/{item_id}/reject")
async def outbox_reject(item_id: str):
    try:
        state = _state()
        await state.init_db()
        await state.update_outbox_item(item_id, status="rejected")
        return {"success": True}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.post("/api/sending/{action}")
async def sending_toggle(action: str):
    if action not in ("pause", "resume"):
        return JSONResponse({"success": False, "message": "unknown action"}, status_code=400)
    try:
        state = _state()
        await state.init_db()
        if action == "pause":
            await state.set_setting("sending_paused", "paused from dashboard")
        else:
            await state.set_setting("sending_paused", "")
            await state.set_setting("bounce_count", "0")
        return {"success": True}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.get("/api/export/prospects.csv")
async def export_prospects(all: bool = False, min_score: int = 0, email_status: str = ""):
    """Sequencer-ready CSV download of the prospect list."""
    from harvey.state import StateManager
    from harvey.export import export_prospects_csv

    state = StateManager(db_path=str(DB_PATH))
    try:
        await state.init_db()
        statuses = [s.strip() for s in email_status.split(",") if s.strip()] or None
        _, text = await export_prospects_csv(
            state, email_statuses=statuses, min_score=min_score, include_all=all,
        )
    except Exception as e:
        logger.warning("Prospect export failed: %s", e)
        text = ""
    return PlainTextResponse(
        text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="prospects.csv"'},
    )


@app.get("/api/campaigns")
async def get_campaigns():
    rows = await query_db("SELECT * FROM campaigns ORDER BY created_at DESC LIMIT 100")
    for row in rows:
        try:
            row["sequence"] = json.loads(row.get("sequence_json", "[]"))
        except (json.JSONDecodeError, TypeError):
            row["sequence"] = []
        try:
            row["prospect_ids"] = json.loads(row.get("prospect_ids_json", "[]"))
        except (json.JSONDecodeError, TypeError):
            row["prospect_ids"] = []
    return rows


@app.get("/api/conversations")
async def get_conversations():
    rows = await query_db("""
        SELECT c.*, p.first_name, p.last_name, p.email as prospect_email, p.company,
               campaigns.name AS campaign_name
        FROM conversations c
        LEFT JOIN prospects p ON c.prospect_id = p.id
        LEFT JOIN campaigns ON c.campaign_id = campaigns.id
        ORDER BY c.updated_at DESC LIMIT 100
    """)
    for row in rows:
        try:
            row["thread"] = json.loads(row.get("thread_json", "[]"))
        except (json.JSONDecodeError, TypeError):
            row["thread"] = []
    return rows


@app.get("/api/activity")
async def get_activity():
    rows = await query_db("SELECT * FROM actions ORDER BY created_at DESC LIMIT 100")
    for row in rows:
        try:
            row["details"] = json.loads(row.get("details_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            row["details"] = {}
    return rows


# ── Dashboard UI ──


# ── Discovery: the provider menu, an estimate, and a run ──
#
# This is the only stage that spends money, so the UI never starts one without
# showing what it will cost first.

_discovery_task: asyncio.Task | None = None
_discovery_report: dict | None = None
_discovery_start_lock = asyncio.Lock()


def _discovery_queries(body: dict, config):
    from harvey.collectors.discover import build_queries

    cities = [c.strip() for c in (body.get("cities") or []) if c.strip()] or None
    raw_terms = body.get("terms")
    terms = ([t.strip() for t in raw_terms if isinstance(t, str) and t.strip()]
             if isinstance(raw_terms, list) else None)
    radius = body.get('radius_km', 40)
    if isinstance(radius, bool) or not isinstance(radius, (int, float)) or not math.isfinite(radius) or not 1 <= radius <= 200:
        raise ValueError('Search radius must be between 1 and 200 km')
    queries = build_queries(
        config, cities=cities,
        depth=int(body.get("depth") or 30),
        limit=int(body.get("limit") or 100),
        terms=terms,
    )
    locations = body.get('locations') or []
    if not isinstance(locations, list) or len(locations) > 50:
        raise ValueError('Invalid locations')
    coords = {}
    for location in locations:
        if not isinstance(location, dict) or not isinstance(location.get('name'), str):
            raise ValueError('Invalid location')
        lat, lon = location.get('lat'), location.get('lon')
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in (lat, lon)) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('Invalid location coordinates')
        coords[location['name']] = f'{lat},{lon},{radius}'
    for query in queries:
        if query.location in coords:
            query.coordinate = coords[query.location]
        elif query.coordinate and 'radius_km' in body:
            query.coordinate = ','.join(query.coordinate.split(',')[:2]) + f',{radius}'
    if not isinstance(body.get('email_search', False),bool) or body.get('email_mode','quick') not in ('quick','thorough'):
        raise ValueError('Invalid email search options')
    if body.get('provider') == 'google_maps':
        if not cities and not coords:
            raise ValueError('Google Maps requires a specific location.')
        mode, profile = body.get('maps_mode', 'quick'), body.get('maps_filter', 'all')
        resume = body.get('maps_resume', True)
        if not isinstance(resume, bool):
            raise ValueError('Invalid resume option')
        for query in queries:
            query.maps_mode, query.maps_filter, query.maps_resume = mode, profile, resume
        from harvey.collectors.google_maps import plan
        plan(queries)  # Validate and bound before any background work starts.
    return queries



def _discovery_category_supported(provider_key, term):
    from harvey.collectors.discover import PROVIDERS
    if provider_key == "osm":
        return bool(PROVIDERS[provider_key]._tags(term))
    if provider_key == "geoapify":
        return bool(PROVIDERS[provider_key].category_for(term))
    return True


async def _discovery_quota(state, provider_key, queries):
    from harvey.collectors.discovery_quota import LIMITS, quota_status
    from harvey.collectors.discover import PROVIDERS
    if provider_key not in LIMITS:
        return None
    required = sum(PROVIDERS[provider_key].quota_units(q) for q in queries)
    return await quota_status(state, provider_key, required)


def _discovery_preflight(provider_key, queries, config):
    """Return explainable OSM support and truthful ICP caveats before a run."""
    from harvey.collectors.discover import OpenStreetMap

    unsupported = []
    if not queries:
        unsupported.append({"term": "", "location": "", "status": "missing"})
    if provider_key in ("osm", "geoapify"):
        osm = OpenStreetMap()
        for query in queries:
            if not _discovery_category_supported(provider_key, query.term):
                unsupported.append({"term": query.term, "location": query.location,
                                    "status": "unsupported",
                                    "suggestions": [term for term in osm.suggest_terms(query.term)
                                                    if _discovery_category_supported(provider_key, term)]})
    descriptions = [str(x).lower() for x in config.icp.industries]
    broad_sme = any(any(phrase in x for phrase in (
        "branchenübergreifend", "alle branchen", "kmu", "kleine und mittlere unternehmen",
        "all industries", "sme")) for x in descriptions)
    size = str(config.icp.company_size or "").lower()
    size_claim = any(x in size for x in ("500", "unter", "under", "fewer than"))
    warnings = []
    if provider_key in ('osm', 'geoapify'):
        from harvey.collectors.parking import parking_intent
        intents = [parking_intent(q.term) for q in queries]
        if any(intent is not None and intent.operators for intent in intents):
            warnings.append({
                'code': 'parking_operator_evidence', 'status': 'warning',
                'message': 'Only explicitly recorded parking operators are returned. Coverage may be incomplete. Facility contact details are not assigned to the operator; the search area refers to its parking locations, not its headquarters.',
            })
        if any(intent is not None and not intent.operators for intent in intents):
            warnings.append({
                'code': 'parking_facilities', 'status': 'warning',
                'message': 'This search returns parking facilities, not necessarily operator companies. Use Parking operators to look for explicitly recorded operators.',
            })
    if broad_sme:
        warnings.append({"code": "broad_sme", "status": "warning"})
    if size_claim:
        warnings.append({"code": "company_size_unverified", "status": "unknown"})
    return {"unsupported": unsupported, "warnings": warnings,
            "can_run": not unsupported}


@app.get('/api/discover/locations')
async def discovery_locations(q: str = Query('', max_length=200), lang: str = Query('de', pattern='^(de|en)$')):
    from harvey.config import load_env
    from harvey.collectors.location_suggestions import suggest_locations
    state = _state()
    await state.init_db()
    return await suggest_locations(state, q.strip(), lang, load_env().geoapify_api_key)


@app.get('/api/discover/progress')
async def get_discovery_progress():
    from harvey.discovery_progress import KEY, progress_view
    state = _state()
    await state.init_db()
    raw = await state.get_setting(KEY)
    running = bool(_discovery_task and not _discovery_task.done())
    progress = progress_view(json.loads(raw) if raw else None, running)
    if progress:
        progress['stop_requested'] = bool(running and await state.get_setting('discovery_paused'))
    return {'progress': progress}


@app.get("/api/discover/providers")
async def get_discovery_providers():
    """What each source does, what it costs, and whether it's ready to use."""
    try:
        from harvey.collectors.discover import DEFAULT_PROVIDER, PROVIDERS, provider_menu
        from harvey.config import load_config, load_env

        config = load_config()
        state = _state()
        await state.init_db()
        from harvey.collectors.discovery_quota import quota_status
        providers = provider_menu(load_env().model_dump())
        from harvey.discovery_catalog import term_catalog
        for item in providers:
            item["quota"] = await quota_status(state, item["key"])
        return {
            "providers": providers,
            "default": DEFAULT_PROVIDER,
            "selected": await state.get_setting("discovery_provider") or DEFAULT_PROVIDER,
            "paused": await state.get_setting("discovery_paused"),
            "running": bool(_discovery_task and not _discovery_task.done()),
            "last_report": _discovery_report,
            "default_terms": (getattr(config.icp, "discovery_terms", []) or
                              config.icp.industries or [config.product.name]),
            "default_locations": config.icp.geography,
            'term_catalog': {key: term_catalog(key, _discovery_category_supported) for key in PROVIDERS},
            'location_autocomplete': bool(load_env().geoapify_api_key),
            "suggested_terms": (PROVIDERS["osm"].SUGGESTED_TERMS
                                if "osm" in PROVIDERS else []),
            "supported_terms": {key: [term for term in PROVIDERS["osm"].SUGGESTED_TERMS
                                     if _discovery_category_supported(key, term)]
                                for key in ("osm", "geoapify")},
        }
    except Exception as e:
        logger.exception("discovery providers failed")
        return {"providers": [], "error": str(e)}


@app.post("/api/discover/estimate")
async def estimate_discovery(request: Request):
    """Projected spend and the exact query list, before anything is called."""
    try:
        from harvey.collectors.discover import PROVIDERS, estimate_cost
        from harvey.config import load_config

        body = await request.json()
        provider = body.get("provider") or ""
        if provider not in PROVIDERS:
            return JSONResponse({"error": f"unknown provider {provider!r}"},
                                status_code=400)

        config = load_config()
        queries = _discovery_queries(body, config)
        preflight = _discovery_preflight(provider, queries, config)
        state = _state()
        await state.init_db()
        if provider == 'google_maps':
            from harvey.collectors.google_maps import browser_available
            if not await browser_available():
                preflight['can_run'] = False
                preflight['warnings'].append({'message': 'Chromium is missing. Run bash scripts/install-maps-browser.sh in the project terminal.'})
        quota = await _discovery_quota(state, provider, queries)
        if quota and not quota["can_run"]:
            preflight["can_run"] = False
        return {
            "provider": provider,
            "queries": [q.keyword() for q in queries],
            "query_details": [{"term": q.term, "location": q.location,
                               "keyword": q.keyword(),
                               "status": ("unsupported" if not _discovery_category_supported(provider, q.term)
                                          else "supported" if provider in ("osm", "geoapify")
                                          else "provider_query")}
                              for q in queries],
            "query_count": len(queries) * (9 if provider == 'google_maps' and body.get('maps_mode') == 'grid' else 1),
            "max_results": sum(q.limit for q in queries) * (9 if provider == 'google_maps' and body.get('maps_mode') == 'grid' else 1),
            "estimated_cost": round(estimate_cost(provider, queries), 4),
            "free": PROVIDERS[provider].estimate(queries) == 0,
            "quota": quota,
            **preflight,
        }
    except (ValueError, TypeError) as e:
        return JSONResponse({'error': str(e), 'success': False, 'message': str(e)}, status_code=422)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/discover/run")
async def start_discovery(request: Request):
    async with _discovery_start_lock:
        return await _start_discovery(request)


async def _start_discovery(request: Request):
    """Kick off a run in the background and hand back immediately.

    Discovery takes minutes, not milliseconds — holding the request open
    would just time out. Progress shows up in the run log.
    """
    global _discovery_task, _discovery_report

    if _discovery_task and not _discovery_task.done():
        return JSONResponse({"success": False, "message": "a run is already going"},
                            status_code=409)
    try:
        from harvey.collectors.discover import PROVIDERS
        from harvey.config import load_config
        from harvey.pipeline import run_prospecting

        body = await request.json()
        provider = body.get("provider") or ""
        if provider not in PROVIDERS:
            return JSONResponse({"success": False,
                                 "message": f"unknown provider {provider!r}"},
                                status_code=400)

        config = load_config()
        queries = _discovery_queries(body, config)
        preflight = _discovery_preflight(provider, queries, config)
        if not preflight["can_run"]:
            return JSONResponse({"success": False,
                                 "message": ("Bitte mindestens einen Suchbegriff eingeben." if
                                             any(x["status"] == "missing" for x in preflight["unsupported"])
                                             else "Diese Datenquelle unterstützt einzelne Suchbegriffe nicht."),
                                 **preflight}, status_code=422)
        max_spend = float(body.get("max_spend", 1.0))

        state = _state()
        await state.init_db()
        target_profile=None
        if body.get('target_profile_id'):
            from harvey.target_profiles import get_profile
            if not isinstance(body['target_profile_id'],str) or len(body['target_profile_id'])>100:
                raise ValueError('Invalid target profile')
            target_profile=await get_profile(state,body['target_profile_id'])
        quota = await _discovery_quota(state, provider, queries)
        if quota and not quota["can_run"]:
            return JSONResponse({"success": False, "message": "Free quota exhausted. No paid search was started.",
                                 "quota": quota}, status_code=422)
        await state.set_setting("discovery_provider", provider)
        await state.set_setting("discovery_paused", "")

        from harvey.discovery_progress import DiscoveryProgress
        progress = DiscoveryProgress(state)
        await progress.update({'search': {
            'terms': list(dict.fromkeys(query.term for query in queries)),
            'cities': list(dict.fromkeys(query.location for query in queries if query.location)),
            'target_profile_id':body.get('target_profile_id',''),
            'email_search': body.get('email_search', False), 'email_mode': body.get('email_mode','quick'),
            'maps_mode': body.get('maps_mode', 'quick'), 'maps_filter': body.get('maps_filter', 'all'), 'maps_resume': body.get('maps_resume', True),
            'locations': body.get('locations') or [], 'radius_km': body.get('radius_km', 40), 'query_count': len(queries) * (9 if provider == 'google_maps' and body.get('maps_mode') == 'grid' else 1),
        }})

        async def _go():
            global _discovery_report
            try:
                # Discovery chains straight into profiling: reading the sites
                # is free, and it is what makes the results worth anything.
                result = await run_prospecting(state, config, provider, queries,
                                               max_spend=max_spend, on_progress=progress.update,
                                               radius_km=body.get('radius_km', 40),
                                               email_search=body.get('email_search',False), email_mode=body.get('email_mode','quick'),**({'target_profile':target_profile} if target_profile else {}))
                _discovery_report = {
                    **(result.discover or {}),
                    "profiled_companies": result.profiled_companies,
                    "profile_observations": result.profile_observations,
                    "errors": result.errors,
                    "email_summary": getattr(result, "email_summary", {}),
                    "target_summary":getattr(result,"target_summary",{}),
                }
                paused = await state.get_setting('discovery_paused')
                await progress.finish('stopped' if paused or (result.discover or {}).get('stopped') else
                                      'completed_with_errors' if result.errors or progress.data['errors'] else 'completed')
            except Exception as exc:
                logger.exception("discovery run failed")
                _discovery_report = {"errors": [str(exc)], "stopped": "failed"}
                await progress.finish('failed')

        _discovery_report = None
        _discovery_task = asyncio.create_task(_go())
        return {"success": True, "queries": len(queries) * (9 if provider == "google_maps" and body.get("maps_mode") == "grid" else 1)}
    except (ValueError, TypeError) as e:
        return JSONResponse({'error': str(e), 'success': False, 'message': str(e)}, status_code=422)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.post("/api/profile/run")
async def start_profile():
    async with _discovery_start_lock:
        return await _start_profile()


async def _start_profile():
    """Read the websites of everything discovered but not yet looked at.

    Free and model-free, so there is nothing to estimate and no cap to set.
    """
    global _discovery_task, _discovery_report

    if _discovery_task and not _discovery_task.done():
        return JSONResponse({"success": False, "message": "a run is already going"},
                            status_code=409)
    try:
        from harvey.pipeline import run_profile_stage

        state = _state()
        await state.init_db()
        pending = await state.count_companies_needing_profile()
        if not pending:
            return {"success": True, "pending": 0}

        from harvey.discovery_progress import DiscoveryProgress
        progress = DiscoveryProgress(state)
        await progress.update({})
        await state.set_setting('discovery_paused', '')

        async def _go():
            global _discovery_report
            try:
                companies, observations, _ = await run_profile_stage(state, limit=200, on_progress=progress.update)
                _discovery_report = {
                    "profiled_companies": companies,
                    "profile_observations": observations,
                }
                await progress.finish('stopped' if await state.get_setting('discovery_paused') else 'completed')
            except Exception as exc:
                logger.exception("profile run failed")
                _discovery_report = {"errors": [str(exc)], "stopped": "failed"}
                await progress.finish('failed')

        _discovery_report = None
        _discovery_task = asyncio.create_task(_go())
        return {"success": True, "pending": pending}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.post("/api/discover/stop")
async def stop_discovery():
    """Kill switch. Read between batches, so an in-flight run stops cleanly."""
    try:
        state = _state()
        await state.init_db()
        await state.set_setting("discovery_paused", "stopped from dashboard")
        return {"success": True}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.get("/api/today")
async def get_today():
    """What needs a human, right now.

    The dashboard opens here rather than on a setup checklist: the question a
    returning user actually has is "is anything waiting on me?", and the
    answer is usually a short list or nothing at all.
    """
    items: list[dict] = []
    stats: dict = {}
    try:
        from harvey.signals import seed_signal_catalog

        state = _state()
        await state.init_db()
        await seed_signal_catalog(state)

        codes = await state.get_signal_codes()
        proposed = [c for c in codes if c.get("status") == "proposed"]
        confirmed = [c for c in codes if c.get("status") == "confirmed"]
        pending = await state.get_outbox(status="pending_review", limit=200)
        approved = await state.get_outbox(status="approved", limit=200)
        paused = await state.get_setting("sending_paused")
        counts = await state.count_prospects_by_status()

        convos = await query_db(
            "SELECT COUNT(*) AS n FROM conversations WHERE status = 'open'"
        )
        open_convos = convos[0]["n"] if convos else 0
        companies = await query_db("SELECT COUNT(*) AS n FROM companies WHERE removed_at IS NULL")
        n_companies = companies[0]["n"] if companies else 0

        unprofiled_count = await state.count_companies_needing_profile()
        stats = {
            "companies": n_companies,
            "prospects": sum(counts.values()),
            "signals_confirmed": len(confirmed),
            "outbox_pending": len(pending),
            "outbox_approved": len(approved),
            "open_conversations": open_convos,
            "unprofiled": unprofiled_count,
        }

        # Ordered by how much it blocks Siveron from doing anything at all.
        if paused:
            items.append({
                "key": "paused", "tone": "bad",
                "title": "Sending is paused",
                "detail": str(paused) + ". Nothing will go out until you resume it.",
                "action": "Review and resume", "tab": "outbox",
            })

        setup = await get_setup_status()
        if isinstance(setup, dict) and setup.get("percent", 100) < 100:
            missing = [c["label"] for c in setup.get("checks", [])
                       if c.get("required") and not c.get("done")]
            items.append({
                "key": "setup", "tone": "warn",
                "title": "Finish setting Siveron up",
                "detail": ", ".join(missing[:3]) or "Some required steps are incomplete.",
                "action": "Open setup", "tab": "settings",
            })

        if proposed:
            items.append({
                "key": "signals", "tone": "warn",
                "title": (f"{len(proposed)} signal waiting for your confirmation"
                          if len(proposed) == 1
                          else f"{len(proposed)} signals waiting for your confirmation"),
                "detail": ("Siveron won't collect anything you haven't approved. "
                           "Confirm which signals define a good prospect for you."),
                "action": "Review signals", "tab": "signals",
            })
        elif not confirmed:
            items.append({
                "key": "signals-none", "tone": "warn",
                "title": "No signals confirmed",
                "detail": "Every signal is rejected, so prospecting has nothing to collect.",
                "action": "Review signals", "tab": "signals",
            })

        if not n_companies and confirmed:
            items.append({
                "key": "discover", "tone": "good",
                "title": "No companies yet",
                "detail": ("Signals are confirmed but nothing has been collected. "
                           "Discovery is free to try — no account needed."),
                "action": "Find businesses", "tab": "discover",
            })

        unprofiled = unprofiled_count
        if unprofiled:
            items.append({
                "key": "profile", "tone": "good",
                "title": f"{unprofiled} companies not looked at yet",
                "detail": ("Reading their websites is free and it is what makes "
                           "an email specific — who their agency is, what they "
                           "are missing, whether they are spending on ads."),
                "action": "Read their sites", "tab": "discover",
            })

        if pending:
            items.append({
                "key": "outbox", "tone": "warn",
                "title": (f"{len(pending)} email waiting for approval" if len(pending) == 1
                          else f"{len(pending)} emails waiting for approval"),
                "detail": "Nothing sends until you approve it. Read them one at a time.",
                "action": "Open the decisions desk", "tab": "outbox",
            })

        if open_convos:
            items.append({
                "key": "replies", "tone": "good",
                "title": (f"{open_convos} live conversation" if open_convos == 1
                          else f"{open_convos} live conversations"),
                "detail": "People replied. Check how Siveron is handling them.",
                "action": "Read conversations", "tab": "conversations",
            })

        from harvey.work_items import work_items
        operations=await work_items(state,await _delivery_assessment_context(state))
        items=[i for i in items if i['key'] not in ('outbox','replies') and not(i['key']=='paused' and any(t['kind']=='blocked' for t in operations['items']))]
        async with state._connect() as db:
            for status,key in [('pending_review','outbox_pending'),('approved','outbox_approved')]:
                stats[key]=(await (await db.execute('SELECT COUNT(*) FROM outbox WHERE status=?',(status,))).fetchone())[0]
        return {"items": items, "stats": stats,"work_total":operations['total']}
    except Exception as e:
        logger.exception("today load failed")
        return {"items": [], "stats": stats, "error": str(e)}


# ── Signals: Siveron proposes, the user confirms ──
#
# Nothing is collected until a human has said yes to it. This is the gate the
# whole prospecting pipeline hangs off: collectors ask `state.confirmed_signal_codes()`
# and skip anything that isn't in the set.

CATEGORY_META = {
    "discovery": {
        "label": "Discovery — who exists",
        "blurb": "How Siveron finds businesses at all, and how visible they are. "
                 "This is the only stage that costs money.",
    },
    "profile": {
        "label": "Profile — what they are",
        "blurb": "Read from the pages a business already publishes. Free, no AI "
                 "tokens, three HTTP requests per company. These are the signals "
                 "that make an email specific.",
    },
    "people": {
        "label": "People — who decides",
        "blurb": "Named humans and whether they're the one who can say yes.",
    },
    "verification": {
        "label": "Contactability — can you reach them",
        "blurb": "Whether the address will actually deliver, and what to do when "
                 "it won't.",
    },
}
CATEGORY_ORDER = ["discovery", "profile", "people", "verification"]


@app.get("/api/signals")
async def get_signals():
    """The signal vocabulary, grouped for review, with live cohort sizes."""
    try:
        from harvey.signals import seed_signal_catalog

        state = _state()
        await state.init_db()
        # Seeding is idempotent and never overrides a decision the user made,
        # so it is safe to run on every load — new signals shipped in an
        # upgrade show up as `proposed` without any migration step.
        await seed_signal_catalog(state)

        codes = await state.get_signal_codes()
        counts = {c["signal_code"]: c for c in await state.signal_counts()}

        groups, summary = [], {"proposed": 0, "confirmed": 0, "rejected": 0}
        for cat in CATEGORY_ORDER:
            rows = []
            for sig in codes:
                if sig.get("category") != cat:
                    continue
                seen = counts.get(sig["code"], {})
                rows.append({
                    **sig,
                    "companies": seen.get("companies", 0),
                    "observations": seen.get("observations", 0),
                })
            if rows:
                meta = CATEGORY_META.get(cat, {})
                groups.append({
                    "key": cat,
                    "label": meta.get("label", cat.title()),
                    "blurb": meta.get("blurb", ""),
                    "signals": rows,
                })
        for sig in codes:
            summary[sig.get("status", "proposed")] = (
                summary.get(sig.get("status", "proposed"), 0) + 1
            )

        return {"summary": summary, "groups": groups, "total": len(codes)}
    except Exception as e:
        logger.exception("signals load failed")
        return {"error": str(e), "groups": [], "summary": {}}


@app.post("/api/signals/status")
async def set_signals_status(request: Request):
    """Confirm or reject one signal, or a whole category at once."""
    try:
        body = await request.json()
        status = (body.get("status") or "").strip()
        codes = body.get("codes") or ([body["code"]] if body.get("code") else [])
        if status not in ("proposed", "confirmed", "rejected"):
            return JSONResponse(
                {"success": False, "message": f"invalid status: {status!r}"},
                status_code=400,
            )
        if not codes:
            return JSONResponse(
                {"success": False, "message": "no signal codes given"}, status_code=400
            )

        from harvey.signals import seed_signal_catalog

        state = _state()
        await state.init_db()
        # Seed first: a confirm that arrives before anything has loaded the
        # catalog would otherwise report success while changing nothing.
        await seed_signal_catalog(state)

        changed, unknown = 0, []
        for code in codes:
            if await state.set_signal_status(code, status):
                changed += 1
            else:
                unknown.append(code)
        return {
            "success": True, "changed": changed,
            "status": status, "unknown": unknown,
        }
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.post("/api/cohort")
async def preview_cohort(request: Request):
    """How many companies carry ALL these signals and none of those.

    The payoff for confirming signals: a cohort is a query, not a list. Set
    intersection happens in SQL — intersecting in JS over a capped fetch
    silently returns the wrong answer.
    """
    try:
        body = await request.json()
        require = [c for c in (body.get("require") or []) if c]
        exclude = [c for c in (body.get("exclude") or []) if c]
        if not require:
            return {"size": 0, "companies": []}

        state = _state()
        await state.init_db()
        ids = await state.cohort(require, exclude, limit=1000)
        if not ids:
            return {"size": 0, "companies": []}

        placeholders = ",".join("?" for _ in ids[:200])
        rows = await query_db(
            f"SELECT id, name, domain, industry, location FROM companies "
            f"WHERE removed_at IS NULL AND id IN ({placeholders})",
            tuple(ids[:200]),
        )
        return {"size": len(ids), "companies": rows}
    except Exception as e:
        return JSONResponse({"size": 0, "companies": [], "error": str(e)}, status_code=500)


@app.get("/api/runs")
async def get_runs_api():
    """The collector run log — what ran, when, what it produced and cost."""
    try:
        state = _state()
        await state.init_db()
        await state.sweep_stale_runs()
        return await state.get_runs(limit=25)
    except Exception as e:
        return {"error": str(e)}


WEB_DIR = (Path(__file__).resolve().parent / "web")


TEXT_TYPES = {".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml"}
BINARY_TYPES = {".woff2": "font/woff2", ".woff": "font/woff", ".png": "image/png"}


@app.get("/static/{path:path}")
async def static_file(path: str):
    """Serve the dashboard's own assets from disk.

    Read per-request rather than cached at import: editing app.css and hitting
    reload is the whole point of having them as real files. Fonts are vendored
    rather than fetched from a CDN — this is a local tool and it should work
    with the network off.
    """
    target = (WEB_DIR / path).resolve()
    root = WEB_DIR.resolve()
    if not target.is_file() or not target.is_relative_to(root):
        return PlainTextResponse("not found", status_code=404)

    if target.suffix in BINARY_TYPES:
        return Response(
            target.read_bytes(),
            media_type=BINARY_TYPES[target.suffix],
            headers={"Cache-Control": "public, max-age=604800"},
        )
    return PlainTextResponse(
        target.read_text(encoding="utf-8"),
        media_type=TEXT_TYPES.get(target.suffix, "text/plain"),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


def start_dashboard(host: str = "127.0.0.1", port: int = 5555):
    """Start the dashboard server."""
    import uvicorn

    print(f"\n  Siveron Dashboard running at http://{host}:{port}")
    print("  Press Ctrl+C to stop.\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")

# Focused, local CRM endpoints. Registration has no external side effects.
from harvey.crm_routes import install_crm_routes
install_crm_routes(app, _state, query_db, _read_env_file)


@app.get('/api/campaign-readiness')
async def campaign_readiness():
    """Explain remaining sending setup without blocking local draft/review work."""
    notices=[]
    try:
        with open(_resolve_config_file()) as stream:
            cfg=yaml.safe_load(stream) or {}
        email=((cfg.get('channels') or {}).get('email') or {})
        if not email.get('enabled',False):
            notices.append('E-Mail-Versand ist deaktiviert.')
        if email.get('max_daily_sends',0)<=0:
            notices.append('Das tägliche Versandlimit steht auf 0.')
        if email.get('provider','instantly') not in ('smtp','gmail'):
            notices.append('Dieser Freigabeablauf benötigt SMTP oder Gmail als Versandweg.')
        setup=await get_setup_status()
        if any(c['id']=='email_provider' and not c['done'] for c in setup.get('checks',[])):
            notices.append('Das Versandpostfach muss noch eingerichtet werden.')
        sm=_state()
        await sm.init_db()
        if await sm.get_setting('sending_paused'):
            notices.append('Der Versand ist pausiert.')
    except Exception:
        notices.append('Versandeinstellungen konnten nicht vollständig geprüft werden. Bitte Einstellungen öffnen.')
    return {'notices':notices}


_sending_config_lock = asyncio.Lock()


@app.get('/api/settings/sending')
async def get_sending_settings():
    from harvey.sending_settings import read_sending_settings
    try:
        result=read_sending_settings(_resolve_config_file())
        result['agent_running']=_check_harvey_pid() is not None
        return result
    except Exception:
        return JSONResponse({'error':'Versandeinstellungen konnten nicht gelesen werden.'},status_code=422)


@app.post('/api/settings/sending')
async def update_sending_settings(request:Request):
    from harvey.sending_settings import save_sending_settings, SendingSettingsError
    try:
        payload=await request.json()
        async with _sending_config_lock:
            if _check_harvey_pid() is not None:
                return JSONResponse({'error':'Bitte den Agenten im Reiter Steuerung zuerst anhalten und danach erneut speichern.'},status_code=409)
            result=save_sending_settings(_resolve_config_file(),payload)
        return dict(result,success=True)
    except (ValueError,SendingSettingsError):
        return JSONResponse({'error':'Ungültige oder veraltete Einstellungen. Bitte neu laden und Status sowie Tageslimit prüfen.'},status_code=422)
    except OSError:
        return JSONResponse({'error':'Die Versandeinstellungen konnten nicht gespeichert werden.'},status_code=500)

from harvey.target_profiles import install_target_profile_routes
install_target_profile_routes(app, _state)

from harvey.campaign_results import install_result_routes
from harvey.work_items import install_work_routes
install_result_routes(app,_state)
install_work_routes(app,_state,_delivery_assessment_context)

from harvey.sales_workflows import install_sales_routes
install_sales_routes(app,_state)

from harvey.company_field_review import install_field_review_routes
install_field_review_routes(app, _state)

from harvey.assistant import install_assistant_routes
install_assistant_routes(app, _state)

from harvey.decision_makers import install_decision_maker_routes
install_decision_maker_routes(app, _state, _company_people_jobs)

from harvey.contact_research import install_contact_research_routes
install_contact_research_routes(app, _state)

from harvey.company_reports import install_report_routes
install_report_routes(app, _state)
