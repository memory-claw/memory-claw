#!/bin/sh
set -eu

ASUS_USER_HOST="${ASUS_USER_HOST:-asus@100.68.221.47}"
ASUS_TAILSCALE_IP="${ASUS_TAILSCALE_IP:-100.68.221.47}"
ASUS_REPO="${ASUS_REPO:-~/memory-claw}"
ASUS_SSH_KEY="${ASUS_SSH_KEY:-$HOME/.ssh/asus_deploy}"
ASUS_BRANCH="${ASUS_BRANCH:-codex/institutional-memory-engine}"

if command -v tailscale >/dev/null 2>&1; then
  tailscale ping --timeout=5s "$ASUS_TAILSCALE_IP" >/dev/null
fi

ssh -i "$ASUS_SSH_KEY" "$ASUS_USER_HOST" \
  "set -eu; cd $ASUS_REPO; git fetch origin \"$ASUS_BRANCH\"; git checkout -B \"$ASUS_BRANCH\" \"origin/$ASUS_BRANCH\"; uv sync; uv run python scripts/dgx_check.py --skip-model-smoke --skip-backup-video"
