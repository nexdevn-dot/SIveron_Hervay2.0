"""Missing optional competitive knowledge is normal; core warnings stay visible."""
import pytest
import harvey.brain as module


@pytest.mark.parametrize('agent',['writer','handler'])
@pytest.mark.parametrize('optional_present',[False,True])
def test_optional_competitive_knowledge(tmp_path,monkeypatch,caplog,agent,optional_present):
    monkeypatch.setattr(module,'SKILLS_DIR',tmp_path)
    names=('email_frameworks','signal_playbook','sales_methodology','offer_strategy','product_knowledge','objection_handling')
    for name in names: (tmp_path/(name+'.md')).write_text('Skill '+name)
    if optional_present: (tmp_path/'competitive_intel.md').write_text('Known competitor facts')
    brain=module.Brain.__new__(module.Brain)
    result=brain.load_skills_for_agent(agent)
    assert ('Known competitor facts' in result)==optional_present
    assert 'Skill product_knowledge' in result
    assert not caplog.records
    (tmp_path/'product_knowledge.md').unlink()
    brain.load_skills_for_agent(agent)
    assert 'product_knowledge.md' in caplog.text
    assert 'competitive_intel.md' not in caplog.text


@pytest.mark.parametrize('kind', ['prompt', 'skill'])
def test_authored_context_is_utf8_on_windows_locale(tmp_path, monkeypatch, kind):
    from pathlib import Path
    content = 'Geschäftsführer — Grüße 日本語 {{name}}'
    (tmp_path/'example.md').write_bytes(content.encode('utf-8'))
    monkeypatch.setattr(module, 'PROMPTS_DIR', tmp_path)
    monkeypatch.setattr(module, 'SKILLS_DIR', tmp_path)
    read_text = Path.read_text
    def windows_read_text(path, encoding=None, errors=None, **kwargs):
        return read_text(path, encoding=encoding or 'cp1252', errors=errors, **kwargs)
    monkeypatch.setattr(Path, 'read_text', windows_read_text)
    brain = module.Brain.__new__(module.Brain)
    result = brain.load_prompt('example', name='Bao') if kind == 'prompt' else brain.load_skill('example')
    assert result == (content.replace('{{name}}', 'Bao') if kind == 'prompt' else content)
