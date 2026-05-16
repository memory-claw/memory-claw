#!/bin/sh
set -eu

ASUS_USER_HOST="${ASUS_USER_HOST:-asus@100.68.221.47}"
ASUS_TAILSCALE_IP="${ASUS_TAILSCALE_IP:-100.68.221.47}"
ASUS_REPO="${ASUS_REPO:-~/memory-claw}"
ASUS_SSH_KEY="${ASUS_SSH_KEY:-$HOME/.ssh/asus_deploy}"
ASUS_BRANCH="${ASUS_BRANCH:-codex/institutional-memory-engine}"
OPENCLAW_WORKSPACE="${OPENCLAW_WORKSPACE:-\$HOME/.openclaw/workspace}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
REMOTE_ENV_FILE=""

cleanup() {
  if [ -n "$REMOTE_ENV_FILE" ]; then
    rm -f "$REMOTE_ENV_FILE"
  fi
}
trap cleanup EXIT INT TERM

if command -v tailscale >/dev/null 2>&1; then
  echo "Tailscale status before ASUS deploy:"
  tailscale status || true
  if ! tailscale ping --timeout=5s "$ASUS_TAILSCALE_IP"; then
    echo "Tailscale cannot see ASUS peer $ASUS_TAILSCALE_IP. Check OAuth client tailnet, tag:ci, and ACL grants."
    tailscale netcheck || true
    exit 1
  fi
fi

if [ -n "${SLACK_BOT_TOKEN:-}" ] || [ -n "${SLACK_CHANNEL:-}" ] || [ -n "$SLACK_WEBHOOK_URL" ]; then
  if [ -z "${SLACK_BOT_TOKEN:-}" ] || [ -z "${SLACK_CHANNEL:-}" ]; then
    echo "SLACK_BOT_TOKEN and SLACK_CHANNEL must both be set to deploy ASUS .env."
    exit 1
  fi
  REMOTE_ENV_FILE="$(mktemp)"
  {
    printf 'OLLAMA_BASE_URL=%s\n' "$OLLAMA_BASE_URL"
    printf 'SLACK_BOT_TOKEN=%s\n' "$SLACK_BOT_TOKEN"
    printf 'SLACK_CHANNEL=%s\n' "$SLACK_CHANNEL"
    printf 'SLACK_WEBHOOK_URL=%s\n' "$SLACK_WEBHOOK_URL"
    printf 'SLACK_APP_TOKEN=%s\n' "${SLACK_APP_TOKEN:-}"
  } >"$REMOTE_ENV_FILE"
  ssh -i "$ASUS_SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$ASUS_USER_HOST" \
    "set -eu; PATH=\$HOME/.local/bin:\$PATH; cd $ASUS_REPO; umask 077; cat > .env" <"$REMOTE_ENV_FILE"
fi

ssh -i "$ASUS_SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$ASUS_USER_HOST" \
  "set -eu; PATH=\$HOME/.local/bin:\$PATH; cd $ASUS_REPO; git fetch origin \"$ASUS_BRANCH\"; git checkout -B \"$ASUS_BRANCH\" \"origin/$ASUS_BRANCH\"; OPENCLAW_WORKSPACE=$OPENCLAW_WORKSPACE; mkdir -p \"\$OPENCLAW_WORKSPACE/skills/institutional-memory\"; cp SOUL.md \"\$OPENCLAW_WORKSPACE/SOUL.md\"; cp HEARTBEAT.md \"\$OPENCLAW_WORKSPACE/HEARTBEAT.md\"; cp skills/institutional-memory/SKILL.md \"\$OPENCLAW_WORKSPACE/skills/institutional-memory/SKILL.md\"; uv sync; uv run python scripts/dgx_check.py --skip-model-smoke --skip-backup-video"
