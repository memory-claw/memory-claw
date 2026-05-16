import sys

from scripts import demo_rehearsal


def test_silent_rehearsal_uses_default_threshold(monkeypatch, capsys):
    calls = []

    def fake_run_json(*args):
        calls.append(args)
        if args[0] == "reset-demo":
            return {"status": "reset"}
        if "RFP liability indemnification clause" in args:
            return [{"source": "corpus/2023_rfp_postmortem.txt"}]
        if "clinical trial dermatology placebo" in args:
            return []
        raise AssertionError(f"unexpected call: {args}")

    monkeypatch.setattr(demo_rehearsal, "run_json", fake_run_json)
    monkeypatch.setattr(sys, "argv", ["demo_rehearsal.py", "--skip-ingest"])

    assert demo_rehearsal.main() == 0

    assert ("search-memory", "--query", "clinical trial dermatology placebo") in calls
