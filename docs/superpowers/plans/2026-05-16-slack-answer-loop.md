# Slack Answer Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real-time memory search and reply to the existing Socket Mode listener so the bot can answer questions from Slack using institutional memory.

**Architecture:** Extend `scripts/slack_listener.py` (raw `slack_sdk.socket_mode.SocketModeClient`) with core logic in new `institutional_memory/listener.py`. No new dependencies. Ack-first pattern preserved — all search/reply runs after Slack ack.

**Tech Stack:** slack_sdk (existing), ChromaDB + Ollama via `search_memory()` (existing), pytest

**Spec:** `docs/superpowers/specs/2026-05-16-slack-answer-loop-design.md`

---

### Task 0: Config additions

**Goal:** Add threshold and channel config vars to `config.py` and `.env.example`.

**Files:**
- Modify: `institutional_memory/config.py:34-37`
- Modify: `.env.example`

**Acceptance Criteria:**
- [ ] UNPROMPTED_THRESHOLD defaults to 0.80
- [ ] THREAD_THRESHOLD defaults to 0.65
- [ ] LISTENER_CHANNELS defaults to empty string
- [ ] .env.example documents all three new vars

**Verify:** `uv run python -c "from institutional_memory.config import UNPROMPTED_THRESHOLD, THREAD_THRESHOLD, LISTENER_CHANNELS; print(UNPROMPTED_THRESHOLD, THREAD_THRESHOLD, LISTENER_CHANNELS)"` → `0.8 0.65 `

**Steps:**

- [ ] **Step 1: Add config vars to config.py**

Add after the existing `SLACK_WEBHOOK_URL` line (line 37) in `institutional_memory/config.py`:

```python
UNPROMPTED_THRESHOLD = float(os.getenv("UNPROMPTED_THRESHOLD", "0.80"))
THREAD_THRESHOLD = float(os.getenv("THREAD_THRESHOLD", "0.65"))
LISTENER_CHANNELS = os.getenv("LISTENER_CHANNELS", "")
```

- [ ] **Step 2: Update .env.example**

Add to `.env.example` after `SLACK_WEBHOOK_URL=`:

```
LISTENER_CHANNELS=
UNPROMPTED_THRESHOLD=0.80
THREAD_THRESHOLD=0.65
```

- [ ] **Step 3: Verify imports work**

Run: `uv run python -c "from institutional_memory.config import UNPROMPTED_THRESHOLD, THREAD_THRESHOLD, LISTENER_CHANNELS; print(UNPROMPTED_THRESHOLD, THREAD_THRESHOLD, LISTENER_CHANNELS)"`
Expected: `0.8 0.65 `

- [ ] **Step 4: Run existing tests**

Run: `uv run pytest -x -q`
Expected: all pass (no regressions)

- [ ] **Step 5: Commit**

```bash
git add institutional_memory/config.py .env.example
git commit -m "feat: add listener threshold and channel config"
```

---

### Task 1: Event filtering and deduplication

**Goal:** Implement `should_skip()` and `DedupeSet` class in `listener.py` with full tests.

**Files:**
- Create: `institutional_memory/listener.py`
- Create: `tests/test_listener.py`

**Acceptance Criteria:**
- [ ] `should_skip` returns True for bot_id, own user, subtypes, short messages
- [ ] `should_skip` returns False for normal human messages >= 5 chars
- [ ] `DedupeSet` tracks `(channel, ts)` pairs with max 200 entries and 60s TTL
- [ ] `DedupeSet.seen()` returns False first time, True on repeat
- [ ] Expired entries are evicted

**Verify:** `uv run pytest tests/test_listener.py -v -k "skip or dedupe"` → all pass

**Steps:**

- [ ] **Step 1: Write failing tests for should_skip**

Create `tests/test_listener.py`:

```python
from institutional_memory.listener import should_skip


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_listener.py -v -k "skip"`
Expected: ImportError (listener module doesn't exist yet)

- [ ] **Step 3: Implement should_skip**

Create `institutional_memory/listener.py`:

```python
"""Slack listener core logic — event filtering, search, and reply."""

from __future__ import annotations

from typing import Any


def should_skip(event: dict[str, Any], bot_user_id: str) -> bool:
    if event.get("bot_id"):
        return True
    if event.get("user") == bot_user_id:
        return True
    if event.get("subtype"):
        return True
    if len(str(event.get("text", "")).strip()) < 5:
        return True
    return False
```

- [ ] **Step 4: Run should_skip tests**

Run: `uv run pytest tests/test_listener.py -v -k "skip"`
Expected: all pass

- [ ] **Step 5: Write failing tests for DedupeSet**

Append to `tests/test_listener.py`:

```python
import time

from institutional_memory.listener import DedupeSet


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
```

- [ ] **Step 6: Implement DedupeSet**

Add to `institutional_memory/listener.py`:

```python
import time
from collections import OrderedDict


class DedupeSet:
    def __init__(self, max_size: int = 200, ttl_seconds: float = 60.0) -> None:
        self._entries: OrderedDict[tuple[str, str], float] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds

    def seen(self, channel: str, ts: str) -> bool:
        key = (channel, ts)
        now = time.monotonic()
        existing = self._entries.get(key)
        if existing is not None and (now - existing) < self._ttl:
            return True
        if existing is not None:
            del self._entries[key]
        self._entries[key] = now
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_size:
            self._entries.popitem(last=False)
        return False
```

- [ ] **Step 7: Run all tests**

Run: `uv run pytest tests/test_listener.py -v -k "skip or dedupe"`
Expected: all pass

- [ ] **Step 8: Commit**

```bash
git add institutional_memory/listener.py tests/test_listener.py
git commit -m "feat: add event filtering and deduplication for listener"
```

---

### Task 2: Channel allowlist and threshold selection

**Goal:** Implement `resolve_channels()` and `select_threshold()` with tests.

**Files:**
- Modify: `institutional_memory/listener.py`
- Modify: `tests/test_listener.py`

**Acceptance Criteria:**
- [ ] `resolve_channels` converts `#names` to channel IDs via `conversations.list`
- [ ] `resolve_channels` passes through raw channel IDs (starting with `C`) unchanged
- [ ] `resolve_channels` falls back to `SLACK_CHANNEL` if `LISTENER_CHANNELS` is empty
- [ ] `select_threshold` returns 0.60 for mentions
- [ ] `select_threshold` returns 0.65 for active threads
- [ ] `select_threshold` returns 0.80 for unprompted

**Verify:** `uv run pytest tests/test_listener.py -v -k "channel or threshold"` → all pass

**Steps:**

- [ ] **Step 1: Write failing tests for select_threshold**

Append to `tests/test_listener.py`:

```python
from institutional_memory.listener import select_threshold


def test_threshold_mention():
    assert select_threshold(is_mention=True, is_active_thread=False) == 0.60


def test_threshold_active_thread():
    assert select_threshold(is_mention=False, is_active_thread=True) == 0.65


def test_threshold_unprompted():
    assert select_threshold(is_mention=False, is_active_thread=False) == 0.80


def test_threshold_mention_overrides_thread():
    assert select_threshold(is_mention=True, is_active_thread=True) == 0.60
```

- [ ] **Step 2: Implement select_threshold**

Add to `institutional_memory/listener.py`:

```python
from institutional_memory.config import (
    RELEVANCE_THRESHOLD,
    THREAD_THRESHOLD,
    UNPROMPTED_THRESHOLD,
)


def select_threshold(is_mention: bool, is_active_thread: bool) -> float:
    if is_mention:
        return RELEVANCE_THRESHOLD
    if is_active_thread:
        return THREAD_THRESHOLD
    return UNPROMPTED_THRESHOLD
```

- [ ] **Step 3: Run threshold tests**

Run: `uv run pytest tests/test_listener.py -v -k "threshold"`
Expected: all pass

- [ ] **Step 4: Write failing tests for resolve_channels**

Append to `tests/test_listener.py`:

```python
from institutional_memory.listener import resolve_channels


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
```

- [ ] **Step 5: Implement resolve_channels**

Add to `institutional_memory/listener.py`:

```python
from slack_sdk import WebClient


def resolve_channels(
    listener_channels: str,
    fallback_channel: str,
    client: Any = None,
) -> set[str]:
    raw = listener_channels.strip() if listener_channels else ""
    if not raw:
        raw = fallback_channel.strip() if fallback_channel else ""
    if not raw:
        return set()

    entries = [e.strip() for e in raw.split(",") if e.strip()]
    ids: set[str] = set()
    names_to_resolve: list[str] = []

    for entry in entries:
        if entry.startswith("C") and not entry.startswith("#"):
            ids.add(entry)
        else:
            names_to_resolve.append(entry.lstrip("#"))

    if names_to_resolve and client is not None:
        response = client.conversations_list(types="public_channel,private_channel", limit=1000)
        channel_map = {ch["name"]: ch["id"] for ch in response.get("channels", [])}
        for name in names_to_resolve:
            if name not in channel_map:
                raise ValueError(f"Could not resolve channel name: #{name}")
            ids.add(channel_map[name])

    return ids
```

- [ ] **Step 6: Run channel tests**

Run: `uv run pytest tests/test_listener.py -v -k "channel"`
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add institutional_memory/listener.py tests/test_listener.py
git commit -m "feat: add channel allowlist resolution and threshold selection"
```

---

### Task 3: Query building

**Goal:** Implement `build_search_query()` that strips mentions, builds thread context from human messages only, caps at 2000 chars.

**Files:**
- Modify: `institutional_memory/listener.py`
- Modify: `tests/test_listener.py`

**Acceptance Criteria:**
- [ ] Top-level messages use raw text with `<@BOT_ID>` stripped
- [ ] Thread messages prepend human-only context from `conversations.replies`
- [ ] Bot messages filtered from thread context by `bot_id` and `user == bot_user_id`
- [ ] Total thread context capped at 2000 chars
- [ ] `conversations.replies` failure falls back to message text only

**Verify:** `uv run pytest tests/test_listener.py -v -k "query"` → all pass

**Steps:**

- [ ] **Step 1: Write failing tests for strip_mention**

Append to `tests/test_listener.py`:

```python
from institutional_memory.listener import strip_mention, build_search_query


def test_strip_mention_removes_bot_id():
    assert strip_mention("<@U999> what is our policy?", "U999") == "what is our policy?"


def test_strip_mention_no_mention():
    assert strip_mention("what is our policy?", "U999") == "what is our policy?"


def test_strip_mention_multiple():
    assert strip_mention("<@U999> hey <@U999> help", "U999") == "hey  help"
```

- [ ] **Step 2: Write failing tests for build_search_query**

Append to `tests/test_listener.py`:

```python
class FakeRepliesClient:
    def __init__(self, replies):
        self._replies = replies

    def conversations_replies(self, channel, ts, limit):
        return {"messages": self._replies}


class FakeFailingRepliesClient:
    def conversations_replies(self, channel, ts, limit):
        raise Exception("API error")


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
    assert len(query) <= 2100  # 2000 context + message text + separator


def test_query_thread_api_failure_falls_back():
    event = {"channel": "C123", "text": "<@U999> help me", "ts": "2.0", "thread_ts": "1.0"}
    client = FakeFailingRepliesClient()
    query = build_search_query(event, bot_user_id="U999", client=client)
    assert query == "help me"
```

- [ ] **Step 3: Implement strip_mention and build_search_query**

Add to `institutional_memory/listener.py`:

```python
import re


def strip_mention(text: str, bot_user_id: str) -> str:
    return re.sub(rf"<@{re.escape(bot_user_id)}>", "", text).strip()


def _is_bot_message(message: dict[str, Any], bot_user_id: str) -> bool:
    return bool(message.get("bot_id") or message.get("user") == bot_user_id)


def build_search_query(
    event: dict[str, Any],
    bot_user_id: str,
    client: Any,
) -> str:
    text = strip_mention(str(event.get("text", "")), bot_user_id)
    thread_ts = event.get("thread_ts")

    if not thread_ts or client is None:
        return text

    try:
        response = client.conversations_replies(
            channel=event["channel"], ts=thread_ts, limit=10
        )
        messages = response.get("messages", [])
    except Exception:
        return text

    context_parts: list[str] = []
    total_chars = 0
    for msg in messages:
        if _is_bot_message(msg, bot_user_id):
            continue
        msg_text = strip_mention(str(msg.get("text", "")), bot_user_id).strip()
        if not msg_text:
            continue
        if total_chars + len(msg_text) > 2000:
            remaining = 2000 - total_chars
            if remaining > 0:
                context_parts.append(msg_text[:remaining])
            break
        context_parts.append(msg_text)
        total_chars += len(msg_text)

    if context_parts:
        context = "\n".join(context_parts)
        return f"{context}\n\n{text}"
    return text
```

- [ ] **Step 4: Run query tests**

Run: `uv run pytest tests/test_listener.py -v -k "query"`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add institutional_memory/listener.py tests/test_listener.py
git commit -m "feat: add query building with thread context and mention stripping"
```

---

### Task 4: Reply formatting

**Goal:** Implement `format_reply()` and `format_no_hits_reply()`.

**Files:**
- Modify: `institutional_memory/listener.py`
- Modify: `tests/test_listener.py`

**Acceptance Criteria:**
- [ ] Single hit shows score, snippet (~150 chars), source path
- [ ] Multiple hits (max 3) show each with score and source
- [ ] No-hit mention reply returns the "didn't find anything" message
- [ ] Snippets truncated with ellipsis at ~150 chars

**Verify:** `uv run pytest tests/test_listener.py -v -k "format"` → all pass

**Steps:**

- [ ] **Step 1: Write failing tests for format_reply**

Append to `tests/test_listener.py`:

```python
from institutional_memory.listener import format_reply, format_no_hits_reply


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
    assert result.count("—") == 3  # em dash for each source


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
```

- [ ] **Step 2: Implement format_reply and format_no_hits_reply**

Add to `institutional_memory/listener.py`:

```python
MAX_HITS = 3
MAX_SNIPPET_CHARS = 150


def _truncate(text: str, max_chars: int = MAX_SNIPPET_CHARS) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def format_reply(hits: list[dict[str, Any]]) -> str:
    capped = hits[:MAX_HITS]
    if len(capped) == 1:
        hit = capped[0]
        score = round(hit["score"] * 100)
        snippet = _truncate(hit["text"])
        return (
            f"\U0001f4ce Found relevant context ({score}% match):\n\n"
            f"> \"{snippet}\"\n\n"
            f"— {hit['source']}"
        )
    lines = ["\U0001f4ce Found relevant context:\n"]
    for hit in capped:
        score = round(hit["score"] * 100)
        snippet = _truncate(hit["text"])
        lines.append(f"> \"{snippet}\"")
        lines.append(f"— {hit['source']} ({score}%)\n")
    return "\n".join(lines).rstrip()
    

def format_no_hits_reply() -> str:
    return "\U0001f50d I didn't find anything relevant in institutional memory."
```

- [ ] **Step 3: Run format tests**

Run: `uv run pytest tests/test_listener.py -v -k "format"`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add institutional_memory/listener.py tests/test_listener.py
git commit -m "feat: add reply formatting for listener"
```

---

### Task 5: Main handler and audit logging

**Goal:** Implement `handle_listener_event()` that wires filtering, threshold, query, search, format, and reply together with audit logging.

**Files:**
- Modify: `institutional_memory/listener.py`
- Modify: `tests/test_listener.py`

**Acceptance Criteria:**
- [ ] Unprompted message in allowed channel with high-score hit → thread reply + audit `listener_reply`
- [ ] Unprompted message below threshold → silence + audit `listener_skip`
- [ ] Mention with hits → thread reply
- [ ] Mention with no hits → "no relevant context" reply
- [ ] Message in non-allowed channel without mention → skipped (`not_in_allowlist`)
- [ ] Active thread follow-up uses 0.65 threshold
- [ ] Tracks `(channel, thread_ts)` in `active_threads` after reply
- [ ] `search_memory` failure → log error, no reply, no crash
- [ ] `chat.postMessage` failure → log error, no crash

**Verify:** `uv run pytest tests/test_listener.py -v -k "handle"` → all pass

**Steps:**

- [ ] **Step 1: Write failing tests for handle_listener_event**

Append to `tests/test_listener.py`:

```python
from unittest.mock import patch, MagicMock
from institutional_memory.listener import handle_listener_event, ListenerState


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
```

- [ ] **Step 2: Implement ListenerState and handle_listener_event**

Add to `institutional_memory/listener.py`:

```python
from dataclasses import dataclass, field

from institutional_memory.audit import log_event
from institutional_memory.search import search_memory


@dataclass
class ListenerState:
    bot_user_id: str
    allowed_channels: set[str]
    dedupe: DedupeSet
    active_threads: set[tuple[str, str]] = field(default_factory=set)


def _is_mention(event: dict[str, Any], bot_user_id: str) -> bool:
    if event.get("type") == "app_mention":
        return True
    return f"<@{bot_user_id}>" in str(event.get("text", ""))


def handle_listener_event(
    event: dict[str, Any],
    client: Any,
    state: ListenerState,
) -> dict[str, Any]:
    channel = str(event.get("channel", ""))
    ts = str(event.get("ts", ""))
    thread_ts = event.get("thread_ts") or ts

    if should_skip(event, state.bot_user_id):
        return {"status": "skipped", "reason": "filtered"}

    if state.dedupe.seen(channel, ts):
        return {"status": "skipped", "reason": "dedupe"}

    is_mention = _is_mention(event, state.bot_user_id)
    is_active_thread = (channel, event.get("thread_ts", "")) in state.active_threads

    if not is_mention and not is_active_thread and channel not in state.allowed_channels:
        log_event("listener_skip", channel=channel, reason="not_in_allowlist")
        return {"status": "skipped", "reason": "not_in_allowlist"}

    threshold = select_threshold(is_mention, is_active_thread)

    query = build_search_query(event, bot_user_id=state.bot_user_id, client=client)

    try:
        hits = search_memory(query, threshold=threshold)
    except Exception as exc:
        log_event("listener_error", channel=channel, error=str(exc))
        return {"status": "error", "error": str(exc)}

    if not hits:
        if is_mention:
            try:
                client.chat_postMessage(
                    channel=channel, text=format_no_hits_reply(), thread_ts=thread_ts
                )
                log_event("listener_reply", channel=channel, thread_ts=thread_ts, query=query, top_score=0, sources=[], triggered_by="mention")
                return {"status": "replied", "hits": 0, "triggered_by": "mention"}
            except Exception as exc:
                log_event("listener_error", channel=channel, error=str(exc))
                return {"status": "error", "error": str(exc)}
        log_event("listener_skip", channel=channel, reason="below_threshold", top_score=0)
        return {"status": "skipped", "reason": "below_threshold"}

    triggered_by = "mention" if is_mention else ("thread" if is_active_thread else "unprompted")
    reply_text = format_reply(hits)

    try:
        client.chat_postMessage(channel=channel, text=reply_text, thread_ts=thread_ts)
    except Exception as exc:
        log_event("listener_error", channel=channel, error=str(exc))
        return {"status": "error", "error": str(exc)}

    state.active_threads.add((channel, thread_ts))
    sources = [h["source"] for h in hits[:MAX_HITS]]
    log_event(
        "listener_reply",
        channel=channel,
        thread_ts=thread_ts,
        query=query,
        top_score=hits[0]["score"],
        sources=sources,
        triggered_by=triggered_by,
    )
    return {"status": "replied", "hits": len(hits), "triggered_by": triggered_by}
```

- [ ] **Step 3: Run handler tests**

Run: `uv run pytest tests/test_listener.py -v -k "handle"`
Expected: all pass

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest -v`
Expected: all pass (no regressions)

- [ ] **Step 5: Commit**

```bash
git add institutional_memory/listener.py tests/test_listener.py
git commit -m "feat: add main listener handler with search, reply, and audit"
```

---

### Task 6: Wire into scripts/slack_listener.py

**Goal:** Extend existing entry point to use `handle_listener_event`, add startup channel resolution, bot user ID fetch, and JSONL output.

**Files:**
- Modify: `scripts/slack_listener.py`

**Acceptance Criteria:**
- [ ] Startup fetches bot user ID via `auth.test`
- [ ] Startup resolves `LISTENER_CHANNELS` to IDs
- [ ] Startup prints JSONL status to stdout
- [ ] Events dispatched to `handle_listener_event` after ack
- [ ] Existing ingestion behavior preserved (`handle_message_event` still called)
- [ ] Audit logs `listener_started` and `listener_stopped`
- [ ] All existing tests still pass

**Verify:** `uv run pytest -v` → all pass

**Steps:**

- [ ] **Step 1: Rewrite scripts/slack_listener.py**

Replace the contents of `scripts/slack_listener.py` with:

```python
"""Long-running Slack Socket Mode listener.

Run outside OpenClaw:
    uv run python scripts/slack_listener.py
"""

from __future__ import annotations

import json
import signal
import sys
from threading import Event

from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from institutional_memory.audit import log_event
from institutional_memory.config import (
    LISTENER_CHANNELS,
    SLACK_APP_TOKEN,
    SLACK_BOT_TOKEN,
    SLACK_CHANNEL,
)
from institutional_memory.listener import (
    DedupeSet,
    ListenerState,
    handle_listener_event,
    resolve_channels,
)
from institutional_memory.slack_ingest import handle_message_event


def _build_state(web_client: WebClient) -> ListenerState:
    auth = web_client.auth_test()
    bot_user_id = auth["user_id"]

    allowed_channels = resolve_channels(
        LISTENER_CHANNELS, fallback_channel=SLACK_CHANNEL, client=web_client
    )

    return ListenerState(
        bot_user_id=bot_user_id,
        allowed_channels=allowed_channels,
        dedupe=DedupeSet(),
    )


def process(
    client: SocketModeClient,
    request: SocketModeRequest,
    web_client: WebClient,
    state: ListenerState,
) -> None:
    if request.type == "events_api":
        client.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))
        event = request.payload.get("event", {})

        # Existing ingestion (write to inbox)
        try:
            ingest_result = handle_message_event(event, client=web_client)
        except Exception as exc:
            ingest_result = {"status": "error", "error": str(exc)}
        log_event("slack_event_ingested", **ingest_result)

        # Answer loop (search + reply)
        result = handle_listener_event(event, web_client, state)
        print(json.dumps(result, ensure_ascii=False), flush=True)


def main() -> int:
    if not SLACK_APP_TOKEN:
        print(json.dumps({"status": "error", "error": "SLACK_APP_TOKEN missing"}), file=sys.stderr)
        return 1
    if not SLACK_BOT_TOKEN:
        print(json.dumps({"status": "error", "error": "SLACK_BOT_TOKEN missing"}), file=sys.stderr)
        return 1

    web_client = WebClient(token=SLACK_BOT_TOKEN)
    state = _build_state(web_client)

    log_event("listener_started", bot_user_id=state.bot_user_id, channels=sorted(state.allowed_channels))
    print(
        json.dumps({
            "status": "listening",
            "bot_user_id": state.bot_user_id,
            "channels": sorted(state.allowed_channels),
        }),
        flush=True,
    )

    sm_client = SocketModeClient(app_token=SLACK_APP_TOKEN, web_client=web_client)
    sm_client.socket_mode_request_listeners.append(
        lambda client, request: process(client, request, web_client, state)
    )

    stop = Event()

    def _shutdown(signum, frame):
        log_event("listener_stopped")
        print(json.dumps({"status": "stopped"}), flush=True)
        stop.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    sm_client.connect()
    stop.wait()
    sm_client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest -v`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add scripts/slack_listener.py
git commit -m "feat: wire listener handler into slack_listener.py entry point"
```

---

## Dependency Graph

```
Task 0 (config)
    ↓
Task 1 (filtering + dedupe)
    ↓           ↓
Task 2       Task 4
(channels +  (formatting)
 threshold)
    ↓           ↓
Task 3       Task 5 (handler) ← depends on Tasks 2, 3, 4, 5
(query)         ↓
    ↘        Task 6 (wire entry point)
     ↗
```

Parallel lanes: Tasks 2+3 can run in parallel with Task 4 (no shared code). Task 5 needs all of 2-4. Task 6 needs 5.
