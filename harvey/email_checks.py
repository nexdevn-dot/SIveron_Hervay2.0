"""Shared syntax/transport checks, separate from DNS evidence and verification."""
from functools import lru_cache
import re
from email_validator import validate_email, EmailNotValidError

# Preserve the current mail transport's ASCII policy; do not silently enable SMTPUTF8.
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


@lru_cache(maxsize=4096)
def _syntax(value):
    try:
        # Preserve existing fixture compatibility; this does NOT run DNS or verify a mailbox.
        result = validate_email(value, check_deliverability=False, test_environment=True)
        return result.normalized.lower()
    except EmailNotValidError:
        return None


def email_checks(value):
    value = value.strip() if isinstance(value, str) else ''
    normalized = _syntax(value) if value else None
    syntax = normalized is not None
    transport = syntax and bool(EMAIL_RE.fullmatch(value))
    return {'syntax_valid':syntax, 'send_supported':transport,
            'reason':'empty' if not value else 'syntax_invalid' if not syntax else
                     'transport_unsupported' if not transport else 'ready'}


def send_address_valid(value):
    return email_checks(value)['send_supported']


@lru_cache(maxsize=4096)
def normalize_public_email(value):
    normalized = _syntax(str(value).strip())
    if not normalized or normalized.endswith(('.png','.jpg','.jpeg','.svg','.webp')):
        return None
    if normalized.rsplit('@',1)[-1] in ('example.com','example.org','example.net'):
        return None
    return normalized
