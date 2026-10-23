"""Conservative, persistent free-tier limits for Siveron's own requests.

Requests are reserved before sending and never refunded on ambiguous failures.
Usage in other apps is not visible here. Periods use UTC, not the browser clock.
"""
from datetime import datetime, timezone

LIMITS = {"geoapify": (3000, "day"), "serpapi": (250, "month")}


def quota_key(provider, now=None):
    now = now or datetime.now(timezone.utc)
    period = LIMITS[provider][1]
    stamp = now.strftime("%Y-%m-%d" if period == "day" else "%Y-%m")
    return f"discovery_quota:{provider}:{stamp}"


async def quota_status(state, provider, required=0):
    if provider not in LIMITS:
        return None
    limit, period = LIMITS[provider]
    used = int(await state.get_setting(quota_key(provider), "0"))
    return {"limit": limit, "used": used, "remaining": max(0, limit - used),
            "period": period, "required": required,
            "can_run": required <= max(0, limit - used), "scope": "local"}


async def reserve_quota(state, provider, units):
    limit, _ = LIMITS[provider]
    return await state.reserve_setting(quota_key(provider), units, limit)
