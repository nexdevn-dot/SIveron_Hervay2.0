"""Force refresh bypasses cached quota without model calls."""
from unittest.mock import AsyncMock
import pytest
from harvey.codex import CodexQuotaClient
from harvey.integrations.quota import QuotaClient


@pytest.mark.asyncio
@pytest.mark.parametrize('provider',['codex','claude'])
async def test_force_refresh_updates_timestamp_and_drops_failed_reading(provider):
    readings=[{'five_hour':{'utilization':8}}, {'five_hour':{'utilization':11}}, None]
    fetch=AsyncMock(side_effect=readings)
    if provider=='codex':
        client=CodexQuotaClient(type('Client',(),{'read_rate_limits':fetch})())
    else:
        client=QuotaClient();client._fetch=fetch
    assert client.checked_at is None
    assert (await client.get_utilization())['five_hour']['utilization']==8
    stamp=client.checked_at
    assert stamp and stamp.endswith('Z')
    assert (await client.get_utilization())['five_hour']['utilization']==8
    assert fetch.await_count==1 and client.checked_at==stamp
    assert (await client.get_utilization(force=True))['five_hour']['utilization']==11
    assert fetch.await_count==2
    assert await client.get_utilization(force=True) is None
    assert await client.get_utilization() is None
    assert fetch.await_count==3
