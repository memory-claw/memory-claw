"""Slack listener core logic — event filtering, search, and reply."""

from __future__ import annotations

import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from institutional_memory.audit import log_event
from institutional_memory.config import (
    RELEVANCE_THRESHOLD,
    THREAD_THRESHOLD,
    UNPROMPTED_THRESHOLD,
)
from institutional_memory.search import search_memory


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


# --- Task 2: Channel allowlist and threshold selection ---


def select_threshold(is_mention: bool, is_active_thread: bool) -> float:
    if is_mention:
        return RELEVANCE_THRESHOLD
    if is_active_thread:
        return THREAD_THRESHOLD
    return UNPROMPTED_THRESHOLD


def _channel_map(client: Any) -> dict[str, str]:
    response = client.conversations_list(types="public_channel,private_channel", limit=1000)
    return {ch["name"]: ch["id"] for ch in response.get("channels", [])}


def _resolve_channel_entries(entries: list[str], client: Any | None) -> set[str]:
    ids: set[str] = set()
    names_to_resolve: list[str] = []
    for entry in entries:
        if entry.startswith("C") and not entry.startswith("#"):
            ids.add(entry)
        else:
            names_to_resolve.append(entry.lstrip("#"))
    if names_to_resolve:
        if client is None:
            raise ValueError("Slack client required to resolve channel names")
        channel_map = _channel_map(client)
        for name in names_to_resolve:
            if name not in channel_map:
                raise ValueError(f"Could not resolve channel name: #{name}")
            ids.add(channel_map[name])
    return ids


@dataclass(frozen=True)
class ResolvedChannels:
    channel_ids: frozenset[str]
    allow_all_channels: bool = False


def resolve_channels(
    listener_channels: str,
    fallback_channel: str,
    client: Any = None,
) -> ResolvedChannels:
    raw = listener_channels.strip() if listener_channels else ""
    if not raw:
        raw = fallback_channel.strip() if fallback_channel else ""
    if not raw:
        return ResolvedChannels(channel_ids=frozenset())

    entries = [e.strip() for e in raw.split(",") if e.strip()]
    if "*" in entries:
        if len(entries) > 1:
            raise ValueError("LISTENER_CHANNELS cannot mix '*' with other entries")
        return ResolvedChannels(channel_ids=frozenset(), allow_all_channels=True)

    return ResolvedChannels(channel_ids=frozenset(_resolve_channel_entries(entries, client)))


def parse_channel_threshold_entries(raw: str) -> list[tuple[str, float]]:
    entries: list[tuple[str, float]] = []
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        if ":" not in piece:
            raise ValueError(f"Invalid LISTENER_CHANNEL_THRESHOLDS entry: {piece!r}")
        channel_part, threshold_part = piece.rsplit(":", 1)
        channel_part = channel_part.strip()
        threshold_part = threshold_part.strip()
        if not channel_part:
            raise ValueError(f"Invalid LISTENER_CHANNEL_THRESHOLDS entry: {piece!r}")
        try:
            threshold = float(threshold_part)
        except ValueError as exc:
            raise ValueError(f"Invalid threshold in LISTENER_CHANNEL_THRESHOLDS: {piece!r}") from exc
        entries.append((channel_part, threshold))
    return entries


def resolve_channel_thresholds(raw: str, client: Any | None) -> dict[str, float]:
    if not raw.strip():
        return {}
    by_id: dict[str, float] = {}
    names: list[tuple[str, float]] = []
    for channel_part, threshold in parse_channel_threshold_entries(raw):
        if channel_part.startswith("C") and not channel_part.startswith("#"):
            by_id[channel_part] = threshold
        else:
            names.append((channel_part.lstrip("#"), threshold))
    if names:
        if client is None:
            raise ValueError("Slack client required to resolve LISTENER_CHANNEL_THRESHOLDS names")
        channel_map = _channel_map(client)
        for name, threshold in names:
            if name not in channel_map:
                raise ValueError(f"Could not resolve channel name for threshold: #{name}")
            by_id[channel_map[name]] = threshold
    return by_id


@dataclass
class ListenerState:
    bot_user_id: str
    allowed_channels: set[str]
    dedupe: DedupeSet
    allow_all_channels: bool = False
    channel_thresholds: dict[str, float] = field(default_factory=dict)
    active_threads: set[tuple[str, str]] = field(default_factory=set)


def effective_threshold(
    state: ListenerState,
    channel: str,
    is_mention: bool,
    is_active_thread: bool,
) -> float:
    base = select_threshold(is_mention, is_active_thread)
    if is_mention or is_active_thread:
        return base
    return state.channel_thresholds.get(channel, base)


def build_listener_state(
    *,
    bot_user_id: str,
    listener_channels: str,
    fallback_channel: str,
    client: Any,
    channel_thresholds_raw: str = "",
) -> ListenerState:
    resolved = resolve_channels(listener_channels, fallback_channel, client=client)
    return ListenerState(
        bot_user_id=bot_user_id,
        allowed_channels=set(resolved.channel_ids),
        allow_all_channels=resolved.allow_all_channels,
        channel_thresholds=resolve_channel_thresholds(channel_thresholds_raw, client),
        dedupe=DedupeSet(),
    )


# --- Task 3: Query building ---


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


# --- Task 4: Reply formatting ---

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


# --- Task 5: Main handler ---


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

    if (
        not is_mention
        and not is_active_thread
        and not state.allow_all_channels
        and channel not in state.allowed_channels
    ):
        log_event("listener_skip", channel=channel, reason="not_in_allowlist")
        return {"status": "skipped", "reason": "not_in_allowlist"}

    threshold = effective_threshold(state, channel, is_mention, is_active_thread)
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
