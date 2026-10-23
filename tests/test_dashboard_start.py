"""Starting from the dashboard dispatches the run command, without real agents."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import harvey.dashboard as dashboard


@pytest.mark.asyncio
async def test_dashboard_start_dispatches_run(tmp_path,monkeypatch):
    monkeypatch.setattr(dashboard,'PROJECT_ROOT',tmp_path)
    monkeypatch.setattr(dashboard,'LOG_FILE',tmp_path/'agent.log')
    monkeypatch.setattr(dashboard,'PID_FILE',tmp_path/'agent.pid')
    monkeypatch.setattr(dashboard,'_check_harvey_pid',lambda:None)
    monkeypatch.setattr(dashboard,'_harvey_process',None)
    monkeypatch.setattr(dashboard,'_harvey_started_at',None)
    launch=Mock(return_value=SimpleNamespace(pid=12345))
    monkeypatch.setattr(dashboard.subprocess,'Popen',launch)
    result=await dashboard.start_harvey()
    assert result['success']
    assert launch.call_args.args[0]==[dashboard.sys.executable,'-m','harvey','run']
    assert launch.call_args.kwargs['cwd']==str(tmp_path)
    assert (tmp_path/'agent.pid').read_text()=='12345'
