#!/usr/bin/env python3
"""Report whether the Slack Socket Mode listener is running."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from institutional_memory.config import AUDIT_LOG

# Match the Python worker only (not the `uv run` parent process).
LISTENER_MATCH = "python3 scripts/slack_listener.py"


def _listener_pids() -> list[int]:
    try:
        result = subprocess.run(
            ["pgrep", "-f", LISTENER_MATCH],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    pids: list[int] = []
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if not line.isdigit():
            continue
        pid = int(line)
        if pid == 0:
            continue
        pids.append(pid)
    return sorted(set(pids))


def _audit_listener_state() -> dict[str, object]:
    last_started: dict[str, object] | None = None
    last_stopped: dict[str, object] | None = None
    if not AUDIT_LOG.is_file():
        return {
            "last_started": None,
            "last_stopped": None,
            "audit_suggests_running": False,
        }
    for line in reversed(AUDIT_LOG.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = entry.get("type")
        if event_type == "listener_started" and last_started is None:
            last_started = entry
        elif event_type == "listener_stopped" and last_stopped is None:
            last_stopped = entry
        if last_started is not None and last_stopped is not None:
            break
    audit_suggests_running = False
    if last_started is not None:
        if last_stopped is None:
            audit_suggests_running = True
        else:
            audit_suggests_running = str(last_started.get("ts", "")) > str(
                last_stopped.get("ts", "")
            )
    return {
        "last_started": last_started,
        "last_stopped": last_stopped,
        "audit_suggests_running": audit_suggests_running,
    }


def status() -> dict[str, object]:
    pids = _listener_pids()
    audit = _audit_listener_state()
    listening = len(pids) > 0
    last_started = audit.get("last_started")
    channels: list[str] = []
    bot_user_id: str | None = None
    if isinstance(last_started, dict):
        raw_channels = last_started.get("channels")
        if isinstance(raw_channels, list):
            channels = [str(c) for c in raw_channels]
        bot_user_id = last_started.get("bot_user_id")
    return {
        "listening": listening,
        "pid": pids[0] if len(pids) == 1 else None,
        "pids": pids,
        "multiple_instances": len(pids) > 1,
        "bot_user_id": bot_user_id,
        "channels": channels,
        "last_started": last_started.get("ts") if isinstance(last_started, dict) else None,
        "last_stopped": (
            audit.get("last_stopped", {}).get("ts")
            if isinstance(audit.get("last_stopped"), dict)
            else None
        ),
        "audit_suggests_running": audit.get("audit_suggests_running"),
    }


def main() -> int:
    payload = status()
    print(json.dumps(payload, indent=2))
    if payload.get("multiple_instances"):
        print(
            "warning: multiple listener processes — stop extras (tmux/systemd) before testing",
            file=sys.stderr,
        )
        return 1
    return 0 if payload.get("listening") else 1


if __name__ == "__main__":
    raise SystemExit(main())
