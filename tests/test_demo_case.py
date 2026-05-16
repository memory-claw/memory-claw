from pathlib import Path

from scripts import demo_case


def test_silent_case_replaces_inbox_with_clinical_trial_draft(tmp_path, monkeypatch):
    inbox = tmp_path / "company" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "new_rfp_draft.txt").write_text("old rfp", encoding="utf-8")
    (inbox / ".gitkeep").write_text("", encoding="utf-8")
    monkeypatch.setattr(demo_case, "DEMO_INBOX_PATH", inbox)

    written = demo_case.write_case("silent")

    assert written == inbox / "000_silent_clinical_trial_protocol.txt"
    assert written.exists()
    assert "Clinical Trial Protocol Draft" in written.read_text(encoding="utf-8")
    assert not (inbox / "new_rfp_draft.txt").exists()
    assert (inbox / ".gitkeep").exists()


def test_rfp_case_restores_only_seed_rfp_draft(tmp_path, monkeypatch):
    inbox = tmp_path / "company" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "000_silent_clinical_trial_protocol.txt").write_text("old silent", encoding="utf-8")
    (inbox / "scratch.md").write_text("remove me", encoding="utf-8")
    monkeypatch.setattr(demo_case, "DEMO_INBOX_PATH", inbox)

    written = demo_case.write_case("rfp")

    assert written == inbox / "new_rfp_draft.txt"
    body = written.read_text(encoding="utf-8")
    assert "clause 7.4" in body
    assert "indemnification" in body
    assert not (inbox / "000_silent_clinical_trial_protocol.txt").exists()
    assert not (inbox / "scratch.md").exists()
