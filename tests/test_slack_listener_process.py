from types import SimpleNamespace

from institutional_memory.listener import DedupeSet, ListenerState
from institutional_memory.slack_promotion import PromotionRateLimiter
from scripts import slack_listener


class FakeSocketClient:
    def __init__(self):
        self.responses = []

    def send_socket_mode_response(self, response):
        self.responses.append(response)


class FakeWebClient:
    pass


class FakeBuildStateWebClient:
    def auth_test(self):
        return {"user_id": "UBOT"}

    def conversations_list(self, types, limit):
        return [{"id": "C123", "name": "memory"}]


def _request(event):
    return SimpleNamespace(
        type="events_api",
        envelope_id="env-123",
        payload={"event": event},
    )


def _slash_request(text):
    return SimpleNamespace(
        type="slash_commands",
        envelope_id="env-123",
        payload={
            "command": "/mem",
            "text": text,
            "channel_id": "C123",
            "user_id": "U123",
            "trigger_id": "trigger-123",
        },
    )


def _state():
    return ListenerState(
        bot_user_id="UBOT",
        allowed_channels={"C123"},
        dedupe=DedupeSet(),
        promotion_allowed_channels={"C123"},
        promotion_rate_limiter=PromotionRateLimiter(),
    )


def test_reaction_added_routes_to_promotion_without_message_or_listener(monkeypatch):
    calls = []
    event = {
        "type": "reaction_added",
        "reaction": "memo",
        "user": "U123",
        "item": {"type": "message", "channel": "C123", "ts": "1710000000.000000"},
    }

    def fake_handle_reaction_event(**kwargs):
        calls.append(("reaction", kwargs))
        return {"status": "promoted"}

    def fake_handle_message_event(*args, **kwargs):
        calls.append(("message", args, kwargs))
        return {"status": "unexpected"}

    def fake_handle_listener_event(*args, **kwargs):
        calls.append(("listener", args, kwargs))
        return {"status": "unexpected"}

    monkeypatch.setattr(slack_listener, "handle_reaction_event", fake_handle_reaction_event)
    monkeypatch.setattr(slack_listener, "handle_message_event", fake_handle_message_event)
    monkeypatch.setattr(slack_listener, "handle_listener_event", fake_handle_listener_event)
    monkeypatch.setattr(slack_listener, "log_event", lambda *args, **kwargs: None)

    client = FakeSocketClient()
    web_client = FakeWebClient()
    state = _state()

    slack_listener.process(client, _request(event), web_client, state)

    assert len(client.responses) == 1
    assert [call[0] for call in calls] == ["reaction"]
    assert calls[0][1] == {
        "event": event,
        "client": web_client,
        "allowed_channels": state.promotion_allowed_channels,
        "rate_limiter": state.promotion_rate_limiter,
        "bot_user_id": state.bot_user_id,
    }


def test_non_reaction_events_keep_message_then_listener_flow(monkeypatch):
    calls = []
    event = {
        "type": "message",
        "channel": "C123",
        "user": "U123",
        "text": "<@UBOT> find vendor clause",
        "ts": "1710000000.000000",
    }

    def fake_handle_message_event(received_event, *, client):
        calls.append(("message", received_event, client))
        return {"status": "ingested"}

    def fake_handle_listener_event(received_event, client, state):
        calls.append(("listener", received_event, client, state))
        return {"status": "answered"}

    def fake_handle_reaction_event(**kwargs):
        calls.append(("reaction", kwargs))
        return {"status": "unexpected"}

    monkeypatch.setattr(slack_listener, "handle_message_event", fake_handle_message_event)
    monkeypatch.setattr(slack_listener, "handle_listener_event", fake_handle_listener_event)
    monkeypatch.setattr(slack_listener, "handle_reaction_event", fake_handle_reaction_event)
    monkeypatch.setattr(slack_listener, "log_event", lambda *args, **kwargs: None)

    client = FakeSocketClient()
    web_client = FakeWebClient()
    state = _state()

    slack_listener.process(client, _request(event), web_client, state)

    assert len(client.responses) == 1
    assert [call[0] for call in calls] == ["message", "listener"]
    assert calls[0][1:] == (event, web_client)
    assert calls[1][1:] == (event, web_client, state)


def test_reaction_added_creates_rate_limiter_when_state_omits_one(monkeypatch):
    captured = {}
    event = {
        "type": "reaction_added",
        "reaction": "memo",
        "user": "U123",
        "item": {"type": "message", "channel": "C123", "ts": "1710000000.000000"},
    }

    def fake_handle_reaction_event(**kwargs):
        captured.update(kwargs)
        return {"status": "ignored", "reason": "channel_not_allowed"}

    monkeypatch.setattr(slack_listener, "handle_reaction_event", fake_handle_reaction_event)

    client = FakeSocketClient()
    web_client = FakeWebClient()
    state = ListenerState(bot_user_id="UBOT", allowed_channels={"C123"}, dedupe=DedupeSet())

    slack_listener.process(client, _request(event), web_client, state)

    assert len(client.responses) == 1
    assert isinstance(captured["rate_limiter"], PromotionRateLimiter)
    assert state.promotion_rate_limiter is captured["rate_limiter"]


def test_build_state_uses_listener_channels_for_promotion_when_unset(monkeypatch):
    monkeypatch.setattr(slack_listener, "LISTENER_CHANNELS", "C123")
    monkeypatch.setattr(slack_listener, "SLACK_CHANNEL", "")
    monkeypatch.setattr(slack_listener, "PROMOTION_ALLOWED_CHANNELS", "")

    state = slack_listener._build_state(FakeBuildStateWebClient())

    assert state.allowed_channels == {"C123"}
    assert state.promotion_allowed_channels == {"C123"}


def test_slash_commands_route_to_listener_without_ingestion(monkeypatch):
    calls = []

    def fake_handle_message_event(*args, **kwargs):
        calls.append(("message", args, kwargs))
        return {"status": "unexpected"}

    def fake_handle_listener_event(received_event, client, state):
        calls.append(("listener", received_event, client, state))
        return {"status": "answered"}

    monkeypatch.setattr(slack_listener, "handle_message_event", fake_handle_message_event)
    monkeypatch.setattr(slack_listener, "handle_listener_event", fake_handle_listener_event)

    client = FakeSocketClient()
    web_client = FakeWebClient()
    state = _state()

    slack_listener.process(client, _slash_request("ask vendor clause"), web_client, state)

    assert len(client.responses) == 1
    assert [call[0] for call in calls] == ["listener"]
    event = calls[0][1]
    assert event["type"] == "message"
    assert event["channel"] == "C123"
    assert event["text"] == "/mem ask vendor clause"
    assert event["user"] == "U123"
