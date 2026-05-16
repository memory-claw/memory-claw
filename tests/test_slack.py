from institutional_memory import slack
from slack_sdk.errors import SlackApiError


def test_source_attributions_find_corpus_filenames():
    text = "Review prior bid notes from corpus/2023_rfp_postmortem.txt before sending."

    assert slack.source_attributions(text) == ["corpus/2023_rfp_postmortem.txt"]


def test_source_attributions_ignore_missing_source_filename():
    assert slack.source_attributions("Review prior bid notes before sending.") == []


def test_send_slack_reports_bot_token_api_error_without_webhook(monkeypatch):
    class FakeClient:
        def __init__(self, token):
            assert token == "xoxb-test"

        def chat_postMessage(self, channel, text):
            raise SlackApiError("channel_not_found", {"error": "channel_not_found"})

    monkeypatch.setattr(slack, "SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setattr(slack, "SLACK_WEBHOOK_URL", None)
    monkeypatch.setattr(slack, "WebClient", FakeClient)

    result = slack.send_slack_message(None, None, "hello")

    assert result == {"status": "slack_failed", "error": "channel_not_found"}
