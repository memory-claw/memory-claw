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
    LISTENER_CHANNEL_THRESHOLDS,
    LISTENER_CHANNELS,
    SLACK_APP_TOKEN,
    SLACK_BOT_TOKEN,
    SLACK_CHANNEL,
)
from institutional_memory.listener import build_listener_state, handle_listener_event
from institutional_memory.openclaw_wake import maybe_wake_openclaw
from institutional_memory.slack_ingest import handle_message_event


def _build_state(web_client: WebClient):
    auth = web_client.auth_test()
    return build_listener_state(
        bot_user_id=auth["user_id"],
        listener_channels=LISTENER_CHANNELS,
        fallback_channel=SLACK_CHANNEL,
        client=web_client,
        channel_thresholds_raw=LISTENER_CHANNEL_THRESHOLDS,
    )


def _channels_for_log(state) -> str | list[str]:
    if state.allow_all_channels:
        return "all"
    return sorted(state.allowed_channels)


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
        maybe_wake_openclaw(ingest_result)

        # Answer loop (search + reply)
        result = handle_listener_event(event, web_client, state)
        print(json.dumps(result, ensure_ascii=False), flush=True)


def main() -> int:
    if not SLACK_APP_TOKEN:
        print(json.dumps({"status": "error", "error": "SLACK_APP_TOKEN missing"}), file=sys.stderr)
        return 1
    if SLACK_APP_TOKEN == "xapp-your-token-here":
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "SLACK_APP_TOKEN is still the .env.example placeholder",
                    "hint": "api.slack.com/apps → Socket Mode → app-level token (connections:write)",
                }
            ),
            file=sys.stderr,
        )
        return 1
    if not SLACK_BOT_TOKEN:
        print(json.dumps({"status": "error", "error": "SLACK_BOT_TOKEN missing"}), file=sys.stderr)
        return 1

    web_client = WebClient(token=SLACK_BOT_TOKEN)
    state = _build_state(web_client)

    channels = _channels_for_log(state)
    log_event("listener_started", bot_user_id=state.bot_user_id, channels=channels)
    print(
        json.dumps({
            "status": "listening",
            "bot_user_id": state.bot_user_id,
            "channels": channels,
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
