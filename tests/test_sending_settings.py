"""Sending preferences change only the two requested keys; never start an agent."""
import os
import pytest
from fastapi.testclient import TestClient
import harvey.dashboard as dashboard
from harvey.sending_settings import read_sending_settings, save_sending_settings, SendingSettingsError


@pytest.fixture
def config_file(tmp_path):
    path=tmp_path/'harvey.local.yaml'
    path.write_text('''# Keep this comment
persona:
  name: Example
channels:
  email:
    enabled: false # stays commented
    provider: smtp
    max_daily_sends: 0
    require_approval: true
    send_to_risky: false
  linkedin:
    enabled: false
brain:
  codex_restricted_text: true
''')
    path.chmod(0o600)
    return path


def test_exact_atomic_edit_keeps_comments_and_other_values(config_file):
    before=config_file.read_text()
    revision=read_sending_settings(config_file)['revision']
    result=save_sending_settings(config_file,dict(enabled=True,max_daily_sends=1,revision=revision))
    assert result['enabled'] is True and result['max_daily_sends']==1
    assert config_file.read_text()==before.replace('enabled: false #','enabled: true #').replace('max_daily_sends: 0','max_daily_sends: 1')
    if os.name != 'nt':
        assert config_file.stat().st_mode & 0o777==0o600
    assert not list(config_file.parent.glob('.harvey.local.yaml.*'))
    with pytest.raises(SendingSettingsError):
        save_sending_settings(config_file,dict(enabled=False,max_daily_sends=0,revision=revision))


@pytest.mark.parametrize('enabled,limit',[(1,1),('true',1),(True,True),(True,-1),(True,1.5),(True,100001),(True,'2')])
def test_invalid_values_do_not_change_file(config_file,enabled,limit):
    before=config_file.read_bytes()
    with pytest.raises(SendingSettingsError):
        save_sending_settings(config_file,dict(enabled=enabled,max_daily_sends=limit,revision=read_sending_settings(config_file)['revision']))
    assert config_file.read_bytes()==before


def test_missing_keys_are_inserted_without_overwriting_provider(config_file):
    config_file.write_text('channels:\n  email:\n    provider: smtp # preserve\n')
    result=save_sending_settings(config_file,dict(enabled=False,max_daily_sends=0,revision=read_sending_settings(config_file)['revision']))
    assert result['enabled'] is False and result['max_daily_sends']==0
    assert 'provider: smtp # preserve' in config_file.read_text()


def test_settings_api_does_not_start_agent_or_touch_other_config(config_file,monkeypatch):
    monkeypatch.setattr(dashboard,'_resolve_config_file',lambda:config_file)
    monkeypatch.setattr(dashboard,'_check_harvey_pid',lambda:None)
    with TestClient(dashboard.app) as client:
        data=client.get('/api/settings/sending').json()
        assert data['enabled'] is False and data['max_daily_sends']==0
        payload=dict(enabled=True,max_daily_sends=1,revision=data['revision'])
        assert client.post('/api/settings/sending',json=payload).json()['success']
        assert client.post('/api/settings/sending',json=payload).status_code==422
        before=config_file.read_bytes()
        monkeypatch.setattr(dashboard,'_check_harvey_pid',lambda:123)
        assert client.get('/api/settings/sending').json()['agent_running']
        assert client.post('/api/settings/sending',json=payload).status_code==409
        assert config_file.read_bytes()==before


@pytest.mark.parametrize('newline', [b'\n', b'\r\n'])
@pytest.mark.parametrize('missing_keys', [False, True])
def test_atomic_edit_preserves_file_newlines(config_file, newline, missing_keys):
    original = b'# preserve\nchannels:\n  email:\n    provider: smtp # keep\n'
    if not missing_keys:
        original += b'    enabled: false\n    max_daily_sends: 0\n'
    original = original.replace(b'\n', newline)
    config_file.write_bytes(original)
    revision = read_sending_settings(config_file)['revision']
    save_sending_settings(config_file, dict(enabled=True, max_daily_sends=1, revision=revision))
    updated = config_file.read_bytes()
    assert b'provider: smtp # keep' + newline in updated
    assert b'enabled: true' + newline in updated
    assert b'max_daily_sends: 1' + newline in updated
    assert b'\r' not in updated.replace(b'\r\n', b'')
    if newline == b'\r\n':
        assert b'\n' not in updated.replace(b'\r\n', b'')


def test_line_ending_change_is_a_stale_revision(config_file):
    original = config_file.read_bytes().replace(b'\r\n', b'\n')
    config_file.write_bytes(original)
    revision = read_sending_settings(config_file)['revision']
    changed = original.replace(b'\n', b'\r\n')
    config_file.write_bytes(changed)
    with pytest.raises(SendingSettingsError):
        save_sending_settings(config_file, dict(enabled=True, max_daily_sends=1, revision=revision))
    assert config_file.read_bytes() == changed
