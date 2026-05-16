from institutional_memory import drafts, paths


def test_read_draft_returns_slack_thread_metadata(tmp_path, monkeypatch):
    company_inbox = tmp_path / "company" / "inbox"
    draft_path = company_inbox / "slack" / "C123_1710000000.000000.md"
    draft_path.parent.mkdir(parents=True)
    draft_path.write_text(
        "\n".join(
            [
                "# Slack Thread: pricing review",
                "",
                "**Channel:** C123",
                "**Thread TS:** 1710000000.000000",
                "**Permalink:** https://example.slack.com/archives/C123/p1710000000000000",
                "",
                "## Messages",
                "",
                "- 1710000000.000000 U123: Review this bid.",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(drafts, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(drafts, "COMPANY_INBOX_PATH", company_inbox)
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(paths, "COMPANY_INBOX_PATH", company_inbox)

    payload = drafts.read_draft("company/inbox/slack/C123_1710000000.000000.md")

    assert payload["path"] == "company/inbox/slack/C123_1710000000.000000.md"
    assert payload["slack_channel_id"] == "C123"
    assert payload["slack_thread_ts"] == "1710000000.000000"
    assert payload["slack_permalink"] == "https://example.slack.com/archives/C123/p1710000000000000"


def test_list_new_drafts_finds_nested_slack_files(tmp_path, monkeypatch):
    company_inbox = tmp_path / "company" / "inbox"
    draft_path = company_inbox / "slack" / "C123_1710000000.000000.md"
    draft_path.parent.mkdir(parents=True)
    draft_path.write_text("Slack thread", encoding="utf-8")
    monkeypatch.setattr(drafts, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(drafts, "COMPANY_INBOX_PATH", company_inbox)
    monkeypatch.setattr(drafts, "load_processed_records", lambda: [])

    assert drafts.list_new_drafts() == ["company/inbox/slack/C123_1710000000.000000.md"]


def test_list_new_drafts_finds_company_parent_inbox_files(tmp_path, monkeypatch):
    company_inbox = tmp_path / "company" / "inbox"
    company_inbox.mkdir(parents=True)
    (company_inbox / "pricing_review.md").write_text("Review pricing", encoding="utf-8")
    monkeypatch.setattr(drafts, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(drafts, "COMPANY_INBOX_PATH", company_inbox)
    monkeypatch.setattr(drafts, "load_processed_records", lambda: [])

    assert drafts.list_new_drafts() == ["company/inbox/pricing_review.md"]


def test_list_new_drafts_ignores_legacy_root_inbox_files(tmp_path, monkeypatch):
    legacy_inbox = tmp_path / "inbox"
    company_inbox = tmp_path / "company" / "inbox"
    legacy_inbox.mkdir()
    company_inbox.mkdir(parents=True)
    (legacy_inbox / "legacy.md").write_text("old", encoding="utf-8")
    monkeypatch.setattr(drafts, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(drafts, "COMPANY_INBOX_PATH", company_inbox)
    monkeypatch.setattr(drafts, "load_processed_records", lambda: [])

    assert drafts.list_new_drafts() == []
