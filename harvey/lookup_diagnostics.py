"""Stable non-secret public lookup outcomes; no raw exception messages."""
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


def diagnostic(stage, code, url='', retryable=False, http_status=None):
    try:
        parts=urlsplit(url)
        clean=urlunsplit((parts.scheme,parts.hostname or '',parts.path,'','')) if parts.scheme in ('http','https') else ''
    except ValueError:clean=''
    return dict(stage=stage,code=code,source=clean,retryable=retryable,http_status=http_status)


def result_diagnostic(result):
    reasons=result.get('diagnostics') or [diagnostic('lookup',{
        'found':'found','not_found':'no_email_in_checked_pages','no_website':'no_website',
        'unreachable':'unreachable'}.get(result.get('status'),'lookup_failed'),retryable=result.get('status') in ('failed','unreachable'))]
    return {'checked_at':datetime.now(timezone.utc).isoformat(),'reasons':reasons[:24],
        'retryable':any(r.get('retryable') for r in reasons)}
