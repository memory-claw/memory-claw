"""Slack listener core logic — event filtering, search, and reply."""

from __future__ import annotations

import json
import re
import shutil
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from institutional_memory.audit import log_event
from institutional_memory.config import (
    AUDIT_LOG,
    CHROMA_PATH,
    COMPANY_INBOX_PATH,
    COMPANY_CORPUS_PATH,
    PROJECT_ROOT,
    RUNTIME_PATH,
    RELEVANCE_THRESHOLD,
    THREAD_THRESHOLD,
    UNPROMPTED_THRESHOLD,
)
from institutional_memory.response_composer import (
    compose_slack_answer,
    detect_response_intent,
    detect_thread_advice_command,
    should_accept_advice_offer,
)
from institutional_memory.search import search_memory
from institutional_memory.slack_ingest import sync_slack_history
from institutional_memory.slack_promotion import PromotionRateLimiter
from institutional_memory.slack_promotion import handle_reaction_event as promote_slack_thread_from_command
from institutional_memory.state import reset_processed
from institutional_memory.source_policy import (
    apply_source_policy,
    load_source_policy,
    parse_source_command,
    render_source_command,
)


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
        if entry.startswith(("C", "G")) and not entry.startswith("#"):
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
    text_override: str | None = None,
) -> str:
    text = text_override if text_override is not None else strip_mention(str(event.get("text", "")), bot_user_id)
    context = build_thread_context(event, bot_user_id=bot_user_id, client=client)
    if context:
        return f"{context}\n\n{text}"
    return text


# --- Task 4: Reply formatting ---

MAX_HITS = 3
MAX_SNIPPET_CHARS = 150
PROMOTION_CHANNELS_PATH = RUNTIME_PATH / "promotion_channels.json"


@dataclass(frozen=True)
class MemCommand:
    kind: str
    args: str = ""


def parse_mem_command(text: str) -> MemCommand | None:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return None

    lowered = normalized.lower()
    if lowered == "/mem" or lowered == "mem":
        return MemCommand("help")
    if lowered.startswith("/mem "):
        remainder = normalized[5:].strip()
    elif lowered.startswith("mem "):
        remainder = normalized[4:].strip()
    else:
        return None

    if not remainder:
        return MemCommand("help")

    verb, _, args = remainder.partition(" ")
    verb = verb.lower()
    args = args.strip()

    aliases = {
        "help": "help",
        "ask": "ask",
        "find": "ask",
        "precedent": "precedent",
        "status": "status",
        "save-thread": "save-thread",
        "save": "save-thread",
        "allow-promote-here": "allow-promote-here",
        "sync": "sync",
        "demo-reset": "demo-reset",
    }
    if verb in {"source", "show-source"} and args:
        return MemCommand("source", f"show source {args}")
    if verb in {"full-source", "show-full-source"} and args:
        return MemCommand("source", f"show full source {args}")
    if verb in aliases:
        return MemCommand(aliases[verb], args)
    return MemCommand("ask", remainder)


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


def format_no_shareable_hits_reply() -> str:
    return "\U0001f50d I didn't find Slack-shareable context in institutional memory."


def _format_mem_help() -> str:
    return "\n".join(
        [
            "Memory commands:",
            "- /mem ask <question>",
            "- /mem precedent <question>",
            "- /mem source <n>",
            "- /mem full-source <n>",
            "- /mem save-thread",
            "- /mem allow-promote-here",
            "- /mem sync current <limit>",
            "- /mem status",
            "- /mem demo-reset confirm",
        ]
    )


def _format_mem_status(state: "ListenerState") -> str:
    return "\n".join(
        [
            "Memory status:",
            f"- active threads: {len(state.active_threads)}",
            f"- cached source lists: {len(state.thread_source_refs)}",
            f"- allowed channels: {len(state.allowed_channels)}",
            f"- promotion channels: {len(state.promotion_allowed_channels)}",
            f"- runtime path: {'present' if RUNTIME_PATH.exists() else 'missing'}",
            f"- chroma path: {'present' if CHROMA_PATH.exists() else 'missing'}",
            f"- corpus path: {'present' if COMPANY_CORPUS_PATH.exists() else 'missing'}",
            f"- audit log: {'present' if AUDIT_LOG.exists() else 'missing'}",
        ]
    )


def _format_promotion_result(result: dict[str, Any]) -> str:
    status = str(result.get("status", "unknown"))
    lines = [f"Save-thread status: {status}."]
    if result.get("path"):
        lines.append(f"Path: {result['path']}")
    if result.get("note"):
        lines.append(str(result["note"]))
    if result.get("reason"):
        lines.append(f"Reason: {result['reason']}")
    if result.get("error"):
        lines.append(f"Error: {result['error']}")
    return "\n".join(lines)


def _format_allow_promote_here(channel: str) -> str:
    return (
        f"Promotion enabled here ({channel}). "
        "React with :brain: to save threads to corpus."
    )


def _format_sync_result(result: dict[str, Any]) -> str:
    written = result.get("written") or []
    count = len(written) if isinstance(written, list) else 0
    noun = "thread" if count == 1 else "threads"
    lines = [f"Imported {count} {noun} from Slack."]
    if result.get("skipped"):
        lines.append(f"Skipped: {result['skipped']}")
    errors = result.get("errors") or []
    if errors:
        lines.append(f"Errors: {len(errors)}")
    if result.get("note"):
        lines.append(str(result["note"]))
    return "\n".join(lines)


def _format_reset_result(result: dict[str, Any]) -> str:
    return (
        "Demo reset complete."
        f"\n- clear audit: {result.get('clear_audit')}"
        f"\n- clear chroma: {result.get('clear_chroma')}"
        f"\n- clear slack inbox: {result.get('clear_slack_inbox')}"
    )


def load_persisted_promotion_channels() -> set[str]:
    if not PROMOTION_CHANNELS_PATH.exists():
        return set()
    try:
        data = json.loads(PROMOTION_CHANNELS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    channels = data.get("channels") if isinstance(data, dict) else []
    return {str(channel) for channel in channels if str(channel).startswith(("C", "G"))}


def save_persisted_promotion_channels(channels: set[str]) -> None:
    PROMOTION_CHANNELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"channels": sorted(channels)}
    PROMOTION_CHANNELS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def reset_demo_state_from_command() -> dict[str, Any]:
    RUNTIME_PATH.mkdir(parents=True, exist_ok=True)
    for child in RUNTIME_PATH.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)

    reset_processed()
    shutil.rmtree(CHROMA_PATH, ignore_errors=True)
    (PROJECT_ROOT / "ingested_files.json").unlink(missing_ok=True)

    slack_inbox = COMPANY_INBOX_PATH / "slack"
    if slack_inbox.exists():
        for child in slack_inbox.rglob("*"):
            if child.is_file() and child.name != ".gitkeep":
                child.unlink(missing_ok=True)

    AUDIT_LOG.unlink(missing_ok=True)
    return {
        "status": "reset",
        "clear_audit": True,
        "clear_chroma": True,
        "clear_slack_inbox": True,
    }


def _parse_sync_args(args: str, current_channel: str) -> tuple[str, int]:
    parts = args.split()
    if not parts:
        return current_channel, 20

    channel = parts[0]
    limit_text = parts[1] if len(parts) > 1 else "20"
    if channel.lower() in {"current", "here", "this"}:
        channel = current_channel
    if channel.startswith("<#"):
        channel = channel[2:].split("|", 1)[0].rstrip(">")
    if channel.startswith("#"):
        raise ValueError("Use current, here, or a Slack channel ID for /mem sync.")

    limit = int(limit_text)
    if limit < 1 or limit > 100:
        raise ValueError("Sync limit must be between 1 and 100.")
    return channel, limit


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
    thread_footer_signatures: dict[tuple[str, str], tuple[str, ...]] = field(default_factory=dict)
    thread_advice_offer_pending: set[tuple[str, str]] = field(default_factory=set)
    thread_source_refs: dict[tuple[str, str], list[dict[str, Any]]] = field(default_factory=dict)
    thread_full_source_cooldowns: dict[tuple[str, str, int], float] = field(default_factory=dict)
    promotion_allowed_channels: set[str] = field(default_factory=set)
    promotion_rate_limiter: PromotionRateLimiter | None = None


def _is_mention(event: dict[str, Any], bot_user_id: str) -> bool:
    if event.get("type") == "app_mention":
        return True
    return f"<@{bot_user_id}>" in str(event.get("text", ""))


def _thread_key(channel: str, thread_ts: str) -> tuple[str, str]:
    return (channel, thread_ts)


def _advice_mode_reply(mode: str) -> str:
    return f"Advice mode is {mode} for this thread."


def _post_reply(client: Any, channel: str, thread_ts: str | None, text: str) -> None:
    kwargs = {"channel": channel, "text": text}
    if thread_ts:
        kwargs["thread_ts"] = thread_ts
    client.chat_postMessage(**kwargs)


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
) -> tuple[str, tuple[str, str, int] | None] | None:
    command = parse_source_command(text)
    if command is None:
        return None

    refs = state.thread_source_refs.get(key)
    if not refs:
        return ("I do not have a recent source list for this thread.", None)

    cooldown_key = None
    if command.kind == "full":
        cooldown_key = (key[0], key[1], command.index)
        now = time.monotonic()
        previous = state.thread_full_source_cooldowns.get(cooldown_key)
        if previous is not None and now - previous < FULL_SOURCE_COOLDOWN_SECONDS:
            remaining = round(FULL_SOURCE_COOLDOWN_SECONDS - (now - previous))
            return (
                f"Please wait {remaining} seconds before showing full source {command.index} again.",
                None,
            )

    rendered = render_source_command(command, refs)
    if rendered.get("status") != "ok":
        cooldown_key = None
    return (rendered["text"], cooldown_key)


def _footer_signature(hits: list[dict[str, Any]], advice_mode: str) -> tuple[str, ...]:
    commands: list[str] = []
    if advice_mode == "offer":
        commands.append("advice")
    for index, hit in enumerate(hits[:MAX_HITS], start=1):
        access = str(hit.get("access", ""))
        if access in {"excerpt", "share"}:
            commands.append(f"show source {index}")
        if access == "share":
            commands.append(f"show full source {index}")
    return tuple(commands)


def handle_listener_event(
    event: dict[str, Any],
    client: Any,
    state: ListenerState,
) -> dict[str, Any]:
    channel = str(event.get("channel", ""))
    ts = str(event.get("ts", ""))
    thread_ts = event.get("thread_ts") or (None if event.get("slash_command") else ts)

    is_mention = _is_mention(event, state.bot_user_id)
    is_active_thread = _thread_key(channel, str(event.get("thread_ts", ""))) in state.active_threads
    is_short_active_thread_reply = is_active_thread and len(str(event.get("text", "")).strip()) < 5
    command_text = strip_mention(str(event.get("text", "")), state.bot_user_id)
    mem_command = parse_mem_command(command_text)
    is_explicit_command = mem_command is not None

    if event.get("bot_id") or event.get("user") == state.bot_user_id or event.get("subtype"):
        return {"status": "skipped", "reason": "filtered"}
    if should_skip(event, state.bot_user_id) and not is_short_active_thread_reply and not is_explicit_command:
        return {"status": "skipped", "reason": "filtered"}

    if state.dedupe.seen(channel, ts):
        return {"status": "skipped", "reason": "dedupe"}

    if not is_mention and not is_explicit_command and not is_active_thread and channel not in state.allowed_channels:
        log_event("listener_skip", channel=channel, reason="not_in_allowlist")
        return {"status": "skipped", "reason": "not_in_allowlist"}

    key = _thread_key(channel, str(thread_ts))
    forced_query: str | None = None
    forced_intent: str | None = None

    if mem_command:
        if mem_command.kind == "help":
            try:
                _post_reply(client, channel, thread_ts, _format_mem_help())
                log_event("listener_reply", channel=channel, thread_ts=thread_ts, query="", top_score=0, sources=[], triggered_by="command", response_intent="help")
                return {"status": "replied", "hits": 0, "triggered_by": "command"}
            except Exception as exc:
                log_event("listener_error", channel=channel, error=str(exc))
                return {"status": "error", "error": str(exc)}

        if mem_command.kind == "status":
            try:
                _post_reply(client, channel, thread_ts, _format_mem_status(state))
                log_event("listener_reply", channel=channel, thread_ts=thread_ts, query="", top_score=0, sources=[], triggered_by="command", response_intent="status")
                return {"status": "replied", "hits": 0, "triggered_by": "command"}
            except Exception as exc:
                log_event("listener_error", channel=channel, error=str(exc))
                return {"status": "error", "error": str(exc)}

        if mem_command.kind == "source":
            command_text = mem_command.args

        if mem_command.kind == "save-thread":
            if state.promotion_rate_limiter is None:
                state.promotion_rate_limiter = PromotionRateLimiter()
            synthetic_event = {
                "reaction": "brain",
                "user": event.get("user"),
                "item": {"type": "message", "channel": channel, "ts": str(thread_ts or ts)},
            }
            try:
                result = promote_slack_thread_from_command(
                    event=synthetic_event,
                    client=client,
                    allowed_channels=state.promotion_allowed_channels or state.allowed_channels or {channel},
                    rate_limiter=state.promotion_rate_limiter,
                    bot_user_id=state.bot_user_id,
                )
                _post_reply(client, channel, thread_ts, _format_promotion_result(result))
                log_event("listener_reply", channel=channel, thread_ts=thread_ts, query="", top_score=0, sources=[], triggered_by="command", response_intent="save-thread")
                return {"status": "replied", "hits": 0, "triggered_by": "command"}
            except Exception as exc:
                log_event("listener_error", channel=channel, error=str(exc))
                return {"status": "error", "error": str(exc)}

        if mem_command.kind == "allow-promote-here":
            state.promotion_allowed_channels.add(channel)
            try:
                save_persisted_promotion_channels(state.promotion_allowed_channels)
                _post_reply(client, channel, thread_ts, _format_allow_promote_here(channel))
                log_event("listener_reply", channel=channel, thread_ts=thread_ts, query="", top_score=0, sources=[], triggered_by="command", response_intent="allow-promote-here")
                return {"status": "replied", "hits": 0, "triggered_by": "command"}
            except Exception as exc:
                log_event("listener_error", channel=channel, error=str(exc))
                return {"status": "error", "error": str(exc)}

        if mem_command.kind == "sync":
            try:
                sync_channel, sync_limit = _parse_sync_args(mem_command.args, channel)
                result = sync_slack_history(
                    mode="corpus",
                    channel=sync_channel,
                    limit=sync_limit,
                    client=client,
                    force=False,
                    sleep_seconds=0,
                )
                _post_reply(client, channel, thread_ts, _format_sync_result(result))
                log_event("listener_reply", channel=channel, thread_ts=thread_ts, query="", top_score=0, sources=[], triggered_by="command", response_intent="sync")
                return {"status": "replied", "hits": 0, "triggered_by": "command"}
            except Exception as exc:
                try:
                    _post_reply(client, channel, thread_ts, f"Sync failed: {exc}")
                except Exception:
                    pass
                log_event("listener_error", channel=channel, error=str(exc))
                return {"status": "error", "error": str(exc)}

        if mem_command.kind == "demo-reset":
            if mem_command.args.strip().lower() != "confirm":
                reply = "Demo reset clears audit, Chroma, runtime state, and Slack inbox imports. Run /mem demo-reset confirm to continue."
                try:
                    _post_reply(client, channel, thread_ts, reply)
                    log_event("listener_reply", channel=channel, thread_ts=thread_ts, query="", top_score=0, sources=[], triggered_by="command", response_intent="demo-reset")
                    return {"status": "replied", "hits": 0, "triggered_by": "command"}
                except Exception as exc:
                    log_event("listener_error", channel=channel, error=str(exc))
                    return {"status": "error", "error": str(exc)}

            try:
                result = reset_demo_state_from_command()
                _post_reply(client, channel, thread_ts, _format_reset_result(result))
                log_event("listener_reply", channel=channel, thread_ts=thread_ts, query="", top_score=0, sources=[], triggered_by="command", response_intent="demo-reset")
                return {"status": "replied", "hits": 0, "triggered_by": "command"}
            except Exception as exc:
                log_event("listener_error", channel=channel, error=str(exc))
                return {"status": "error", "error": str(exc)}

        if mem_command.kind == "ask":
            forced_query = mem_command.args
            forced_intent = "context"
        elif mem_command.kind == "precedent":
            forced_query = mem_command.args
            forced_intent = "precedent"

    advice_mode = _handle_advice_mode_command(command_text, key, state)
    if advice_mode:
        advice_reply = _advice_mode_reply(advice_mode)
        try:
            _post_reply(client, channel, thread_ts, advice_reply)
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

    try:
        source_result = _handle_source_command(command_text, key, state)
    except Exception as exc:
        log_event("listener_error", channel=channel, error=str(exc))
        return {"status": "error", "error": str(exc)}
    if source_result:
        source_reply, cooldown_key = source_result
        advice_mode = state.thread_advice_modes.get(key, "offer")
        try:
            _post_reply(client, channel, thread_ts, source_reply)
            if cooldown_key is not None:
                state.thread_full_source_cooldowns[cooldown_key] = time.monotonic()
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

    threshold = select_threshold(is_mention or is_explicit_command, is_active_thread)
    query = build_search_query(event, bot_user_id=state.bot_user_id, client=client, text_override=forced_query)

    try:
        hits = search_memory(query, threshold=threshold)
    except Exception as exc:
        log_event("listener_error", channel=channel, error=str(exc))
        return {"status": "error", "error": str(exc)}

    if not hits:
        if is_mention or is_explicit_command:
            triggered_by = "command" if is_explicit_command else "mention"
            try:
                _post_reply(client, channel, thread_ts, format_no_hits_reply())
                log_event(
                    "listener_reply",
                    channel=channel,
                    thread_ts=thread_ts,
                    query=query,
                    top_score=0,
                    sources=[],
                    triggered_by=triggered_by,
                )
                return {"status": "replied", "hits": 0, "triggered_by": triggered_by}
            except Exception as exc:
                log_event("listener_error", channel=channel, error=str(exc))
                return {"status": "error", "error": str(exc)}
        log_event("listener_skip", channel=channel, reason="below_threshold", top_score=0)
        return {"status": "skipped", "reason": "below_threshold"}

    try:
        policy = load_source_policy()
    except Exception as exc:
        log_event("listener_error", channel=channel, error=str(exc))
        return {"status": "error", "error": str(exc)}

    visible_hits = apply_source_policy(hits, policy)
    if not visible_hits:
        if is_mention or is_explicit_command:
            triggered_by = "command" if is_explicit_command else "mention"
            try:
                _post_reply(client, channel, thread_ts, format_no_shareable_hits_reply())
                log_event(
                    "listener_reply",
                    channel=channel,
                    thread_ts=thread_ts,
                    query=query,
                    top_score=0,
                    sources=[],
                    triggered_by=triggered_by,
                    response_intent="context",
                    advice_mode=state.thread_advice_modes.get(key, "offer"),
                )
                return {"status": "replied", "hits": 0, "triggered_by": triggered_by}
            except Exception as exc:
                log_event("listener_error", channel=channel, error=str(exc))
                return {"status": "error", "error": str(exc)}
        log_event(
            "listener_skip",
            channel=channel,
            reason="source_policy_filtered",
            top_score=hits[0]["score"],
        )
        return {"status": "skipped", "reason": "source_policy_filtered"}

    triggered_by = "command" if is_explicit_command else ("mention" if is_mention else ("thread" if is_active_thread else "unprompted"))
    intent = forced_intent or detect_response_intent(command_text)
    advice_mode = state.thread_advice_modes.get(key, "offer")
    footer_signature = _footer_signature(visible_hits, advice_mode)
    include_footer = (
        advice_mode == "offer"
        and bool(footer_signature)
        and state.thread_footer_signatures.get(key) != footer_signature
    )
    reply_text = compose_slack_answer(
        query,
        visible_hits,
        intent=intent,
        advice_mode=advice_mode,
        include_footer=include_footer,
    )

    try:
        _post_reply(client, channel, thread_ts, reply_text)
    except Exception as exc:
        log_event("listener_error", channel=channel, error=str(exc))
        return {"status": "error", "error": str(exc)}

    if thread_ts:
        state.active_threads.add((channel, str(thread_ts)))
    state.thread_source_refs[key] = visible_hits[:MAX_HITS]
    if include_footer:
        state.thread_footer_shown.add(key)
        state.thread_footer_signatures[key] = footer_signature
        if '"advice"' in reply_text:
            state.thread_advice_offer_pending.add(key)
    sources = [h["source"] for h in visible_hits[:MAX_HITS]]
    log_event(
        "listener_reply",
        channel=channel,
        thread_ts=thread_ts,
        query=query,
        top_score=hits[0]["score"],
        sources=sources,
        triggered_by=triggered_by,
        response_intent=intent,
        advice_mode=advice_mode,
    )
    return {"status": "replied", "hits": len(visible_hits), "triggered_by": triggered_by}
