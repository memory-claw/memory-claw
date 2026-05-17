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
MAX_SECTION_CHARS = 1200
MAX_CONTEXT_CHARS = 4000
AUDIT_LOOKBACK_LINES = 1000


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


def _card_messages(messages: list[dict[str, Any]], bot_user_id: str) -> list[dict[str, Any]]:
    return [
        message
        for message in messages
        if message.get("user") != bot_user_id and _message_text(message)
    ]


def _message_author(message: dict[str, Any]) -> str:
    return str(message.get("user") or message.get("username") or message.get("bot_id") or "unknown")


def title_from_messages(channel: str, thread_ts: str, messages: list[dict[str, Any]], bot_user_id: str) -> str:
    for message in _card_messages(messages, bot_user_id):
        text = _message_text(message)
        if text:
            return text[:MAX_TITLE_CHARS].rstrip()
    return f"Slack thread {channel} {thread_ts}"


OUTCOME_PATTERNS = [
    r"\bdecision\s*:\s*(?P<text>.+)$",
    r"\bresolution\s*:\s*(?P<text>.+)$",
    r"\bresolved\s*:\s*(?P<text>.+)$",
    r"\bfixed\s*:\s*(?P<text>.+)$",
    r"\bwe\s+(?:decided|agreed)\s+to\s+(?P<text>.+)$",
]


def _explicit_outcome(messages: list[dict[str, Any]], bot_user_id: str) -> str | None:
    for message in reversed(_card_messages(messages, bot_user_id)):
        text = _message_text(message)
        for pattern in OUTCOME_PATTERNS:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group("text").strip()
    return None


def _takeaway(messages: list[dict[str, Any]], bot_user_id: str) -> str | None:
    for message in reversed(_card_messages(messages, bot_user_id)):
        text = _message_text(message)
        match = re.search(r"\b(?:takeaway|lesson)\s*:\s*(?P<text>.+)$", text, flags=re.IGNORECASE)
        if match:
            return match.group("text").strip()
    return None


def _limit_section(text: str, max_chars: int = MAX_SECTION_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    kept: list[str] = []
    total = 0
    for line in text.splitlines():
        next_total = total + len(line) + 1
        if next_total > max_chars:
            break
        kept.append(line)
        total = next_total
    if not kept:
        return text[:max_chars].rsplit(" ", 1)[0].rstrip() + "\n[truncated]"
    return "\n".join(kept).rstrip() + "\n[truncated]"


def _bounded_context(messages: list[dict[str, Any]], bot_user_id: str) -> str:
    card_messages = _card_messages(messages, bot_user_id)
    if not card_messages:
        return ""

    selected: list[dict[str, Any]] = []
    selected.append(card_messages[0])
    for message in card_messages[-10:]:
        if message not in selected:
            selected.append(message)

    lines: list[str] = []
    total = 0
    for message in selected:
        line = f"{_message_author(message)}: {_message_text(message)}"
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
        with AUDIT_LOG.open(encoding="utf-8") as handle:
            lines = deque(handle, maxlen=AUDIT_LOOKBACK_LINES)
        for line in lines:
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
    bot_user_id: str,
    promoted_at: str | None = None,
) -> str:
    title = title_from_messages(channel, thread_ts, messages, bot_user_id)
    happened = _limit_section(_bounded_context(messages, bot_user_id) or "No substantive Slack text captured.")
    outcome = _explicit_outcome(messages, bot_user_id)
    takeaway = _takeaway(messages, bot_user_id)
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
    ]
    if outcome:
        lines.extend(["## Outcome", "", _limit_section(outcome, 500), ""])
    if takeaway:
        lines.extend(["## Reusable Takeaway", "", _limit_section(takeaway, 500), ""])
    if related_sources:
        lines.extend(["## Related Sources", ""])
        lines.extend(f"- {source}" for source in related_sources)
        lines.append("")
    lines.extend(["## Evidence", "", f"Raw Slack thread snapshot: {evidence_rel}", ""])
    return "\n".join(lines)


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
        result = {
            "status": "exists",
            "channel": channel,
            "thread_ts": thread_ts,
            "path": card_rel,
            "evidence": evidence_rel,
            "note": INGEST_REMINDER,
        }
        log_event("slack_thread_auto_promoted", **result, promoted_by=user, reaction=reaction)
        return result

    allowed, reason = rate_limiter.allow(user)
    if not allowed:
        return {"status": "ignored", "reason": reason or "rate_limited"}

    try:
        messages = client.conversations_replies(channel=channel, ts=thread_ts).get("messages", [])
    except Exception as exc:
        log_event("slack_thread_auto_promote_failed", error=str(exc), channel=channel, thread_ts=thread_ts)
        return {"status": "error", "error": str(exc)}

    if not _card_messages(messages, bot_user_id):
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
            bot_user_id=bot_user_id,
        ),
        encoding="utf-8",
    )

    result: dict[str, Any] = {
        "status": "promoted",
        "channel": channel,
        "thread_ts": thread_ts,
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
        promoted_by=user,
        reaction=reaction,
    )
    return result
