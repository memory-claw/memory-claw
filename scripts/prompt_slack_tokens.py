#!/usr/bin/env python3
"""Interactive helper: paste Slack tokens into .env after creating the app in api.slack.com."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

CHECKLIST = """
=== Slack new-app checklist (browser) ===
1. api.slack.com/apps → Create New App → From scratch
2. Socket Mode ON → app-level token (connections:write) → xapp-...
3. OAuth & Permissions → scopes: chat:write, channels:history, channels:read, app_mentions:read
4. Install to Workspace → copy Bot User OAuth Token → xoxb-...
5. Event Subscriptions ON → message.channels, app_mention
6. In Slack: /invite @YourBot in #institutional-memory
==========================================
"""


def _read_env() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    data: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def _write_env(updates: dict[str, str]) -> None:
    lines: list[str] = []
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or "=" not in line:
                lines.append(line)
                continue
            key = line.split("=", 1)[0]
            if key in updates:
                lines.append(f"{key}={updates[key]}")
                del updates[key]
            else:
                lines.append(line)
    else:
        lines = []
    for key, value in updates.items():
        lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ENV_PATH.chmod(0o600)


def _prompt_token(name: str, pattern: re.Pattern[str], current: str) -> str | None:
    hint = f"(current: set, Enter to keep)" if current and "your-token" not in current and "REPLACE" not in current else "(required)"
    raw = input(f"{name} {hint}: ").strip()
    if not raw:
        return None
    if not pattern.match(raw):
        print(f"Invalid {name} format.", file=sys.stderr)
        return None
    return raw


def main() -> int:
    print(CHECKLIST)
    env = _read_env()
    updates: dict[str, str] = {}

    xapp = _prompt_token("SLACK_APP_TOKEN", re.compile(r"^xapp-.+"), env.get("SLACK_APP_TOKEN", ""))
    if xapp:
        updates["SLACK_APP_TOKEN"] = xapp

    xoxb = _prompt_token("SLACK_BOT_TOKEN", re.compile(r"^xoxb-.+"), env.get("SLACK_BOT_TOKEN", ""))
    if xoxb:
        updates["SLACK_BOT_TOKEN"] = xoxb

    if not updates:
        print("No changes written.")
        return 1

    _write_env(updates)
    print(f"Updated {ENV_PATH}")
    print("Next: uv run python scripts/slack_setup_verify.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
