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
    LISTENER_CHANNELS,
    PROMOTION_ALLOWED_CHANNELS,
    SLACK_APP_TOKEN,
    SLACK_BOT_TOKEN,
    SLACK_CHANNEL,
)
from institutional_memory.listener import (
    DedupeSet,
    ListenerState,
    handle_listener_event,
    resolve_channels,
)
from institutional_memory.slack_ingest import handle_message_event
from institutional_memory.slack_promotion import PromotionRateLimiter


def _build_state(web_client: WebClient) -> ListenerState:
    auth = web_client.auth_test()
    bot_user_id = auth["user_id"]

    allowed_channels = resolve_channels(
        LISTENER_CHANNELS, fallback_channel=SLACK_CHANNEL, client=web_client
    )
    promotion_allowed_channels = resolve_channels(
        PROMOTION_ALLOWED_CHANNELS, fallback_channel="", client=web_client
    )

    return ListenerState(
        bot_user_id=bot_user_id,
        allowed_channels=allowed_channels,
        dedupe=DedupeSet(),
        promotion_allowed_channels=promotion_allowed_channels,
        promotion_rate_limiter=PromotionRateLimiter(),
    )


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

    log_event(
        "listener_started",
        bot_user_id=state.bot_user_id,
        channels=sorted(state.allowed_channels),
        promotion_channels=sorted(state.promotion_allowed_channels),
    )
    print(
        json.dumps({
            "status": "listening",
            "bot_user_id": state.bot_user_id,
            "channels": sorted(state.allowed_channels),
            "promotion_channels": sorted(state.promotion_allowed_channels),
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
