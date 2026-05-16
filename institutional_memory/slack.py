"""Slack delivery helpers."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from institutional_memory.config import SLACK_BOT_TOKEN, SLACK_CHANNEL, SLACK_WEBHOOK_URL
from institutional_memory.paths import PathNotAllowedError, safe_runtime_path

SOURCE_PATTERN = re.compile(r"\bcorpus/[A-Za-z0-9_.-]+\.txt\b")


def _read_message(message_file: str | None, message: str | None) -> str:
    if message_file:
        path = safe_runtime_path(message_file)
        return path.read_text(encoding="utf-8")
    if message:
        return message
    raise ValueError("Provide --message-file or --message")


def source_attributions(text: str) -> list[str]:
    return sorted(set(SOURCE_PATTERN.findall(text)))


def _webhook_post(text: str) -> dict:
    if not SLACK_WEBHOOK_URL:
        return {"status": "slack_failed", "error": "SLACK_BOT_TOKEN is missing and no webhook fallback is configured"}
    request = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            if response.status >= 300:
                return {"status": "slack_failed", "error": f"webhook HTTP {response.status}: {body}"}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"status": "slack_failed", "error": str(exc)}
    return {"status": "sent", "channel": "webhook"}


def send_slack_message(
    channel: str | None,
    message_file: str | None,
    message: str | None,
) -> dict:
    try:
        text = _read_message(message_file, message).strip()
        if not text:
            return {"status": "slack_failed", "error": "message is empty"}
    except (PathNotAllowedError, OSError, ValueError) as exc:
        return {"status": "slack_failed", "error": str(exc)}

    target = channel or SLACK_CHANNEL
    if SLACK_BOT_TOKEN:
        try:
            WebClient(token=SLACK_BOT_TOKEN).chat_postMessage(channel=target, text=text)
            return {
                "status": "sent",
                "channel": target,
                "source_attributions": source_attributions(text),
            }
        except SlackApiError as exc:
            fallback = _webhook_post(text)
            if fallback["status"] == "sent":
                fallback["bot_token_error"] = exc.response.get("error", "slack_api_error")
                fallback["source_attributions"] = source_attributions(text)
            return fallback
    fallback = _webhook_post(text)
    if fallback["status"] == "sent":
        fallback["source_attributions"] = source_attributions(text)
    return fallback
