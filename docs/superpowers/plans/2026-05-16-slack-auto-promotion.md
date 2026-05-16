# Slack Auto-Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture human-curated Slack threads as searchable corpus memory cards when a human reacts with `:memo:` or `:brain:`.

**Architecture:** Add a focused `institutional_memory/slack_promotion.py` module that validates reaction events, resolves the parent Slack thread, writes an indexed memory card under `company/corpus/slack/promoted/`, and writes raw evidence JSON under `company/evidence/slack/`. Extend the Socket Mode listener to route `reaction_added` events through this module while preserving ack-first behavior and keeping message ingest/search unchanged.

**Tech Stack:** Python 3.12, `slack-sdk` WebClient, existing JSONL audit log, existing path safety helpers, pytest, no new runtime dependencies.

---

## File Structure

- Create `institutional_memory/slack_promotion.py`
  - Owns promotion validation, rate limiting, title generation, conservative card composition, evidence writing, related-source audit lookup, and JSON-safe return payloads.
- Modify `institutional_memory/config.py`
  - Adds `COMPANY_EVIDENCE_PATH`, `PROMOTION_ALLOWED_CHANNELS`, `PROMOTION_USER_COOLDOWN_SECONDS`, and `PROMOTION_GLOBAL_MAX_PER_MINUTE`.
- Modify `institutional_memory/paths.py`
  - Adds `safe_evidence_path()` for `.json` files under `company/evidence/`.
- Modify `institutional_memory/listener.py`
  - Adds promotion-related state fields to `ListenerState`.
- Modify `scripts/slack_listener.py`
  - Resolves promotion channel allowlist at startup and routes `reaction_added` events to `handle_reaction_event()`.
- Modify `.env.example`
  - Documents promotion config defaults.
- Modify `tests/test_paths.py`
  - Covers evidence path safety.
- Create `tests/test_slack_promotion.py`
  - Covers the promotion module end to end with fake Slack clients and temp paths.
- Modify `tests/test_listener.py`
  - Verifies `ListenerState` can carry promotion state without breaking existing listener behavior.
- Create `tests/test_slack_listener_process.py`
  - Verifies `scripts/slack_listener.process()` routes `reaction_added` without invoking message ingest/search.
- Modify `README.md`
  - Documents the reaction workflow and explicit reingest requirement.

---

### Task 1: Add Promotion Config And Evidence Path Safety

**Files:**
- Modify: `institutional_memory/config.py`
- Modify: `institutional_memory/paths.py`
- Modify: `.env.example`
- Test: `tests/test_paths.py`

- [ ] **Step 1: Write failing path tests**

Append these tests to `tests/test_paths.py`:

```python
def test_safe_evidence_allows_json_under_company_evidence():
    from institutional_memory.paths import safe_evidence_path

    assert safe_evidence_path("company/evidence/slack/C123_1710000000.000000.json") == (
        PROJECT_ROOT / "company/evidence/slack/C123_1710000000.000000.json"
    ).resolve()


def test_safe_evidence_blocks_corpus_path():
    from institutional_memory.paths import safe_evidence_path

    with pytest.raises(PathNotAllowedError):
        safe_evidence_path("company/corpus/slack/evidence/C123.json")


def test_safe_evidence_rejects_markdown():
    from institutional_memory.paths import safe_evidence_path

    with pytest.raises(PathNotAllowedError):
        safe_evidence_path("company/evidence/slack/C123.md")
```

- [ ] **Step 2: Run path tests to verify failure**

Run:

```bash
uv run pytest tests/test_paths.py -q
```

Expected: FAIL because `safe_evidence_path` does not exist.

- [ ] **Step 3: Add config values**

In `institutional_memory/config.py`, insert this line after `COMPANY_CORPUS_PATH = COMPANY_DOCS_PATH / "corpus"`:

```python
COMPANY_EVIDENCE_PATH = COMPANY_DOCS_PATH / "evidence"
```

Insert these lines after `LISTENER_CHANNELS = os.getenv("LISTENER_CHANNELS", "")`:

```python
PROMOTION_ALLOWED_CHANNELS = os.getenv("PROMOTION_ALLOWED_CHANNELS", "")
PROMOTION_USER_COOLDOWN_SECONDS = float(os.getenv("PROMOTION_USER_COOLDOWN_SECONDS", "60"))
PROMOTION_GLOBAL_MAX_PER_MINUTE = int(os.getenv("PROMOTION_GLOBAL_MAX_PER_MINUTE", "10"))
```

- [ ] **Step 4: Add evidence path helper**

Update the import in `institutional_memory/paths.py` from:

```python
from institutional_memory.config import COMPANY_CORPUS_PATH, COMPANY_INBOX_PATH, PROJECT_ROOT, RUNTIME_PATH
```

to:

```python
from institutional_memory.config import (
    COMPANY_CORPUS_PATH,
    COMPANY_EVIDENCE_PATH,
    COMPANY_INBOX_PATH,
    PROJECT_ROOT,
    RUNTIME_PATH,
)
```

Append this function after `safe_corpus_path()`:

```python
def safe_evidence_path(raw: str) -> Path:
    candidate = _ensure_under(_resolve_under_project(raw), COMPANY_EVIDENCE_PATH, raw)
    if candidate.suffix.lower() != ".json":
        raise PathNotAllowedError("Only .json evidence files are allowed")
    return candidate
```

- [ ] **Step 5: Document env defaults**

Append these lines to `.env.example`:

```text
PROMOTION_ALLOWED_CHANNELS=
PROMOTION_USER_COOLDOWN_SECONDS=60
PROMOTION_GLOBAL_MAX_PER_MINUTE=10
```

- [ ] **Step 6: Run path tests**

Run:

```bash
uv run pytest tests/test_paths.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add institutional_memory/config.py institutional_memory/paths.py tests/test_paths.py .env.example
git commit -m "feat: add slack promotion path config"
```

---

### Task 2: Add Slack Promotion Core Module

**Files:**
- Create: `institutional_memory/slack_promotion.py`
- Create: `tests/test_slack_promotion.py`

- [ ] **Step 1: Write failing promotion module tests**

Create `tests/test_slack_promotion.py` with this content:

```python
import json
from pathlib import Path

from institutional_memory import paths, slack_promotion


class FakePromotionClient:
    def __init__(self, messages=None, permalink=None):
        self.messages = messages or [
            {"ts": "1710000000.000000", "user": "U123", "text": "Need precedent for vendor liability clause"},
            {"ts": "1710000001.000000", "user": "U456", "text": "Resolution: use the standard cap from the vendor terms playbook"},
        ]
        self.permalink = permalink or "https://example.slack.com/archives/C123/p1710000000000000"
        self.replies_calls = []
        self.history_calls = []
        self.permalink_calls = []

    def conversations_history(self, channel, latest, inclusive, limit):
        self.history_calls.append(
            {"channel": channel, "latest": latest, "inclusive": inclusive, "limit": limit}
        )
        message = next((item for item in self.messages if item.get("ts") == latest), None)
        if message is None:
            message = {"ts": latest, "user": "U123", "text": "Need precedent"}
        return {"messages": [message]}

    def conversations_replies(self, channel, ts):
        self.replies_calls.append({"channel": channel, "ts": ts})
        return {"messages": self.messages}

    def chat_getPermalink(self, channel, message_ts):
        self.permalink_calls.append({"channel": channel, "message_ts": message_ts})
        return {"permalink": self.permalink}


def _patch_promotion_paths(monkeypatch, tmp_path):
    company_corpus = tmp_path / "company" / "corpus"
    company_evidence = tmp_path / "company" / "evidence"
    monkeypatch.setattr(slack_promotion, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(slack_promotion, "COMPANY_CORPUS_PATH", company_corpus)
    monkeypatch.setattr(slack_promotion, "COMPANY_EVIDENCE_PATH", company_evidence)
    monkeypatch.setattr(paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(paths, "COMPANY_CORPUS_PATH", company_corpus)
    monkeypatch.setattr(paths, "COMPANY_EVIDENCE_PATH", company_evidence)
    return company_corpus, company_evidence


def _reaction_event(**overrides):
    event = {
        "type": "reaction_added",
        "user": "U123",
        "reaction": "memo",
        "item": {"type": "message", "channel": "C123", "ts": "1710000000.000000"},
    }
    event.update(overrides)
    return event


def test_unsupported_reaction_is_ignored(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(reaction="eyes"),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result == {"status": "ignored", "reason": "unsupported_reaction"}


def test_bot_reaction_is_ignored(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(user="UBOT"),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result == {"status": "ignored", "reason": "bot_reaction"}


def test_empty_allowlist_disables_promotion(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels=set(),
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result == {"status": "ignored", "reason": "channel_not_allowed"}


def test_channel_outside_allowlist_is_ignored(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C999"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result == {"status": "ignored", "reason": "channel_not_allowed"}


def test_approved_reaction_writes_memory_card_and_evidence(tmp_path, monkeypatch):
    company_corpus, company_evidence = _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    evidence = company_evidence / "slack" / "C123_1710000000.000000.json"
    assert card.exists()
    assert evidence.exists()
    text = card.read_text(encoding="utf-8")
    assert "# Slack Memory: Need precedent for vendor liability clause" in text
    assert "Reaction: :memo:" in text
    assert "## Resolution" in text
    assert "use the standard cap" in text
    assert "company/evidence/slack/C123_1710000000.000000.json" in text
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["channel"] == "C123"
    assert payload["thread_ts"] == "1710000000.000000"
    assert payload["messages"][0]["text"] == "Need precedent for vendor liability clause"


def test_brain_reaction_records_brain_metadata(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(reaction="brain"),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    assert "Reaction: :brain:" in card.read_text(encoding="utf-8")


def test_reaction_on_reply_promotes_parent_thread(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    client = FakePromotionClient(messages=[
        {"ts": "1710000000.000000", "user": "U123", "text": "Need precedent for vendor liability clause"},
        {"ts": "1710000005.000000", "thread_ts": "1710000000.000000", "user": "U456", "text": "Resolution: use standard cap"},
    ])

    result = slack_promotion.handle_reaction_event(
        _reaction_event(item={"type": "message", "channel": "C123", "ts": "1710000005.000000"}),
        client=client,
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    assert client.replies_calls == [{"channel": "C123", "ts": "1710000000.000000"}]
    assert (company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md").exists()


def test_existing_card_returns_exists_without_rewrite(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    card.parent.mkdir(parents=True)
    card.write_text("original", encoding="utf-8")

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(user_cooldown_seconds=999),
        bot_user_id="UBOT",
    )

    assert result["status"] == "exists"
    assert card.read_text(encoding="utf-8") == "original"


def test_missing_resolution_writes_no_resolution_captured(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    client = FakePromotionClient(messages=[
        {"ts": "1710000000.000000", "user": "U123", "text": "Need precedent for vendor liability clause"},
        {"ts": "1710000001.000000", "user": "U456", "text": "I will look around"},
    ])

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=client,
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    text = card.read_text(encoding="utf-8")
    assert "No resolution captured" in text
    assert "## Reusable Takeaway" not in text


def test_explicit_takeaway_section_is_included(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    client = FakePromotionClient(messages=[
        {"ts": "1710000000.000000", "user": "U123", "text": "Need precedent"},
        {"ts": "1710000001.000000", "user": "U456", "text": "Takeaway: route vendor liability changes through legal first"},
    ])

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=client,
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    text = card.read_text(encoding="utf-8")
    assert "## Reusable Takeaway" in text
    assert "route vendor liability changes through legal first" in text


def test_long_threads_use_bounded_card_window_but_full_evidence(tmp_path, monkeypatch):
    company_corpus, company_evidence = _patch_promotion_paths(monkeypatch, tmp_path)
    messages = [{"ts": "1710000000.000000", "user": "U123", "text": "Need precedent"}]
    messages.extend(
        {"ts": f"17100000{i:02d}.000000", "user": "U456", "text": f"message {i} " + ("x" * 500)}
        for i in range(20)
    )
    client = FakePromotionClient(messages=messages)

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=client,
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    evidence = company_evidence / "slack" / "C123_1710000000.000000.json"
    assert len(card.read_text(encoding="utf-8")) <= 2500
    assert len(json.loads(evidence.read_text(encoding="utf-8"))["messages"]) == 21
```

- [ ] **Step 2: Run tests to verify module missing failure**

Run:

```bash
uv run pytest tests/test_slack_promotion.py -q
```

Expected: FAIL because `institutional_memory.slack_promotion` does not exist.

- [ ] **Step 3: Implement promotion module**

Create `institutional_memory/slack_promotion.py` with this content:

```python
"""Slack reaction-based promotion into corpus memory cards."""

from __future__ import annotations

import html
import json
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from slack_sdk.errors import SlackApiError

from institutional_memory.audit import log_event
from institutional_memory.config import (
    AUDIT_LOG,
    COMPANY_CORPUS_PATH,
    COMPANY_EVIDENCE_PATH,
    PROJECT_ROOT,
    PROMOTION_GLOBAL_MAX_PER_MINUTE,
    PROMOTION_USER_COOLDOWN_SECONDS,
)
from institutional_memory.paths import safe_corpus_path, safe_evidence_path

APPROVED_REACTIONS = {"memo", "brain"}
INGEST_REMINDER = "run uv run python scripts/ingest_corpus.py --force to make promoted Slack memory searchable"
MAX_TITLE_CHARS = 80
MAX_CARD_CHARS = 2000
MAX_CONTEXT_CHARS = 4000


class PromotionRateLimiter:
    def __init__(
        self,
        user_cooldown_seconds: float = PROMOTION_USER_COOLDOWN_SECONDS,
        global_max_per_minute: int = PROMOTION_GLOBAL_MAX_PER_MINUTE,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.user_cooldown_seconds = user_cooldown_seconds
        self.global_max_per_minute = global_max_per_minute
        self.clock = clock
        self._user_last: dict[str, float] = {}
        self._global_events: deque[float] = deque()

    def allow(self, user: str) -> tuple[bool, str | None]:
        now = self.clock()
        last = self._user_last.get(user)
        if last is not None and now - last < self.user_cooldown_seconds:
            return False, "rate_limited_user"

        while self._global_events and now - self._global_events[0] >= 60:
            self._global_events.popleft()

        if self.global_max_per_minute > 0 and len(self._global_events) >= self.global_max_per_minute:
            return False, "rate_limited_global"

        self._user_last[user] = now
        self._global_events.append(now)
        return True, None


def _clean_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<@[A-Z0-9]+>", "", text)
    return " ".join(text.split())


def _message_text(message: dict[str, Any]) -> str:
    return _clean_text(str(message.get("text", "")))


def _human_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        message
        for message in messages
        if not message.get("bot_id") and message.get("user") and _message_text(message)
    ]


def title_from_messages(channel: str, thread_ts: str, messages: list[dict[str, Any]]) -> str:
    for message in _human_messages(messages):
        text = _message_text(message)
        if text:
            return text[:MAX_TITLE_CHARS].rstrip()
    return f"Slack thread {channel} {thread_ts}"


def _first_marker_text(messages: list[dict[str, Any]], markers: list[str]) -> str | None:
    for message in reversed(_human_messages(messages)):
        text = _message_text(message)
        lower = text.lower()
        for marker in markers:
            if lower.startswith(marker):
                return text.split(":", 1)[1].strip() if ":" in text else text
    return None


def _resolution(messages: list[dict[str, Any]]) -> str:
    value = _first_marker_text(
        messages,
        ["resolution:", "resolved:", "decision:", "decided:", "fixed:"],
    )
    return value or "No resolution captured"


def _takeaway(messages: list[dict[str, Any]]) -> str | None:
    return _first_marker_text(messages, ["takeaway:", "lesson:"])


def _bounded_context(messages: list[dict[str, Any]]) -> str:
    humans = _human_messages(messages)
    if not humans:
        return ""

    selected: list[dict[str, Any]] = []
    selected.append(humans[0])
    for message in humans[-10:]:
        if message not in selected:
            selected.append(message)

    lines: list[str] = []
    total = 0
    for message in selected:
        line = f"{message.get('user')}: {_message_text(message)}"
        if total + len(line) > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - total
            if remaining > 0:
                lines.append(line[:remaining].rstrip())
            break
        lines.append(line)
        total += len(line)
    return "\n".join(lines)


def _audit_related_sources(channel: str, thread_ts: str) -> tuple[list[str], str]:
    if not AUDIT_LOG.exists():
        return [], "none"
    sources: list[str] = []
    try:
        for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                entry.get("type") == "listener_reply"
                and entry.get("channel") == channel
                and str(entry.get("thread_ts")) == thread_ts
            ):
                for source in entry.get("sources") or []:
                    if source not in sources:
                        sources.append(str(source))
    except OSError:
        return [], "unavailable"
    return sources, "matched" if sources else "none"


def _memory_card_path(channel: str, thread_ts: str) -> Path:
    return safe_corpus_path(str(COMPANY_CORPUS_PATH / "slack" / "promoted" / f"{channel}_{thread_ts}.md"))


def _evidence_path(channel: str, thread_ts: str) -> Path:
    return safe_evidence_path(str(COMPANY_EVIDENCE_PATH / "slack" / f"{channel}_{thread_ts}.json"))


def _render_memory_card(
    *,
    channel: str,
    thread_ts: str,
    promoted_by: str,
    reaction: str,
    permalink: str | None,
    messages: list[dict[str, Any]],
    related_sources: list[str],
    evidence_rel: str,
    promoted_at: str | None = None,
) -> str:
    title = title_from_messages(channel, thread_ts, messages)
    happened = _bounded_context(messages) or "No substantive human text captured."
    resolution = _resolution(messages)
    takeaway = _takeaway(messages)
    timestamp = promoted_at or datetime.now(timezone.utc).isoformat()

    lines = [
        f"# Slack Memory: {title}",
        "",
        f"Promoted At: {timestamp}",
        f"Promoted By: {promoted_by}",
        f"Reaction: :{reaction}:",
        f"Channel: {channel}",
        f"Thread TS: {thread_ts}",
        f"Permalink: {permalink or ''}",
        "",
        "## What Happened",
        "",
        happened,
        "",
        "## Resolution",
        "",
        resolution,
        "",
    ]
    if takeaway:
        lines.extend(["## Reusable Takeaway", "", takeaway, ""])
    if related_sources:
        lines.extend(["## Related Sources", ""])
        lines.extend(f"- {source}" for source in related_sources)
        lines.append("")
    lines.extend(["## Evidence", "", f"Raw Slack thread snapshot: {evidence_rel}", ""])
    text = "\n".join(lines)
    return text[:MAX_CARD_CHARS].rstrip() + "\n" if len(text) > MAX_CARD_CHARS else text


def _item(event: dict[str, Any]) -> dict[str, Any]:
    item = event.get("item") or {}
    return item if isinstance(item, dict) else {}


def _resolve_parent_thread_ts(event: dict[str, Any], client: Any) -> tuple[str, str]:
    item = _item(event)
    channel = str(item.get("channel") or "")
    item_ts = str(item.get("ts") or "")
    if not channel or not item_ts:
        raise ValueError("reaction event missing message channel or ts")
    response = client.conversations_history(channel=channel, latest=item_ts, inclusive=True, limit=1)
    messages = response.get("messages") or []
    message = messages[0] if messages else {"ts": item_ts}
    return channel, str(message.get("thread_ts") or message.get("ts") or item_ts)


def _permalink(client: Any, channel: str, thread_ts: str) -> tuple[str | None, str | None]:
    try:
        return client.chat_getPermalink(channel=channel, message_ts=thread_ts).get("permalink"), None
    except SlackApiError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, str(exc)


def handle_reaction_event(
    event: dict[str, Any],
    *,
    client: Any,
    allowed_channels: set[str],
    rate_limiter: PromotionRateLimiter,
    bot_user_id: str,
) -> dict[str, Any]:
    reaction = str(event.get("reaction") or "")
    if reaction not in APPROVED_REACTIONS:
        return {"status": "ignored", "reason": "unsupported_reaction"}

    user = str(event.get("user") or "")
    if not user:
        return {"status": "ignored", "reason": "missing_user"}
    if user == bot_user_id:
        return {"status": "ignored", "reason": "bot_reaction"}

    item = _item(event)
    if item.get("type") != "message":
        return {"status": "ignored", "reason": "not_message_reaction"}

    channel = str(item.get("channel") or "")
    if channel not in allowed_channels:
        return {"status": "ignored", "reason": "channel_not_allowed"}

    try:
        channel, thread_ts = _resolve_parent_thread_ts(event, client)
    except Exception as exc:
        log_event("slack_thread_auto_promote_failed", error=str(exc), channel=channel)
        return {"status": "error", "error": str(exc)}

    if channel not in allowed_channels:
        return {"status": "ignored", "reason": "channel_not_allowed"}

    card_path = _memory_card_path(channel, thread_ts)
    evidence_path = _evidence_path(channel, thread_ts)
    card_rel = str(card_path.relative_to(PROJECT_ROOT))
    evidence_rel = str(evidence_path.relative_to(PROJECT_ROOT))
    if card_path.exists():
        result = {"status": "exists", "path": card_rel, "evidence": evidence_rel, "note": INGEST_REMINDER}
        log_event("slack_thread_auto_promoted", **result, channel=channel, thread_ts=thread_ts, promoted_by=user, reaction=reaction)
        return result

    allowed, reason = rate_limiter.allow(user)
    if not allowed:
        return {"status": "ignored", "reason": reason or "rate_limited"}

    try:
        messages = client.conversations_replies(channel=channel, ts=thread_ts).get("messages", [])
    except Exception as exc:
        log_event("slack_thread_auto_promote_failed", error=str(exc), channel=channel, thread_ts=thread_ts)
        return {"status": "error", "error": str(exc)}

    if not _human_messages(messages):
        return {"status": "ignored", "reason": "empty_thread"}

    permalink, permalink_error = _permalink(client, channel, thread_ts)
    related_sources, related_sources_mode = _audit_related_sources(channel, thread_ts)

    card_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_payload = {
        "channel": channel,
        "thread_ts": thread_ts,
        "permalink": permalink,
        "promoted_by": user,
        "reaction": reaction,
        "messages": messages,
    }
    evidence_path.write_text(json.dumps(evidence_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    card_path.write_text(
        _render_memory_card(
            channel=channel,
            thread_ts=thread_ts,
            promoted_by=user,
            reaction=reaction,
            permalink=permalink,
            messages=messages,
            related_sources=related_sources,
            evidence_rel=evidence_rel,
        ),
        encoding="utf-8",
    )

    result: dict[str, Any] = {
        "status": "promoted",
        "path": card_rel,
        "evidence": evidence_rel,
        "note": INGEST_REMINDER,
        "related_sources_mode": related_sources_mode,
    }
    if permalink_error:
        result["permalink_warning"] = permalink_error
    log_event(
        "slack_thread_auto_promoted",
        **result,
        channel=channel,
        thread_ts=thread_ts,
        promoted_by=user,
        reaction=reaction,
    )
    return result
```

- [ ] **Step 4: Run core promotion tests**

Run:

```bash
uv run pytest tests/test_slack_promotion.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add institutional_memory/slack_promotion.py tests/test_slack_promotion.py
git commit -m "feat: add slack reaction promotion core"
```

---

### Task 3: Lock In Related Source And Rate Limit Behavior

**Files:**
- Modify: `tests/test_slack_promotion.py`

- [ ] **Step 1: Add behavior tests for related sources and rate limits**

Append these tests to `tests/test_slack_promotion.py`:

```python
def test_related_sources_from_audit_are_best_effort(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    audit_log = tmp_path / "audit_log.jsonl"
    monkeypatch.setattr(slack_promotion, "AUDIT_LOG", audit_log)
    audit_log.write_text(
        json.dumps({
            "type": "listener_reply",
            "channel": "C123",
            "thread_ts": "1710000000.000000",
            "sources": ["company/corpus/vendor_terms.md"],
        })
        + "\n"
        + "{not json}\n",
        encoding="utf-8",
    )

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    assert result["related_sources_mode"] == "matched"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    assert "company/corpus/vendor_terms.md" in card.read_text(encoding="utf-8")


def test_missing_audit_file_does_not_block_promotion(tmp_path, monkeypatch):
    company_corpus, _ = _patch_promotion_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(slack_promotion, "AUDIT_LOG", tmp_path / "missing_audit_log.jsonl")

    result = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=slack_promotion.PromotionRateLimiter(),
        bot_user_id="UBOT",
    )

    assert result["status"] == "promoted"
    assert result["related_sources_mode"] == "none"
    card = company_corpus / "slack" / "promoted" / "C123_1710000000.000000.md"
    assert "## Related Sources" not in card.read_text(encoding="utf-8")


def test_user_rate_limit_blocks_second_distinct_thread(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)
    limiter = slack_promotion.PromotionRateLimiter(user_cooldown_seconds=60)

    first = slack_promotion.handle_reaction_event(
        _reaction_event(),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=limiter,
        bot_user_id="UBOT",
    )
    second = slack_promotion.handle_reaction_event(
        _reaction_event(item={"type": "message", "channel": "C123", "ts": "1710000020.000000"}),
        client=FakePromotionClient(messages=[
            {"ts": "1710000020.000000", "user": "U123", "text": "Another useful thread"},
        ]),
        allowed_channels={"C123"},
        rate_limiter=limiter,
        bot_user_id="UBOT",
    )

    assert first["status"] == "promoted"
    assert second == {"status": "ignored", "reason": "rate_limited_user"}


def test_global_rate_limit_blocks_burst(tmp_path, monkeypatch):
    _patch_promotion_paths(monkeypatch, tmp_path)
    limiter = slack_promotion.PromotionRateLimiter(user_cooldown_seconds=0, global_max_per_minute=1)

    first = slack_promotion.handle_reaction_event(
        _reaction_event(user="U111"),
        client=FakePromotionClient(),
        allowed_channels={"C123"},
        rate_limiter=limiter,
        bot_user_id="UBOT",
    )
    second = slack_promotion.handle_reaction_event(
        _reaction_event(user="U222", item={"type": "message", "channel": "C123", "ts": "1710000020.000000"}),
        client=FakePromotionClient(messages=[
            {"ts": "1710000020.000000", "user": "U222", "text": "Another useful thread"},
        ]),
        allowed_channels={"C123"},
        rate_limiter=limiter,
        bot_user_id="UBOT",
    )

    assert first["status"] == "promoted"
    assert second == {"status": "ignored", "reason": "rate_limited_global"}
```

- [ ] **Step 2: Run tests**

Run:

```bash
uv run pytest tests/test_slack_promotion.py -q
```

Expected: PASS. If this fails, the implementation in `institutional_memory/slack_promotion.py` diverges from the code block in Task 2; restore that implementation before continuing.

- [ ] **Step 3: Commit**

Run:

```bash
git add institutional_memory/slack_promotion.py tests/test_slack_promotion.py
git commit -m "test: cover slack promotion safety cases"
```

---

### Task 4: Wire Promotion State Into Listener Startup

**Files:**
- Modify: `institutional_memory/listener.py`
- Modify: `scripts/slack_listener.py`
- Modify: `tests/test_listener.py`

- [ ] **Step 1: Add failing listener state test**

Append this test to `tests/test_listener.py`:

```python
def test_listener_state_carries_promotion_state():
    limiter = object()
    state = ListenerState(
        bot_user_id="UBOT",
        allowed_channels={"C100"},
        dedupe=DedupeSet(max_size=100, ttl_seconds=60),
        promotion_allowed_channels={"C200"},
        promotion_rate_limiter=limiter,
    )

    assert state.promotion_allowed_channels == {"C200"}
    assert state.promotion_rate_limiter is limiter
```

- [ ] **Step 2: Run listener test to verify failure**

Run:

```bash
uv run pytest tests/test_listener.py::test_listener_state_carries_promotion_state -q
```

Expected: FAIL because `ListenerState` does not accept promotion fields.

- [ ] **Step 3: Add fields to ListenerState**

In `institutional_memory/listener.py`, change the import from:

```python
from typing import Any
```

to:

```python
from typing import Any
```

The import text remains unchanged because `Any` is already present.

Replace the `ListenerState` dataclass with:

```python
@dataclass
class ListenerState:
    bot_user_id: str
    allowed_channels: set[str]
    dedupe: DedupeSet
    active_threads: set[tuple[str, str]] = field(default_factory=set)
    promotion_allowed_channels: set[str] = field(default_factory=set)
    promotion_rate_limiter: Any = None
```

- [ ] **Step 4: Wire startup config**

In `scripts/slack_listener.py`, add these imports to the config import block:

```python
    PROMOTION_ALLOWED_CHANNELS,
```

Add this import with the listener imports:

```python
from institutional_memory.slack_promotion import PromotionRateLimiter
```

In `_build_state()`, insert this code after the existing `allowed_channels = resolve_channels(` call and its closing parenthesis:

```python
    promotion_allowed_channels = resolve_channels(
        PROMOTION_ALLOWED_CHANNELS, fallback_channel="", client=web_client
    )
```

Replace the existing `return ListenerState(` block with:

```python
    return ListenerState(
        bot_user_id=bot_user_id,
        allowed_channels=allowed_channels,
        dedupe=DedupeSet(),
        promotion_allowed_channels=promotion_allowed_channels,
        promotion_rate_limiter=PromotionRateLimiter(),
    )
```

In `main()`, replace the `listener_started` audit event with:

```python
    log_event(
        "listener_started",
        bot_user_id=state.bot_user_id,
        channels=sorted(state.allowed_channels),
        promotion_channels=sorted(state.promotion_allowed_channels),
    )
```

Replace the startup JSON print body with:

```python
        json.dumps({
            "status": "listening",
            "bot_user_id": state.bot_user_id,
            "channels": sorted(state.allowed_channels),
            "promotion_channels": sorted(state.promotion_allowed_channels),
        }),
```

- [ ] **Step 5: Run listener tests**

Run:

```bash
uv run pytest tests/test_listener.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add institutional_memory/listener.py scripts/slack_listener.py tests/test_listener.py
git commit -m "feat: configure slack promotion channels"
```

---

### Task 5: Route Slack Reaction Events Without Message Processing

**Files:**
- Modify: `scripts/slack_listener.py`
- Create: `tests/test_slack_listener_process.py`

- [ ] **Step 1: Write failing process routing tests**

Create `tests/test_slack_listener_process.py` with this content:

```python
from institutional_memory.listener import DedupeSet, ListenerState
from scripts import slack_listener


class FakeSocketClient:
    def __init__(self):
        self.responses = []

    def send_socket_mode_response(self, response):
        self.responses.append(response)


class FakeRequest:
    type = "events_api"
    envelope_id = "env-1"

    def __init__(self, event):
        self.payload = {"event": event}


class FakeWebClient:
    pass


def _state():
    return ListenerState(
        bot_user_id="UBOT",
        allowed_channels={"C123"},
        dedupe=DedupeSet(),
        promotion_allowed_channels={"C123"},
        promotion_rate_limiter=object(),
    )


def test_process_routes_reaction_added_to_promotion(monkeypatch, capsys):
    calls = []

    def fake_handle_reaction_event(event, *, client, allowed_channels, rate_limiter, bot_user_id):
        calls.append({
            "event": event,
            "allowed_channels": allowed_channels,
            "rate_limiter": rate_limiter,
            "bot_user_id": bot_user_id,
        })
        return {"status": "promoted", "path": "company/corpus/slack/promoted/C123_1.md"}

    monkeypatch.setattr(slack_listener, "handle_reaction_event", fake_handle_reaction_event)
    monkeypatch.setattr(slack_listener, "handle_message_event", lambda event, client: (_ for _ in ()).throw(AssertionError("message ingest should not run")))
    monkeypatch.setattr(slack_listener, "handle_listener_event", lambda event, web_client, state: (_ for _ in ()).throw(AssertionError("answer loop should not run")))
    monkeypatch.setattr(slack_listener, "log_event", lambda event_type, **fields: None)

    state = _state()
    request = FakeRequest({
        "type": "reaction_added",
        "user": "U123",
        "reaction": "memo",
        "item": {"type": "message", "channel": "C123", "ts": "1.0"},
    })

    slack_listener.process(FakeSocketClient(), request, FakeWebClient(), state)

    assert len(calls) == 1
    assert calls[0]["allowed_channels"] == {"C123"}
    assert calls[0]["bot_user_id"] == "UBOT"
    assert '"status": "promoted"' in capsys.readouterr().out


def test_process_message_events_still_use_existing_paths(monkeypatch, capsys):
    monkeypatch.setattr(slack_listener, "handle_message_event", lambda event, client: {"status": "written"})
    monkeypatch.setattr(slack_listener, "handle_listener_event", lambda event, web_client, state: {"status": "skipped", "reason": "below_threshold"})
    monkeypatch.setattr(slack_listener, "log_event", lambda event_type, **fields: None)

    request = FakeRequest({
        "type": "message",
        "channel": "C123",
        "ts": "1.0",
        "user": "U123",
        "text": "Need precedent",
    })

    slack_listener.process(FakeSocketClient(), request, FakeWebClient(), _state())

    assert '"reason": "below_threshold"' in capsys.readouterr().out
```

- [ ] **Step 2: Run routing tests to verify failure**

Run:

```bash
uv run pytest tests/test_slack_listener_process.py -q
```

Expected: FAIL because `scripts/slack_listener.py` does not import or route `handle_reaction_event`.

- [ ] **Step 3: Import reaction handler**

In `scripts/slack_listener.py`, add this import:

```python
from institutional_memory.slack_promotion import PromotionRateLimiter, handle_reaction_event
```

If Task 4 already added `from institutional_memory.slack_promotion import PromotionRateLimiter`, replace it with the combined import above.

- [ ] **Step 4: Route reaction events before message ingest**

In `scripts/slack_listener.py`, replace the body after `event = request.payload.get("event", {})` inside `process()` with:

```python
        if event.get("type") == "reaction_added":
            try:
                result = handle_reaction_event(
                    event,
                    client=web_client,
                    allowed_channels=state.promotion_allowed_channels,
                    rate_limiter=state.promotion_rate_limiter,
                    bot_user_id=state.bot_user_id,
                )
            except Exception as exc:
                result = {"status": "error", "error": str(exc)}
                log_event("slack_thread_auto_promote_failed", error=str(exc))
            print(json.dumps(result, ensure_ascii=False), flush=True)
            return

        # Existing ingestion (write to inbox)
        try:
            ingest_result = handle_message_event(event, client=web_client)
        except Exception as exc:
            ingest_result = {"status": "error", "error": str(exc)}
        log_event("slack_event_ingested", **ingest_result)

        # Answer loop (search + reply)
        result = handle_listener_event(event, web_client, state)
        print(json.dumps(result, ensure_ascii=False), flush=True)
```

- [ ] **Step 5: Run routing tests**

Run:

```bash
uv run pytest tests/test_slack_listener_process.py tests/test_listener.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add scripts/slack_listener.py tests/test_slack_listener_process.py
git commit -m "feat: route slack reaction promotion events"
```

---

### Task 6: Document Operator Workflow

**Files:**
- Modify: `README.md`
- Modify: `tests/test_readme_handoff.py`

- [ ] **Step 1: Add failing README assertions**

Append this test to `tests/test_readme_handoff.py`:

```python
def test_readme_documents_slack_auto_promotion():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "PROMOTION_ALLOWED_CHANNELS" in readme
    assert ":memo:" in readme
    assert ":brain:" in readme
    assert "company/corpus/slack/promoted/" in readme
    assert "company/evidence/slack/" in readme
    assert "uv run python scripts/ingest_corpus.py --force" in readme
```

- [ ] **Step 2: Run README test to verify failure**

Run:

```bash
uv run pytest tests/test_readme_handoff.py::test_readme_documents_slack_auto_promotion -q
```

Expected: FAIL because README does not document promotion yet.

- [ ] **Step 3: Add README section**

Append this section under the existing Slack behavior section in `README.md`:

````markdown
### Slack Auto-Promotion

Human-curated Slack memory capture is disabled by default. To enable it, set `PROMOTION_ALLOWED_CHANNELS` to a comma-separated list of channel IDs or channel names:

```text
PROMOTION_ALLOWED_CHANNELS=C123,#engineering
```

When a human reacts to a Slack message with `:memo:` or `:brain:` in an allowed channel, the listener promotes the parent thread into:

- `company/corpus/slack/promoted/<channel>_<thread_ts>.md` — indexed memory card
- `company/evidence/slack/<channel>_<thread_ts>.json` — raw evidence snapshot, not indexed

The memory card becomes searchable only after corpus ingest runs:

```bash
uv run python scripts/ingest_corpus.py --force
```

Promotion does not run from bot replies alone, source attribution alone, or reactions outside `PROMOTION_ALLOWED_CHANNELS`.
````

- [ ] **Step 4: Run README tests**

Run:

```bash
uv run pytest tests/test_readme_handoff.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add README.md tests/test_readme_handoff.py
git commit -m "docs: document slack auto promotion"
```

---

### Task 7: Final Verification

**Files:**
- Verify only

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run pytest tests/test_paths.py tests/test_slack_promotion.py tests/test_listener.py tests/test_slack_listener_process.py tests/test_readme_handoff.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run:

```bash
uv run pytest -q
```

Expected: PASS.

- [ ] **Step 3: Inspect git status**

Run:

```bash
git status --short
```

Expected: only intentional tracked changes are committed. The pre-existing untracked `docs/superpowers/plans/2026-05-16-dashboard-inbox-filter-reingest.md` may remain and must not be staged.

- [ ] **Step 4: Manual dry-run shape check**

Run:

```bash
uv run python - <<'PY'
from institutional_memory.slack_promotion import PromotionRateLimiter, handle_reaction_event

class Client:
    def conversations_history(self, channel, latest, inclusive, limit):
        return {"messages": [{"ts": latest, "user": "U1", "text": "Need precedent"}]}

    def conversations_replies(self, channel, ts):
        return {"messages": [{"ts": ts, "user": "U1", "text": "Need precedent"}]}

    def chat_getPermalink(self, channel, message_ts):
        return {"permalink": "https://example.slack.com/archives/C123/p1710000000000000"}

event = {
    "type": "reaction_added",
    "user": "U1",
    "reaction": "memo",
    "item": {"type": "message", "channel": "C123", "ts": "1710000000.000000"},
}
print(handle_reaction_event(
    event,
    client=Client(),
    allowed_channels={"C123"},
    rate_limiter=PromotionRateLimiter(user_cooldown_seconds=0),
    bot_user_id="UBOT",
))
PY
```

Expected: JSON-like dict printed with `status` either `promoted` on first run or `exists` on later runs, and paths under `company/corpus/slack/promoted/` plus `company/evidence/slack/`.

- [ ] **Step 5: Commit any final verification-only docs correction**

If Step 1 or Step 2 forced a README or test correction, commit it:

```bash
git add README.md tests/test_readme_handoff.py tests/test_slack_promotion.py tests/test_slack_listener_process.py
git commit -m "test: verify slack auto promotion"
```

If no files changed, do not create an empty commit.
