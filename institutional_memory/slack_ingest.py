"""Slack ingestion helpers for inbox and corpus imports."""

from __future__ import annotations

import html
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from institutional_memory.config import (
    COMPANY_CORPUS_PATH,
    COMPANY_INBOX_PATH,
    PROJECT_ROOT,
    SLACK_BOT_TOKEN,
)
from institutional_memory.paths import PathNotAllowedError, safe_corpus_path, safe_inbox_path
from institutional_memory.state import load_processed_records

Mode = Literal["inbox", "corpus"]
INGEST_REMINDER = "run uv run python scripts/ingest_corpus.py --force to make imported Slack corpus files searchable"


def thread_ts(event: dict[str, Any]) -> str:
    value = event.get("thread_ts") or event.get("ts")
    if not value:
        raise ValueError("Slack event missing ts")
    return str(value)


def thread_file_name(event: dict[str, Any]) -> str:
    return f"{event['channel']}_{thread_ts(event)}.md"


def should_ignore_event(event: dict[str, Any]) -> bool:
    return bool(event.get("bot_id") or event.get("subtype") == "bot_message")


def _preview(messages: list[dict[str, Any]]) -> str:
    text = next((str(item.get("text", "")).strip() for item in messages if item.get("text")), "Slack thread")
    text = html.unescape(text)
    text = " ".join(text.split())
    return text[:80] if text else "Slack thread"


def render_thread_markdown(
    *,
    channel: str,
    thread_ts_value: str,
    messages: list[dict[str, Any]],
    permalink: str | None,
    imported_at: str | None = None,
) -> str:
    imported = imported_at or datetime.now(timezone.utc).isoformat()
    lines = [
        f"# Slack Thread: {_preview(messages)}",
        "",
        f"**Channel:** {channel}",
        f"**Thread TS:** {thread_ts_value}",
        f"**Imported At:** {imported}",
        "**Source:** Slack",
        f"**Permalink:** {permalink or ''}",
        "",
        "## Messages",
        "",
    ]
    for message in messages:
        user = message.get("user") or message.get("username") or "unknown"
        text = html.unescape(str(message.get("text", "")).replace("\n", " ")).strip()
        lines.append(f"- {message.get('ts')} {user}: {text}")
    lines.append("")
    return "\n".join(lines)


def destination_path(mode: Mode, filename: str) -> Path:
    if mode == "inbox":
        return safe_inbox_path(str(COMPANY_INBOX_PATH / "slack" / filename))
    if mode == "corpus":
        return safe_corpus_path(str(COMPANY_CORPUS_PATH / "slack" / filename))
    raise ValueError(f"invalid Slack sync mode: {mode}")


def processed_paths() -> set[str]:
    return {str(record.get("path")) for record in load_processed_records() if record.get("path")}


def is_processed(path: Path, processed: set[str]) -> bool:
    rel = str(path.resolve().relative_to(PROJECT_ROOT))
    return rel in processed


def write_thread_file(
    mode: Mode,
    event: dict[str, Any],
    messages: list[dict[str, Any]],
    permalink: str | None,
    force: bool = False,
    processed: set[str] | None = None,
) -> Path:
    path = destination_path(mode, thread_file_name(event))
    processed = processed_paths() if processed is None else processed
    if mode == "inbox" and path.exists() and is_processed(path, processed) and not force:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_thread_markdown(
            channel=str(event["channel"]),
            thread_ts_value=thread_ts(event),
            messages=messages,
            permalink=permalink,
        ),
        encoding="utf-8",
    )
    return path


def _client(client: WebClient | None = None) -> WebClient:
    if client is not None:
        return client
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN missing")
    return WebClient(token=SLACK_BOT_TOKEN)


def _permalink(web_client: WebClient, channel: str, ts: str) -> str | None:
    try:
        return web_client.chat_getPermalink(channel=channel, message_ts=ts).get("permalink")
    except SlackApiError:
        return None


def sync_slack_history(
    *,
    mode: Mode,
    channel: str,
    limit: int,
    client: WebClient | None = None,
    force: bool = False,
    sleep_seconds: float = 1.2,
) -> dict[str, Any]:
    web_client = _client(client)
    response = web_client.conversations_history(channel=channel, limit=limit)
    processed = processed_paths()
    written: list[str] = []
    errors: list[dict[str, str]] = []
    skipped = 0
    for message in response.get("messages", []):
        event = {**message, "channel": channel}
        if should_ignore_event(event):
            skipped += 1
            continue
        root_ts = thread_ts(event)
        try:
            replies = web_client.conversations_replies(channel=channel, ts=root_ts).get("messages", [event])
        except Exception as exc:
            errors.append({"ts": root_ts, "error": str(exc)})
            continue
        path = write_thread_file(
            mode,
            event,
            replies,
            _permalink(web_client, channel, root_ts),
            force=force,
            processed=processed,
        )
        written.append(str(path.relative_to(PROJECT_ROOT)))
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    result: dict[str, Any] = {
        "status": "ok",
        "mode": mode,
        "channel": channel,
        "written": sorted(set(written)),
        "skipped": skipped,
        "errors": errors,
    }
    if mode == "corpus":
        result["note"] = INGEST_REMINDER
    return result


def promote_slack_thread(path: str, force: bool = False) -> dict[str, Any]:
    source = safe_inbox_path(path)
    rel = source.resolve().relative_to(COMPANY_INBOX_PATH.resolve())
    if not rel.parts or rel.parts[0] != "slack":
        raise PathNotAllowedError("Only files under inbox/slack/ can be promoted with promote-slack-thread")
    destination = safe_corpus_path(str(COMPANY_CORPUS_PATH / rel))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return {"status": "exists", "source": str(source.relative_to(PROJECT_ROOT)), "destination": str(destination.relative_to(PROJECT_ROOT)), "note": INGEST_REMINDER}
    shutil.copy2(source, destination)
    return {"status": "promoted", "source": str(source.relative_to(PROJECT_ROOT)), "destination": str(destination.relative_to(PROJECT_ROOT)), "note": INGEST_REMINDER}


def handle_message_event(event: dict[str, Any], client: WebClient | None = None, force: bool = False) -> dict[str, Any]:
    if event.get("type") != "message":
        return {"status": "ignored", "reason": "not_message"}
    if should_ignore_event(event):
        return {"status": "ignored", "reason": "bot_or_subtype"}
    web_client = _client(client)
    channel = str(event["channel"])
    root_ts = thread_ts(event)
    replies = web_client.conversations_replies(channel=channel, ts=root_ts).get("messages", [event])
    path = write_thread_file("inbox", event, replies, _permalink(web_client, channel, root_ts), force=force)
    return {"status": "written", "path": str(path.relative_to(PROJECT_ROOT))}
