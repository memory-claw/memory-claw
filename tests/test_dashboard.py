import dashboard.app as dashboard_app


def test_infer_document_type_all_categories():
    cases = {
        "company/inbox/security_policy.md": "policy",
        "company/inbox/api_incident.md": "postmortem",
        "company/inbox/vendor_clause.txt": "contract",
        "company/inbox/slack/C123.md": "slack",
        "company/inbox/customer_bid.md": "rfp",
        "company/inbox/new_feature_draft.md": "draft",
        "company/inbox/lunch_notes.md": "other",
    }
    for path, expected in cases.items():
        assert dashboard_app._infer_document_type(path) == expected, f"{path} → expected {expected}"


def test_run_ingest_returns_ok_field(monkeypatch):
    monkeypatch.setattr(
        dashboard_app,
        "ingest_folder",
        lambda folder, force: {"files": 0, "chunks": 0},
    )
    monkeypatch.setattr(dashboard_app, "_load_ingested", lambda: {})
    monkeypatch.setattr(dashboard_app, "_list_corpus_paths", lambda: [])

    result = dashboard_app.api_run_ingest()
    assert result["ok"] is True


def test_run_ingest_returns_error_on_exception(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("chroma offline")

    monkeypatch.setattr(dashboard_app, "_load_ingested", boom)

    result = dashboard_app.api_run_ingest()
    assert result["ok"] is False
    assert "chroma offline" in result["error"]
