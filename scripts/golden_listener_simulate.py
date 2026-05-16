#!/usr/bin/env python3
"""Simulate golden @mention events against the listener (no live Slack post)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from institutional_memory.config import (
    LISTENER_CHANNEL_THRESHOLDS,
    LISTENER_CHANNELS,
    SLACK_BOT_TOKEN,
    SLACK_CHANNEL,
)
from institutional_memory.listener import build_listener_state, handle_listener_event
from slack_sdk import WebClient

CHANNEL = "C0B3SJEERBR"
BOT_ID = "U0B5204MF3J"


def _run_case(case_id: str, event: dict, expect: str, state) -> dict:
    client = MagicMock(spec=WebClient)
    result = handle_listener_event(event, client, state)
    ok = result.get("status") == expect
    return {"id": case_id, "ok": ok, "expect": expect, "result": result}


def main() -> int:
    if not SLACK_BOT_TOKEN:
        print(json.dumps({"ok": False, "error": "SLACK_BOT_TOKEN missing"}), file=sys.stderr)
        return 1

    web = WebClient(token=SLACK_BOT_TOKEN)
    state = build_listener_state(
        bot_user_id=BOT_ID,
        listener_channels=LISTENER_CHANNELS,
        fallback_channel=SLACK_CHANNEL,
        client=web,
        channel_thresholds_raw=LISTENER_CHANNEL_THRESHOLDS,
    )
    if state.allow_all_channels:
        channel = CHANNEL
    else:
        channel = next(iter(state.allowed_channels), CHANNEL)

    cases = [
        (
            "G1",
            {
                "type": "app_mention",
                "channel": channel,
                "ts": "1000.1",
                "user": "UUSER",
                "text": (
                    f"<@{BOT_ID}> We're about to close the Vantara deal — custom SSO and "
                    "white-label. I'll send the contract today and loop in engineering "
                    "after it's signed. 8 weeks should be fine."
                ),
            },
            "replied",
        ),
        (
            "G2",
            {
                "type": "app_mention",
                "channel": channel,
                "ts": "1000.2",
                "user": "UUSER",
                "text": f"<@{BOT_ID}> figured we can add rate limiting after launch",
            },
            "replied",
        ),
        (
            "G3",
            {
                "type": "app_mention",
                "channel": channel,
                "ts": "1000.3",
                "user": "UUSER",
                "text": f"<@{BOT_ID}> should I just send them our .env to get them started",
            },
            "replied",
        ),
        (
            "G4",
            {
                "type": "app_mention",
                "channel": channel,
                "ts": "1000.4",
                "user": "UUSER",
                "text": f"<@{BOT_ID}> random nonsense xyz123",
            },
            "replied",
        ),
        (
            "N1",
            {
                "type": "message",
                "channel": channel,
                "ts": "1000.5",
                "user": "UUSER",
                "text": "Anyone else think we should switch to dark mode by default",
            },
            "skipped",
        ),
    ]

    results = [_run_case(case_id, event, expect, state) for case_id, event, expect in cases]
    ok = all(r["ok"] for r in results)
    print(json.dumps({"ok": ok, "cases": results}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
