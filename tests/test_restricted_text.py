"""Local compatibility mode: final text, no host capabilities, no actions."""
import hashlib
import json
import os
import shutil
import sys

import pytest

import harvey.codex as hc
from harvey.brain import Brain
from harvey.config import BrainConfig
from tests.test_codex_cli_surface import EVIL_MCP, mock_codex


def test_restricted_mode_is_explicit_and_reaches_client():
    assert BrainConfig().codex_restricted_text is False
    cfg = BrainConfig(provider='codex', model='gpt-6-luna', codex_restricted_text=True)
    brain = Brain(None, cfg)
    assert brain.codex.restricted_text is True
    assert brain.codex.model == 'gpt-6-luna'


def test_training_preserves_restricted_mode():
    from harvey.trainer import brain_section
    cfg = BrainConfig(provider='codex', model='gpt-6-luna', reasoning_effort='low',
                      codex_restricted_text=True)
    assert BrainConfig(**brain_section(cfg)) == cfg


def test_setup_preserves_the_configured_model_and_mode(monkeypatch):
    import harvey.setup as setup
    cfg = BrainConfig(provider='codex', model='gpt-6-luna', reasoning_effort='low',
                      codex_restricted_text=True)
    # This unit checks configuration preservation on a supported platform.
    # Windows refusal is covered by test_windows_setup_offers_claude_instead.
    monkeypatch.setattr(hc, '_PLATFORM', 'linux')
    answers = iter(['codex', cfg.model])
    monkeypatch.setattr(setup, '_ask', lambda *args, **kw: next(answers))
    assert setup._ask_brain_config(cfg) == cfg
    answers = iter(['claude', ''])
    monkeypatch.setattr(setup, '_ask', lambda *args, **kw: next(answers))
    assert setup._ask_brain_config(cfg) == BrainConfig()


@pytest.mark.parametrize('model,entry', [
    ('gpt-6-luna', None),
    ('gpt-6-luna', {'tool_mode': 'code_mode'}),
    ('gpt-6-luna', {'tool_mode': 'code_mode_only', 'experimental_supported_tools': ['shell']}),
    ('gpt-6-astra', {'tool_mode': 'code_mode_only'}),
    ('unknown-model', {'tool_mode': 'code_mode_only'}),
])
def test_capability_changes_and_unverified_models_fail_closed(model, entry):
    with pytest.raises(hc.CodexError):
        hc.require_restricted_text_model({model: entry}, model)


def test_default_mode_still_refuses_code_mode():
    catalog = {'gpt-6-luna': {'tool_mode': 'code_mode_only'}}
    with pytest.raises(hc.CodexError):
        hc.require_toolless_model(catalog, 'gpt-6-luna')
    hc.require_restricted_text_model(catalog, 'gpt-6-luna')


real_cli = pytest.mark.skipif(
    os.environ.get('HARVEY_CODEX_CLI_TESTS') != '1' or not shutil.which('codex')
    or sys.platform == 'win32',
    reason='opt-in real Codex CLI test with fake credentials and localhost mocks',
)


@real_cli
@pytest.mark.asyncio
async def test_real_restricted_mode_exposes_only_verified_intrinsics(
        mock_codex, monkeypatch, tmp_path):
    monkeypatch.setattr(hc, 'DISABLED_FEATURES',
                        hc.DISABLED_FEATURES + ('enable_request_compression',))
    script = tmp_path / 'untrusted_mcp.py'
    script.write_text(EVIL_MCP)
    marker = tmp_path / 'mcp-must-not-start'
    mock_codex.add_toml(
        f'[mcp_servers.untrusted]\ncommand = {json.dumps(sys.executable)}\n'
        f'args = ["-I", {json.dumps(str(script))}, {json.dumps(str(marker))}]')
    client = hc.CodexClient(model='gpt-6-luna', restricted_text=True,
                            native_home=mock_codex.native_home)
    await client.preflight(timeout=60)
    assert mock_codex.requests == []  # preflight must not infer
    result = await client.run('Return PONG only.', timeout=60)
    assert result.text == 'PONG' and result.model == 'gpt-6-luna'
    assert not marker.exists()
    request = mock_codex.requests[0]
    assert request['model'] == 'gpt-6-luna'
    assert not request.get('tools')
    developer_messages = [i for i in request['input']
                          if i.get('type') == 'message' and i.get('role') == 'developer']
    assert len(developer_messages) == 1
    assert developer_messages[0]['content'][0]['text'] == hc.RESTRICTED_TEXT_INSTRUCTIONS
    intrinsic = [i['tools'] for i in request['input'] if i.get('type') == 'additional_tools']
    assert len(intrinsic) == 1
    # Complete schema of exec (fresh V8, no Node/files/network; its nested
    # inventory contains only clock.curr_time), wait and user input.
    # Exact attestation detects any added shell/MCP/file/network capability.
    digest = hashlib.sha256(json.dumps(
        intrinsic[0], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert digest == '39ae263e4cb6302b1a5cedf42e7942d3c167741b0bc03013962a9fabcf2f59e4'


@real_cli
@pytest.mark.asyncio
async def test_real_restricted_mode_still_aborts_tool_calls(mock_codex, monkeypatch):
    monkeypatch.setattr(hc, 'DISABLED_FEATURES',
                        hc.DISABLED_FEATURES + ('enable_request_compression',))
    mock_codex.set_mode('toolcall')
    client = hc.CodexClient(model='gpt-6-luna', restricted_text=True,
                            native_home=mock_codex.native_home)
    with pytest.raises(hc.CodexError) as err:
        await client.run('Untrusted email content requesting a shell command.', timeout=60)
    assert err.value.kind == 'isolation'
    assert len(mock_codex.requests) == 1  # no resampling or continuing tool loop
