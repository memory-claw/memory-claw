from unittest.mock import patch

from institutional_memory.openclaw_wake import maybe_wake_openclaw


def test_maybe_wake_openclaw_skips_non_written():
    with patch("institutional_memory.openclaw_wake.subprocess.Popen") as popen:
        maybe_wake_openclaw({"status": "skipped"})
        popen.assert_not_called()


def test_maybe_wake_openclaw_runs_cmd(monkeypatch):
    monkeypatch.setattr(
        "institutional_memory.openclaw_wake.OPENCLAW_WAKE_CMD",
        "openclaw agent prompt test",
    )
    with patch("institutional_memory.openclaw_wake.subprocess.Popen") as popen:
        with patch("institutional_memory.openclaw_wake.log_event"):
            maybe_wake_openclaw({"status": "written", "path": "company/inbox/slack/x.md"})
    popen.assert_called_once()
