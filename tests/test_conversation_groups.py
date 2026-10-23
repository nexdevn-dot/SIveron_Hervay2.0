"""Conversation grouping uses the recorded campaign, never a guessed membership."""
import pytest
import harvey.dashboard as dashboard

@pytest.mark.asyncio
async def test_conversation_api_preserves_campaign_and_parses_thread(monkeypatch):
    async def query(sql):
        assert 'LEFT JOIN campaigns ON c.campaign_id = campaigns.id' in sql
        assert 'campaigns.name AS campaign_name' in sql
        return [
            {'id': 'reply', 'campaign_id': 'campaign', 'campaign_name': 'Autumn',
             'thread_json': '[{"sender":"prospect","content":"Hello"}]'},
            {'id': 'unassigned', 'campaign_id': '', 'campaign_name': None, 'thread_json': 'broken'},
        ]
    monkeypatch.setattr(dashboard, 'query_db', query)
    rows = await dashboard.get_conversations()
    assert rows[0]['campaign_name'] == 'Autumn'
    assert rows[0]['thread'][0]['content'] == 'Hello'
    assert rows[1]['campaign_id'] == ''
    assert rows[1]['thread'] == []
