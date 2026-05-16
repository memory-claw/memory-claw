#!/usr/bin/env bash
# Start the Slack Socket Mode listener (idempotent).
# Preferred production setup: systemd user unit (see docs/asus-setup-guide.md).
# Alternative: tmux new -s slack, then run slack_listener.py and detach (Ctrl+b d).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
UV="${UV:-$HOME/.local/bin/uv}"
UNIT="memory-claw-slack-listener.service"

if "$UV" run python scripts/slack_listener_status.py >/dev/null 2>&1; then
  echo "Listener already running:"
  "$UV" run python scripts/slack_listener_status.py
  exit 0
fi

if systemctl --user is-enabled "$UNIT" >/dev/null 2>&1; then
  echo "Starting systemd user service: $UNIT"
  systemctl --user start "$UNIT"
  sleep 2
  exec "$UV" run python scripts/slack_listener_status.py
fi

echo "Starting listener in background (install systemd unit for auto-restart on reboot)."
nohup "$UV" run python scripts/slack_listener.py >>"${TMPDIR:-/tmp}/memory-claw-slack-listener.log" 2>&1 &
sleep 3
exec "$UV" run python scripts/slack_listener_status.py
