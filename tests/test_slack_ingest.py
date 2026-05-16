import pytest

from institutional_memory import paths, slack_ingest


def test_thread_file_name_uses_channel_and_parent_thread_ts():
    event = {"channel": "C123", "ts": "1710000001.000000", "thread_ts": "1710000000.000000"}

    assert slack_ingest.thread_file_name(event) == "C123_1710000000.000000.md"


def test_thread_file_name_uses_message_ts_without_thread_ts():
    event = {"channel": "C123", "ts": "1710000001.000000"}

    assert slack_ingest.thread_file_name(event) == "C123_1710000001.000000.md"


def test_should_ignore_bot_message():
    assert slack_ingest.should_ignore_event({"bot_id": "B123"}) is True
    assert slack_ingest.should_ignore_event({"subtype": "bot_message"}) is True
    assert slack_ingest.should_ignore_event({"user": "U123", "text": "hello"}) is False


class FakeSlackClient:
    def conversations_history(self, channel, limit):
        return {
            "messages": [
                {"channel": channel, "ts": "1710000000.000000", "user": "U123", "text": "Need precedent"},
                {"channel": channel, "ts": "1710000002.000000", "bot_id": "B123", "text": "ignore bot"},
            ]
        }

    def conversations_replies(self, channel, ts):
        return {"messages": [{"channel": channel, "ts": ts, "user": "U123", "text": "Need precedent"}]}

    def chat_getPermalink(self, channel, message_ts):
        return {"permalink": f"https://example.slack.com/archives/{channel}/p{message_ts.replace('.', '')}"}


def test_render_thread_markdown_contains_metadata_and_unescaped_messages():
    messages = [
        {"user": "U123", "text": "Need NHS &amp; liability precedent", "ts": "1710000000.000000"},
        {"user": "U456", "text": "Check old postmortem", "ts": "1710000001.000000"},
    ]

    text = slack_ingest.render_thread_markdown(
        channel="C123",
        thread_ts_value="1710000000.000000",
        messages=messages,
        permalink="https://example.slack.com/archives/C123/p1710000000000000",
        imported_at="2026-05-16T00:00:00+00:00",
    )

    assert "# Slack Thread: Need NHS & liability precedent" in text
    assert "**Channel:** C123" in text
    assert "**Thread TS:** 1710000000.000000" in text
    assert "**Permalink:** https://example.slack.com/archives/C123/p1710000000000000" in text
    assert "- 1710000000.000000 U123: Need NHS & liability precedent" in text


def _patch_slack_ingest_paths(monkeypatch, tmp_path):
    company_inbox = tmp_path / "company" / "inbox"
    company_corpus = tmp_path / "company" / "corpus"
    monkeypatch.setattr(slack_ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(slack_ingest, "COMPANY_INBOX_PATH", company_inbox)
    monkeypatch.setattr(slack_ingest, "COMPANY_CORPUS_PATH", company_corpus)
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(paths, "COMPANY_INBOX_PATH", company_inbox)
    monkeypatch.setattr(paths, "COMPANY_CORPUS_PATH", company_corpus)
    return company_inbox, company_corpus


def test_sync_slack_history_writes_inbox_files(tmp_path, monkeypatch):
    _patch_slack_ingest_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(slack_ingest, "load_processed_records", lambda: [])

    result = slack_ingest.sync_slack_history(mode="inbox", channel="C123", limit=20, client=FakeSlackClient(), sleep_seconds=0)

    assert result["status"] == "ok"
    assert result["written"] == ["company/inbox/slack/C123_1710000000.000000.md"]


def test_sync_slack_history_corpus_includes_ingest_reminder(tmp_path, monkeypatch):
    _patch_slack_ingest_paths(monkeypatch, tmp_path)

    result = slack_ingest.sync_slack_history(mode="corpus", channel="C123", limit=20, client=FakeSlackClient(), sleep_seconds=0)

    assert result["written"] == ["company/corpus/slack/C123_1710000000.000000.md"]
    assert "ingest_corpus.py --force" in result["note"]


def test_promote_slack_thread_rejects_non_slack_inbox_file(tmp_path, monkeypatch):
    company_inbox, company_corpus = _patch_slack_ingest_paths(monkeypatch, tmp_path)
    company_inbox.mkdir(parents=True)
    (company_inbox / "ordinary.md").write_text("not a Slack import", encoding="utf-8")

    with pytest.raises(slack_ingest.PathNotAllowedError):
        slack_ingest.promote_slack_thread("company/inbox/ordinary.md")


def test_handle_socket_event_writes_inbox_thread(tmp_path, monkeypatch):
    _patch_slack_ingest_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(slack_ingest, "load_processed_records", lambda: [])

    event = {"type": "message", "channel": "C123", "ts": "1710000000.000000", "user": "U123", "text": "Need precedent"}
    result = slack_ingest.handle_message_event(event, client=FakeSlackClient())

    assert result["status"] == "written"
    assert result["path"] == "company/inbox/slack/C123_1710000000.000000.md"
