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
from institutional_memory.response_composer import (
    detect_thread_advice_command,
    should_accept_advice_offer,
)
from institutional_memory.search import search_memory
from institutional_memory.source_policy import parse_source_command, render_source_command


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


# --- Task 3: Query building ---


def strip_mention(text: str, bot_user_id: str) -> str:
    return re.sub(rf"<@{re.escape(bot_user_id)}>", "", text).strip()


def _is_bot_message(message: dict[str, Any], bot_user_id: str) -> bool:
    return bool(message.get("bot_id") or message.get("user") == bot_user_id)


THREAD_CONTEXT_FETCH_LIMIT = 100
THREAD_CONTEXT_MAX_PAGES = 5


def build_thread_context(
    event: dict[str, Any],
    bot_user_id: str,
    client: Any,
    limit: int = 10,
    max_chars: int = 2000,
) -> str:
    thread_ts = event.get("thread_ts")

    if not thread_ts or client is None:
        return ""

    messages: list[dict[str, Any]] = []
    cursor: str | None = None
    try:
        for _ in range(THREAD_CONTEXT_MAX_PAGES):
            kwargs = {
                "channel": event["channel"],
                "ts": thread_ts,
                "limit": max(limit, THREAD_CONTEXT_FETCH_LIMIT),
            }
            if cursor:
                kwargs["cursor"] = cursor
            response = client.conversations_replies(**kwargs)
            messages.extend(response.get("messages", []))
            cursor = (response.get("response_metadata") or {}).get("next_cursor") or None
            if not cursor:
                break
    except Exception:
        return ""

    human_texts: list[str] = []
    for msg in messages:
        if _is_bot_message(msg, bot_user_id):
            continue
        msg_text = strip_mention(str(msg.get("text", "")), bot_user_id).strip()
        if msg_text:
            human_texts.append(msg_text)

    recent = human_texts[-limit:]
    context = "\n".join(recent)
    if len(context) <= max_chars:
        return context

    tail = context[-max_chars:]
    newline_index = tail.find("\n")
    if newline_index >= 0:
        return tail[newline_index + 1 :]
    return tail


def build_search_query(
    event: dict[str, Any],
    bot_user_id: str,
    client: Any,
) -> str:
    text = strip_mention(str(event.get("text", "")), bot_user_id)
    context = build_thread_context(event, bot_user_id=bot_user_id, client=client)
    if context:
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

FULL_SOURCE_COOLDOWN_SECONDS = 30.0


@dataclass
class ListenerState:
    bot_user_id: str
    allowed_channels: set[str]
    dedupe: DedupeSet
    active_threads: set[tuple[str, str]] = field(default_factory=set)
    thread_advice_modes: dict[tuple[str, str], str] = field(default_factory=dict)
    thread_footer_shown: set[tuple[str, str]] = field(default_factory=set)
    thread_advice_offer_pending: set[tuple[str, str]] = field(default_factory=set)
    thread_source_refs: dict[tuple[str, str], list[dict[str, Any]]] = field(default_factory=dict)
    thread_full_source_cooldowns: dict[tuple[str, str, int], float] = field(default_factory=dict)


def _is_mention(event: dict[str, Any], bot_user_id: str) -> bool:
    if event.get("type") == "app_mention":
        return True
    return f"<@{bot_user_id}>" in str(event.get("text", ""))


def _thread_key(channel: str, thread_ts: str) -> tuple[str, str]:
    return (channel, thread_ts)


def _advice_mode_reply(mode: str) -> str:
    return f"Advice mode is {mode} for this thread."


def _handle_advice_mode_command(
    text: str,
    key: tuple[str, str],
    state: ListenerState,
) -> str | None:
    mode = detect_thread_advice_command(text)
    if mode is None:
        mode = should_accept_advice_offer(
            text,
            pending_offer=key in state.thread_advice_offer_pending,
        )
    return mode


def _commit_advice_mode(
    mode: str,
    key: tuple[str, str],
    state: ListenerState,
) -> None:
    state.thread_advice_modes[key] = mode
    state.thread_advice_offer_pending.discard(key)


def _handle_source_command(
    text: str,
    key: tuple[str, str],
    state: ListenerState,
) -> str | None:
    command = parse_source_command(text)
    if command is None:
        return None

    refs = state.thread_source_refs.get(key)
    if not refs:
        return "I do not have a recent source list for this thread."

    if command.kind == "full":
        cooldown_key = (key[0], key[1], command.index)
        now = time.monotonic()
        previous = state.thread_full_source_cooldowns.get(cooldown_key)
        if previous is not None and now - previous < FULL_SOURCE_COOLDOWN_SECONDS:
            remaining = round(FULL_SOURCE_COOLDOWN_SECONDS - (now - previous))
            return f"Please wait {remaining} seconds before showing full source {command.index} again."
        state.thread_full_source_cooldowns[cooldown_key] = now

    return render_source_command(command, refs)["text"]


def handle_listener_event(
    event: dict[str, Any],
    client: Any,
    state: ListenerState,
) -> dict[str, Any]:
    channel = str(event.get("channel", ""))
    ts = str(event.get("ts", ""))
    thread_ts = event.get("thread_ts") or ts

    is_mention = _is_mention(event, state.bot_user_id)
    is_active_thread = _thread_key(channel, str(event.get("thread_ts", ""))) in state.active_threads
    is_short_active_thread_reply = is_active_thread and len(str(event.get("text", "")).strip()) < 5

    if event.get("bot_id") or event.get("user") == state.bot_user_id or event.get("subtype"):
        return {"status": "skipped", "reason": "filtered"}
    if should_skip(event, state.bot_user_id) and not is_short_active_thread_reply:
        return {"status": "skipped", "reason": "filtered"}

    if state.dedupe.seen(channel, ts):
        return {"status": "skipped", "reason": "dedupe"}

    if not is_mention and not is_active_thread and channel not in state.allowed_channels:
        log_event("listener_skip", channel=channel, reason="not_in_allowlist")
        return {"status": "skipped", "reason": "not_in_allowlist"}

    key = _thread_key(channel, str(thread_ts))
    command_text = strip_mention(str(event.get("text", "")), state.bot_user_id)
    advice_mode = _handle_advice_mode_command(command_text, key, state)
    if advice_mode:
        advice_reply = _advice_mode_reply(advice_mode)
        try:
            client.chat_postMessage(channel=channel, text=advice_reply, thread_ts=thread_ts)
            _commit_advice_mode(advice_mode, key, state)
            log_event(
                "listener_reply",
                channel=channel,
                thread_ts=thread_ts,
                query="",
                top_score=0,
                sources=[],
                triggered_by="thread",
                response_intent="toggle",
                advice_mode=advice_mode,
            )
            return {"status": "replied", "hits": 0, "triggered_by": "thread"}
        except Exception as exc:
            log_event("listener_error", channel=channel, error=str(exc))
            return {"status": "error", "error": str(exc)}

    source_reply = _handle_source_command(command_text, key, state)
    if source_reply:
        advice_mode = state.thread_advice_modes.get(key, "offer")
        try:
            client.chat_postMessage(channel=channel, text=source_reply, thread_ts=thread_ts)
            log_event(
                "listener_reply",
                channel=channel,
                thread_ts=thread_ts,
                query="",
                top_score=0,
                sources=[],
                triggered_by="thread",
                response_intent="source",
                advice_mode=advice_mode,
            )
            return {"status": "replied", "hits": 0, "triggered_by": "thread"}
        except Exception as exc:
            log_event("listener_error", channel=channel, error=str(exc))
            return {"status": "error", "error": str(exc)}

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
