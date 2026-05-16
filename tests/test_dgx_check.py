import subprocess

from scripts import dgx_check


def test_run_reports_timeout_as_output(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["slow"], timeout=3)

    monkeypatch.setattr(dgx_check.subprocess, "run", raise_timeout)

    code, output = dgx_check.run("slow", timeout=3)

    assert code == 124
    assert "timeout after 3s" in output
