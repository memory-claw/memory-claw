import time
from unittest.mock import MagicMock, patch

from institutional_memory.listener import (
    DedupeSet,
    ListenerState,
    build_thread_context,
    build_search_query,
    format_no_hits_reply,
    format_reply,
    handle_listener_event,
    resolve_channels,
    select_threshold,
    should_skip,
    strip_mention,
)


def test_should_skip_bot_id():
    assert should_skip({"bot_id": "B123", "text": "hello world"}, "U999") is True


def test_should_skip_own_user():
    assert should_skip({"user": "U999", "text": "hello world"}, "U999") is True


def test_should_skip_subtype():
    assert should_skip({"subtype": "message_changed", "text": "hello world"}, "U999") is True


def test_should_skip_short_message():
    assert should_skip({"user": "U123", "text": "ok"}, "U999") is True


def test_should_skip_empty_text():
    assert should_skip({"user": "U123"}, "U999") is True


def test_should_not_skip_normal_message():
    assert should_skip({"user": "U123", "text": "What was our Q3 strategy?"}, "U999") is False


def test_should_not_skip_exactly_5_chars():
    assert should_skip({"user": "U123", "text": "hello"}, "U999") is False


def test_dedupe_first_seen_returns_false():
    d = DedupeSet(max_size=10, ttl_seconds=60)
    assert d.seen("C123", "1710000000.000000") is False


def test_dedupe_repeat_returns_true():
    d = DedupeSet(max_size=10, ttl_seconds=60)
    d.seen("C123", "1710000000.000000")
    assert d.seen("C123", "1710000000.000000") is True


def test_dedupe_different_channel_same_ts():
    d = DedupeSet(max_size=10, ttl_seconds=60)
    d.seen("C123", "1710000000.000000")
    assert d.seen("C456", "1710000000.000000") is False


def test_dedupe_evicts_oldest_when_full():
    d = DedupeSet(max_size=2, ttl_seconds=60)
    d.seen("C1", "ts1")
    d.seen("C2", "ts2")
    d.seen("C3", "ts3")
    assert d.seen("C1", "ts1") is False
    assert d.seen("C3", "ts3") is True


def test_dedupe_ttl_expiry(monkeypatch):
    d = DedupeSet(max_size=10, ttl_seconds=1)
    d.seen("C123", "ts1")
    original_time = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: original_time() + 2)
    assert d.seen("C123", "ts1") is False


# --- Task 2: Channel allowlist and threshold selection ---


def test_threshold_mention():
    assert select_threshold(is_mention=True, is_active_thread=False) == 0.60


def test_threshold_active_thread():
    assert select_threshold(is_mention=False, is_active_thread=True) == 0.65


def test_threshold_unprompted():
    assert select_threshold(is_mention=False, is_active_thread=False) == 0.80


def test_threshold_mention_overrides_thread():
    assert select_threshold(is_mention=True, is_active_thread=True) == 0.60


class FakeWebClient:
    def __init__(self, channels):
        self._channels = channels

    def conversations_list(self, types, limit):
        return {"channels": self._channels}


def test_resolve_channels_passes_through_ids():
    client = FakeWebClient([])
    result = resolve_channels("C123,C456", fallback_channel="#general", client=client)
    assert result == {"C123", "C456"}


def test_resolve_channels_converts_names_to_ids():
    client = FakeWebClient([
        {"id": "C123", "name": "general"},
        {"id": "C456", "name": "random"},
    ])
    result = resolve_channels("#general,#random", fallback_channel="", client=client)
    assert result == {"C123", "C456"}


def test_resolve_channels_mixed_names_and_ids():
    client = FakeWebClient([
        {"id": "C123", "name": "general"},
    ])
    result = resolve_channels("C456,#general", fallback_channel="", client=client)
    assert result == {"C123", "C456"}


def test_resolve_channels_empty_uses_fallback():
    client = FakeWebClient([
        {"id": "C789", "name": "institutional-memory"},
    ])
    result = resolve_channels("", fallback_channel="#institutional-memory", client=client)
    assert result == {"C789"}


def test_resolve_channels_fallback_is_id():
    client = FakeWebClient([])
    result = resolve_channels("", fallback_channel="C789", client=client)
    assert result == {"C789"}


def test_resolve_channels_unresolved_name_raises():
    client = FakeWebClient([
        {"id": "C123", "name": "general"},
    ])
    try:
        resolve_channels("#nonexistent", fallback_channel="", client=client)
        assert False, "should have raised"
    except ValueError as exc:
        assert "nonexistent" in str(exc)


# --- Task 3: Query building ---


def test_strip_mention_removes_bot_id():
    assert strip_mention("<@U999> what is our policy?", "U999") == "what is our policy?"


def test_strip_mention_no_mention():
    assert strip_mention("what is our policy?", "U999") == "what is our policy?"


def test_strip_mention_multiple():
    assert strip_mention("<@U999> hey <@U999> help", "U999") == "hey  help"


class FakeRepliesClient:
    def __init__(self, replies):
        self._replies = replies
        self.calls = []

    def conversations_replies(self, channel, ts, limit, cursor=None):
        self.calls.append({"channel": channel, "ts": ts, "limit": limit, "cursor": cursor})
        return {"messages": self._replies[:limit]}


class FakeFailingRepliesClient:
    def conversations_replies(self, channel, ts, limit):
        raise Exception("API error")


class FakePaginatedRepliesClient:
    def __init__(self, pages):
        self._pages = pages
        self.calls = []

    def conversations_replies(self, channel, ts, limit, cursor=None):
        self.calls.append({"channel": channel, "ts": ts, "limit": limit, "cursor": cursor})
        page_index = int(cursor or 0)
        next_index = page_index + 1
        next_cursor = str(next_index) if next_index < len(self._pages) else ""
        return {
            "messages": self._pages[page_index],
            "response_metadata": {"next_cursor": next_cursor},
        }


def test_query_top_level_strips_mention():
    event = {"channel": "C123", "text": "<@U999> what is our Q3 strategy?", "ts": "1.0"}
    query = build_search_query(event, bot_user_id="U999", client=None)
    assert query == "what is our Q3 strategy?"


def test_query_thread_includes_human_context():
    event = {"channel": "C123", "text": "what about Q4?", "ts": "2.0", "thread_ts": "1.0"}
    replies = [
        {"user": "U123", "text": "Q3 was great for retention"},
        {"user": "U999", "text": "Here is what I found..."},
        {"user": "U123", "text": "what about Q4?"},
    ]
    client = FakeRepliesClient(replies)
    query = build_search_query(event, bot_user_id="U999", client=client)
    assert "Q3 was great for retention" in query
    assert "Here is what I found" not in query
    assert "what about Q4?" in query


def test_query_thread_filters_bot_id_messages():
    event = {"channel": "C123", "text": "more info?", "ts": "2.0", "thread_ts": "1.0"}
    replies = [
        {"user": "U123", "text": "original question"},
        {"bot_id": "B456", "text": "bot noise"},
        {"user": "U123", "text": "more info?"},
    ]
    client = FakeRepliesClient(replies)
    query = build_search_query(event, bot_user_id="U999", client=client)
    assert "bot noise" not in query


def test_query_thread_caps_context_at_2000_chars():
    event = {"channel": "C123", "text": "summarize", "ts": "2.0", "thread_ts": "1.0"}
    replies = [{"user": "U123", "text": "x" * 3000}]
    client = FakeRepliesClient(replies)
    query = build_search_query(event, bot_user_id="U999", client=client)
    assert len(query) <= 2100


def test_query_thread_api_failure_falls_back():
    event = {"channel": "C123", "text": "<@U999> help me", "ts": "2.0", "thread_ts": "1.0"}
    client = FakeFailingRepliesClient()
    query = build_search_query(event, bot_user_id="U999", client=client)
    assert query == "help me"


def test_thread_context_prefers_recent_human_messages():
    event = {"channel": "C123", "text": "latest?", "ts": "2.0", "thread_ts": "1.0"}
    replies = [{"user": "U123", "text": f"message {i}"} for i in range(12)]
    client = FakeRepliesClient(replies)

    context = build_thread_context(event, bot_user_id="U999", client=client)

    assert "message 0" not in context
    assert "message 11" in context


def test_thread_context_paginates_before_selecting_recent_messages():
    event = {"channel": "C123", "text": "latest?", "ts": "2.0", "thread_ts": "1.0"}
    client = FakePaginatedRepliesClient(
        [
            [{"user": "U123", "text": f"old {i}"} for i in range(100)],
            [{"user": "U123", "text": f"recent {i}"} for i in range(12)],
        ]
    )

    context = build_thread_context(event, bot_user_id="U999", client=client)

    assert "old 99" not in context
    assert "recent 11" in context
    assert client.calls[1]["cursor"] == "1"


def test_thread_context_caps_at_2000_chars_and_filters_bots():
    event = {"channel": "C123", "text": "summarize", "ts": "2.0", "thread_ts": "1.0"}
    replies = [
        {"bot_id": "B456", "text": "bot noise"},
        {"user": "U123", "text": "x" * 3000},
    ]
    client = FakeRepliesClient(replies)

    context = build_thread_context(event, bot_user_id="U999", client=client)

    assert "bot noise" not in context
    assert len(context) == 2000


def test_thread_context_trims_to_newline_boundary():
    event = {"channel": "C123", "text": "latest?", "ts": "2.0", "thread_ts": "1.0"}
    replies = [
        {"user": "U123", "text": "old " + ("x" * 100)},
        {"user": "U123", "text": "recent one"},
        {"user": "U123", "text": "recent two"},
    ]
    client = FakeRepliesClient(replies)

    context = build_thread_context(event, bot_user_id="U999", client=client, max_chars=30)

    assert context == "recent one\nrecent two"


# --- Task 4: Reply formatting ---


def test_format_reply_single_hit():
    hits = [{"score": 0.87, "text": "Our retention strategy shifted to product-led growth", "source": "company/corpus/q3_strategy.md"}]
    result = format_reply(hits)
    assert "87%" in result
    assert "q3_strategy.md" in result
    assert "retention strategy" in result


def test_format_reply_multiple_hits():
    hits = [
        {"score": 0.87, "text": "Retention strategy", "source": "company/corpus/q3.md"},
        {"score": 0.74, "text": "PLG metrics improved", "source": "company/corpus/plg.md"},
        {"score": 0.68, "text": "Onboarding changes", "source": "company/corpus/onboard.md"},
    ]
    result = format_reply(hits)
    assert "87%" in result
    assert "74%" in result
    assert "68%" in result
    assert result.count("—") == 3


def test_format_reply_caps_at_3_hits():
    hits = [
        {"score": 0.9, "text": "A", "source": "a.md"},
        {"score": 0.8, "text": "B", "source": "b.md"},
        {"score": 0.7, "text": "C", "source": "c.md"},
        {"score": 0.6, "text": "D", "source": "d.md"},
    ]
    result = format_reply(hits)
    assert "d.md" not in result


def test_format_reply_truncates_long_snippet():
    hits = [{"score": 0.9, "text": "x" * 300, "source": "long.md"}]
    result = format_reply(hits)
    assert "..." in result


def test_format_no_hits_reply():
    result = format_no_hits_reply()
    assert "didn't find anything relevant" in result.lower()


# --- Task 5: Main handler ---


def _make_state(allowed_channels=None, bot_user_id="UBOT"):
    return ListenerState(
        bot_user_id=bot_user_id,
        allowed_channels=allowed_channels or {"C100"},
        dedupe=DedupeSet(max_size=100, ttl_seconds=60),
        active_threads=set(),
    )


class MockWebClient:
    def __init__(self):
        self.posted = []

    def chat_postMessage(self, **kwargs):
        self.posted.append(kwargs)
        return {"ok": True}

    def conversations_replies(self, channel, ts, limit=10):
        return {"messages": []}


def test_handle_unprompted_hit_replies_in_thread():
    state = _make_state()
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "1.0", "user": "U123", "text": "What was our Q3 strategy?"}

    hits = [{"score": 0.85, "text": "Product-led growth", "source": "company/corpus/q3.md"}]
    with patch("institutional_memory.listener.search_memory", return_value=hits):
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert len(client.posted) == 1
    assert client.posted[0]["thread_ts"] == "1.0"
    assert ("C100", "1.0") in state.active_threads


def test_handle_unprompted_below_threshold_silent():
    state = _make_state()
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "1.0", "user": "U123", "text": "What was our Q3 strategy?"}

    with patch("institutional_memory.listener.search_memory", return_value=[]):
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "skipped"
    assert len(client.posted) == 0


def test_handle_mention_no_hits_replies_no_context():
    state = _make_state(allowed_channels=set())
    client = MockWebClient()
    event = {"type": "message", "channel": "C200", "ts": "1.0", "user": "U123", "text": "<@UBOT> what is our policy?"}

    with patch("institutional_memory.listener.search_memory", return_value=[]):
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert "didn't find anything" in client.posted[0]["text"].lower()


def test_handle_mention_any_channel():
    state = _make_state(allowed_channels={"C100"})
    client = MockWebClient()
    event = {"type": "message", "channel": "C999", "ts": "1.0", "user": "U123", "text": "<@UBOT> help"}

    hits = [{"score": 0.65, "text": "Help doc", "source": "help.md"}]
    with patch("institutional_memory.listener.search_memory", return_value=hits):
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"


def test_handle_non_allowed_channel_no_mention_skipped():
    state = _make_state(allowed_channels={"C100"})
    client = MockWebClient()
    event = {"type": "message", "channel": "C999", "ts": "1.0", "user": "U123", "text": "What was our Q3 strategy?"}

    with patch("institutional_memory.listener.log_event"):
        result = handle_listener_event(event, client, state)

    assert result["status"] == "skipped"
    assert result["reason"] == "not_in_allowlist"
    assert len(client.posted) == 0


def test_handle_active_thread_uses_lower_threshold():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "2.0", "thread_ts": "1.0", "user": "U123", "text": "what about Q4?"}

    hits = [{"score": 0.67, "text": "Q4 plans", "source": "q4.md"}]
    with patch("institutional_memory.listener.search_memory", return_value=hits):
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"


def test_handle_app_mention_event():
    state = _make_state(allowed_channels=set())
    client = MockWebClient()
    event = {"type": "app_mention", "channel": "C999", "ts": "1.0", "user": "U123", "text": "<@UBOT> find retention data"}

    hits = [{"score": 0.90, "text": "Retention data", "source": "retention.md"}]
    with patch("institutional_memory.listener.search_memory", return_value=hits):
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"


def test_mention_advice_on_command_updates_thread_mode_without_search():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "2.0", "thread_ts": "1.0", "user": "U123", "text": "<@UBOT> advice on"}

    with patch("institutional_memory.listener.search_memory") as search_memory:
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert state.thread_advice_modes[("C100", "1.0")] == "on"
    assert "advice mode is on" in client.posted[0]["text"].lower()
    search_memory.assert_not_called()


def test_short_yes_requires_pending_offer():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "2.0", "thread_ts": "1.0", "user": "U123", "text": "yes"}

    with patch("institutional_memory.listener.search_memory", return_value=[]) as search_memory:
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "skipped"
    assert state.thread_advice_modes == {}
    search_memory.assert_called_once()


def test_short_yes_after_pending_offer_sets_advice_on_without_search():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    state.thread_advice_offer_pending.add(("C100", "1.0"))
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "2.0", "thread_ts": "1.0", "user": "U123", "text": "yes"}

    with patch("institutional_memory.listener.search_memory") as search_memory:
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert state.thread_advice_modes[("C100", "1.0")] == "on"
    search_memory.assert_not_called()


def test_short_bot_reply_in_active_thread_still_filtered():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    state.thread_advice_offer_pending.add(("C100", "1.0"))
    client = MockWebClient()
    event = {
        "type": "message",
        "channel": "C100",
        "ts": "2.0",
        "thread_ts": "1.0",
        "bot_id": "B123",
        "text": "yes",
    }

    with patch("institutional_memory.listener.search_memory") as search_memory:
        result = handle_listener_event(event, client, state)

    assert result["status"] == "skipped"
    assert result["reason"] == "filtered"
    assert state.thread_advice_modes == {}
    search_memory.assert_not_called()


def test_show_source_uses_recent_thread_refs_without_search():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    state.thread_source_refs[("C100", "1.0")] = [
        {
            "source": "company/corpus/q3.md",
            "text": "Retention strategy shifted toward product-led growth.",
            "access": "share",
        }
    ]
    client = MockWebClient()
    event = {
        "type": "message",
        "channel": "C100",
        "ts": "2.0",
        "thread_ts": "1.0",
        "user": "U123",
        "text": "show source 1",
    }

    with patch(
        "institutional_memory.listener.render_source_command",
        return_value={"status": "ok", "text": "Source 1: q3.md\n\n> Retention strategy shifted."},
    ):
        with patch("institutional_memory.listener.search_memory") as search_memory:
            with patch("institutional_memory.listener.log_event"):
                result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert result["hits"] == 0
    assert "Retention strategy shifted" in client.posted[0]["text"]
    search_memory.assert_not_called()


def test_show_source_without_recent_refs_replies_missing():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    client = MockWebClient()
    event = {
        "type": "message",
        "channel": "C100",
        "ts": "2.0",
        "thread_ts": "1.0",
        "user": "U123",
        "text": "show source 1",
    }

    with patch("institutional_memory.listener.search_memory") as search_memory:
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert "recent source list" in client.posted[0]["text"].lower()
    search_memory.assert_not_called()


def test_show_full_source_cooldown():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    state.thread_source_refs[("C100", "1.0")] = [
        {"source": "company/corpus/q3.md", "text": "Retention strategy", "access": "share"}
    ]
    state.thread_full_source_cooldowns[("C100", "1.0", 1)] = time.monotonic()
    client = MockWebClient()
    event = {
        "type": "message",
        "channel": "C100",
        "ts": "2.0",
        "thread_ts": "1.0",
        "user": "U123",
        "text": "show full source 1",
    }

    with patch("institutional_memory.listener.search_memory") as search_memory:
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "replied"
    assert "wait" in client.posted[0]["text"].lower()
    search_memory.assert_not_called()


def test_advice_command_post_failure_does_not_mutate_mode():
    state = _make_state()
    state.active_threads.add(("C100", "1.0"))
    state.thread_advice_offer_pending.add(("C100", "1.0"))
    client = MockWebClient()
    client.chat_postMessage = MagicMock(side_effect=Exception("Slack down"))
    event = {
        "type": "message",
        "channel": "C100",
        "ts": "2.0",
        "thread_ts": "1.0",
        "user": "U123",
        "text": "yes",
    }

    with patch("institutional_memory.listener.search_memory") as search_memory:
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "error"
    assert state.thread_advice_modes == {}
    assert ("C100", "1.0") in state.thread_advice_offer_pending
    search_memory.assert_not_called()


def test_handle_search_failure_no_crash():
    state = _make_state()
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "1.0", "user": "U123", "text": "What was our strategy?"}

    with patch("institutional_memory.listener.search_memory", side_effect=Exception("Ollama down")):
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "error"
    assert len(client.posted) == 0


def test_handle_post_failure_no_crash():
    state = _make_state()
    client = MockWebClient()
    client.chat_postMessage = MagicMock(side_effect=Exception("Slack down"))
    event = {"type": "message", "channel": "C100", "ts": "1.0", "user": "U123", "text": "What was our strategy?"}

    hits = [{"score": 0.85, "text": "Strategy doc", "source": "strat.md"}]
    with patch("institutional_memory.listener.search_memory", return_value=hits):
        with patch("institutional_memory.listener.log_event"):
            result = handle_listener_event(event, client, state)

    assert result["status"] == "error"


def test_handle_dedupe_skips_repeat():
    state = _make_state()
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "1.0", "user": "U123", "text": "What was our strategy?"}

    hits = [{"score": 0.85, "text": "Strategy", "source": "s.md"}]
    with patch("institutional_memory.listener.search_memory", return_value=hits):
        with patch("institutional_memory.listener.log_event"):
            handle_listener_event(event, client, state)
            result = handle_listener_event(event, client, state)

    assert result["status"] == "skipped"
    assert result["reason"] == "dedupe"


def test_handle_bot_message_skipped():
    state = _make_state()
    client = MockWebClient()
    event = {"type": "message", "channel": "C100", "ts": "1.0", "bot_id": "B123", "text": "automated message here"}

    with patch("institutional_memory.listener.log_event"):
        result = handle_listener_event(event, client, state)

    assert result["status"] == "skipped"
