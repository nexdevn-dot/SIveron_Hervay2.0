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
