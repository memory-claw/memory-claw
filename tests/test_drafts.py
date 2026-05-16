from institutional_memory import drafts, paths


def test_read_draft_returns_slack_thread_metadata(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    draft_path = inbox / "slack" / "C123_1710000000.000000.md"
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
    monkeypatch.setattr(drafts, "INBOX_PATH", inbox)
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(paths, "INBOX_PATH", inbox)

    payload = drafts.read_draft("inbox/slack/C123_1710000000.000000.md")

    assert payload["path"] == "inbox/slack/C123_1710000000.000000.md"
    assert payload["slack_channel_id"] == "C123"
    assert payload["slack_thread_ts"] == "1710000000.000000"
    assert payload["slack_permalink"] == "https://example.slack.com/archives/C123/p1710000000000000"


def test_list_new_drafts_finds_nested_slack_files(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    draft_path = inbox / "slack" / "C123_1710000000.000000.md"
    draft_path.parent.mkdir(parents=True)
    draft_path.write_text("Slack thread", encoding="utf-8")
    monkeypatch.setattr(drafts, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(drafts, "INBOX_PATH", inbox)
    monkeypatch.setattr(drafts, "load_processed_records", lambda: [])

    assert drafts.list_new_drafts() == ["inbox/slack/C123_1710000000.000000.md"]
