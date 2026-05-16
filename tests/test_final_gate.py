import json

from scripts import final_gate


def test_audit_blocks_generic_queries(tmp_path, monkeypatch):
    audit = tmp_path / "audit_log.jsonl"
    audit.write_text(
        json.dumps({"type": "memory_searched", "driver": "openclaw", "query": "RFP draft"})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(final_gate, "AUDIT_LOG", audit)

    blockers = final_gate.audit_blockers()

    assert "generic search query: RFP draft" in blockers


def test_audit_blocks_full_draft_style_queries(tmp_path, monkeypatch):
    audit = tmp_path / "audit_log.jsonl"
    query = " ".join(f"word{i}" for i in range(30))
    audit.write_text(
        json.dumps({"type": "memory_searched", "driver": "openclaw", "query": query})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(final_gate, "AUDIT_LOG", audit)

    blockers = final_gate.audit_blockers()

    assert any(item.startswith("query not focused 2-6 words:") for item in blockers)
    assert any(item.startswith("full-draft-style search query:") for item in blockers)


def test_audit_requires_success_and_silent_case(tmp_path, monkeypatch):
    audit = tmp_path / "audit_log.jsonl"
    events = [
        {"type": "draft_listed", "driver": "openclaw"},
        {"type": "draft_read", "driver": "openclaw"},
        {"type": "memory_searched", "driver": "openclaw", "query": "RFP liability indemnification", "count": 1, "source": "corpus/2023_rfp_postmortem.txt"},
        {"type": "memory_searched", "driver": "openclaw", "query": "clinical trial dermatology", "count": 0},
        {"type": "slack_sent", "driver": "openclaw", "status": "sent"},
        {"type": "processed", "driver": "openclaw", "status": "sent"},
    ]
    audit.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
    monkeypatch.setattr(final_gate, "AUDIT_LOG", audit)

    blockers = final_gate.audit_blockers()

    assert "missing silent-case processed proof" in blockers


def test_audit_requires_silent_zero_hit_search_proof(tmp_path, monkeypatch):
    audit = tmp_path / "audit_log.jsonl"
    events = [
        {"type": "draft_listed", "driver": "openclaw"},
        {"type": "draft_read", "driver": "openclaw"},
        {
            "type": "memory_searched",
            "driver": "openclaw",
            "query": "RFP liability indemnification",
            "count": 1,
            "source": "corpus/2023_rfp_postmortem.txt",
        },
        {"type": "slack_sent", "driver": "openclaw", "status": "sent"},
        {"type": "processed", "driver": "openclaw", "status": "sent"},
        {"type": "processed", "driver": "openclaw", "status": "skipped_no_relevant_memory"},
    ]
    audit.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
    monkeypatch.setattr(final_gate, "AUDIT_LOG", audit)

    blockers = final_gate.audit_blockers()

    assert "missing silent zero-hit search proof" in blockers


def test_audit_requires_success_positive_hit_search_proof(tmp_path, monkeypatch):
    audit = tmp_path / "audit_log.jsonl"
    events = [
        {"type": "draft_listed", "driver": "openclaw"},
        {"type": "draft_read", "driver": "openclaw"},
        {"type": "memory_searched", "driver": "openclaw", "query": "clinical trial dermatology", "count": 0},
        {"type": "slack_sent", "driver": "openclaw", "status": "sent"},
        {"type": "processed", "driver": "openclaw", "status": "sent"},
        {"type": "processed", "driver": "openclaw", "status": "skipped_no_relevant_memory"},
    ]
    audit.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
    monkeypatch.setattr(final_gate, "AUDIT_LOG", audit)

    blockers = final_gate.audit_blockers()

    assert "missing success positive-hit search proof" in blockers


def test_audit_requires_rfp_postmortem_source_proof(tmp_path, monkeypatch):
    audit = tmp_path / "audit_log.jsonl"
    events = [
        {"type": "draft_listed", "driver": "openclaw"},
        {"type": "draft_read", "driver": "openclaw"},
        {"type": "memory_searched", "driver": "openclaw", "query": "RFP liability indemnification", "count": 1, "source": "corpus/other.txt"},
        {"type": "memory_searched", "driver": "openclaw", "query": "clinical trial dermatology", "count": 0},
        {"type": "slack_sent", "driver": "openclaw", "status": "sent"},
        {"type": "processed", "driver": "openclaw", "status": "sent"},
        {"type": "processed", "driver": "openclaw", "status": "skipped_no_relevant_memory"},
    ]
    audit.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
    monkeypatch.setattr(final_gate, "AUDIT_LOG", audit)

    blockers = final_gate.audit_blockers()

    assert "missing RFP postmortem source proof" in blockers


def test_audit_requires_sent_slack_event(tmp_path, monkeypatch):
    audit = tmp_path / "audit_log.jsonl"
    events = [
        {"type": "draft_listed", "driver": "openclaw"},
        {"type": "draft_read", "driver": "openclaw"},
        {"type": "memory_searched", "driver": "openclaw", "query": "RFP liability indemnification", "count": 1, "source": "corpus/2023_rfp_postmortem.txt"},
        {"type": "memory_searched", "driver": "openclaw", "query": "clinical trial dermatology", "count": 0},
        {"type": "slack_sent", "driver": "openclaw", "status": "slack_failed"},
        {"type": "processed", "driver": "openclaw", "status": "sent"},
        {"type": "processed", "driver": "openclaw", "status": "skipped_no_relevant_memory"},
    ]
    audit.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
    monkeypatch.setattr(final_gate, "AUDIT_LOG", audit)

    blockers = final_gate.audit_blockers()

    assert "missing sent Slack proof" in blockers


def test_audit_reports_malformed_json_line(tmp_path, monkeypatch):
    audit = tmp_path / "audit_log.jsonl"
    audit.write_text("{not json}\n", encoding="utf-8")
    monkeypatch.setattr(final_gate, "AUDIT_LOG", audit)

    blockers = final_gate.audit_blockers()

    assert "malformed audit line 1" in blockers


def test_audit_reports_non_object_json_line(tmp_path, monkeypatch):
    audit = tmp_path / "audit_log.jsonl"
    audit.write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr(final_gate, "AUDIT_LOG", audit)

    blockers = final_gate.audit_blockers()

    assert "non-object audit line 1" in blockers


def test_main_snapshots_audit_before_child_checks(tmp_path, monkeypatch, capsys):
    audit = tmp_path / "audit_log.jsonl"
    events = [
        {"type": "draft_listed", "driver": "openclaw"},
        {"type": "draft_read", "driver": "openclaw"},
        {"type": "memory_searched", "driver": "openclaw", "query": "RFP liability indemnification", "count": 1, "source": "corpus/2023_rfp_postmortem.txt"},
        {"type": "memory_searched", "driver": "openclaw", "query": "clinical trial dermatology", "count": 0},
        {"type": "slack_sent", "driver": "openclaw", "status": "sent"},
        {"type": "processed", "driver": "openclaw", "status": "sent"},
        {"type": "processed", "driver": "openclaw", "status": "skipped_no_relevant_memory"},
    ]
    audit.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
    monkeypatch.setattr(final_gate, "AUDIT_LOG", audit)

    def fake_run(command):
        audit.unlink(missing_ok=True)
        return {"command": command, "ok": True, "stdout": "", "stderr": ""}

    monkeypatch.setattr(final_gate, "run", fake_run)

    assert final_gate.main() == 0
