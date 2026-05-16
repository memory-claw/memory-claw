"""Long-running Slack Socket Mode listener.

Run outside OpenClaw:
    uv run python scripts/slack_listener.py
"""

from __future__ import annotations

import json
import sys
from threading import Event

from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from institutional_memory.audit import log_event
from institutional_memory.config import SLACK_APP_TOKEN, SLACK_BOT_TOKEN
from institutional_memory.slack_ingest import handle_message_event


def process(client: SocketModeClient, request: SocketModeRequest) -> None:
    if request.type == "events_api":
        client.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))
        event = request.payload.get("event", {})
        try:
            result = handle_message_event(event, client=WebClient(token=SLACK_BOT_TOKEN))
        except Exception as exc:
            result = {"status": "error", "error": str(exc)}
        log_event("slack_event_ingested", **result)
        print(json.dumps(result, ensure_ascii=False), flush=True)


def main() -> int:
    if not SLACK_APP_TOKEN:
        print(json.dumps({"status": "error", "error": "SLACK_APP_TOKEN missing"}), file=sys.stderr)
        return 1
    if not SLACK_BOT_TOKEN:
        print(json.dumps({"status": "error", "error": "SLACK_BOT_TOKEN missing"}), file=sys.stderr)
        return 1
    client = SocketModeClient(app_token=SLACK_APP_TOKEN, web_client=WebClient(token=SLACK_BOT_TOKEN))
    client.socket_mode_request_listeners.append(process)
    client.connect()
    print(json.dumps({"status": "listening"}), flush=True)
    Event().wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
