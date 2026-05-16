import subprocess
import time

from scripts import dgx_check


def slow_ready_probe():
    time.sleep(1)
    return "READY"


def test_run_reports_timeout_as_output(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["slow"], timeout=3)

    monkeypatch.setattr(dgx_check.subprocess, "run", raise_timeout)

    code, output = dgx_check.run("slow", timeout=3)

    assert code == 124
    assert "timeout after 3s" in output


def test_model_smoke_reports_timeout(monkeypatch):
    assert dgx_check.model_smoke(slow_ready_probe, timeout_seconds=0.01) == (
        False,
        "model smoke timed out after 0.01s",
    )


def test_default_model_probe_allows_enough_tokens_for_ready(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, host):
            captured["host"] = host

        def chat(self, **kwargs):
            captured.update(kwargs)
            return {"message": {"content": "READY"}}

    monkeypatch.setattr(dgx_check.ollama, "Client", FakeClient)

    assert dgx_check.default_model_probe() == "READY"
    assert captured["options"] == {"num_predict": 64}


def test_backup_video_check_rejects_empty_placeholder(tmp_path):
    (tmp_path / "placeholder.mp4").write_bytes(b"")

    assert dgx_check.backup_video_blockers(tmp_path) == [
        "backup video is empty: placeholder.mp4"
    ]

    (tmp_path / "real.mp4").write_bytes(b"video bytes")

    assert dgx_check.backup_video_blockers(tmp_path) == []


def test_slack_secret_check_rejects_example_token():
    assert dgx_check.slack_secret_blockers("xoxb-your-token-here", "#institutional-memory") == [
        "SLACK_BOT_TOKEN is still the .env.example placeholder"
    ]


def test_slack_secret_check_accepts_configured_values():
    assert dgx_check.slack_secret_blockers("xoxb-real-looking-token", "#institutional-memory") == []


def test_slack_secret_check_requires_explicit_channel():
    assert dgx_check.slack_secret_blockers("xoxb-real-looking-token") == [
        "SLACK_CHANNEL missing"
    ]
