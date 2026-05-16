#!/bin/sh
set -eu

ASUS_USER_HOST="${ASUS_USER_HOST:-asus@100.68.221.47}"
ASUS_TAILSCALE_IP="${ASUS_TAILSCALE_IP:-100.68.221.47}"
ASUS_REPO="${ASUS_REPO:-~/memory-claw}"
ASUS_SSH_KEY="${ASUS_SSH_KEY:-$HOME/.ssh/asus_deploy}"
ASUS_BRANCH="${ASUS_BRANCH:-codex/institutional-memory-engine}"
OPENCLAW_WORKSPACE="${OPENCLAW_WORKSPACE:-\$HOME/.openclaw/workspace}"

if command -v tailscale >/dev/null 2>&1; then
  echo "Tailscale status before ASUS deploy:"
  tailscale status || true
  if ! tailscale ping --timeout=5s "$ASUS_TAILSCALE_IP"; then
    echo "Tailscale cannot see ASUS peer $ASUS_TAILSCALE_IP. Check OAuth client tailnet, tag:ci, and ACL grants."
    tailscale netcheck || true
    exit 1
  fi
fi

ssh -i "$ASUS_SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$ASUS_USER_HOST" \
  "set -eu; cd $ASUS_REPO; git fetch origin \"$ASUS_BRANCH\"; git checkout -B \"$ASUS_BRANCH\" \"origin/$ASUS_BRANCH\"; OPENCLAW_WORKSPACE=$OPENCLAW_WORKSPACE; mkdir -p \"\$OPENCLAW_WORKSPACE/skills/institutional-memory\"; cp SOUL.md \"\$OPENCLAW_WORKSPACE/SOUL.md\"; cp HEARTBEAT.md \"\$OPENCLAW_WORKSPACE/HEARTBEAT.md\"; cp skills/institutional-memory/SKILL.md \"\$OPENCLAW_WORKSPACE/skills/institutional-memory/SKILL.md\"; uv sync; uv run python scripts/dgx_check.py --skip-model-smoke --skip-backup-video"
