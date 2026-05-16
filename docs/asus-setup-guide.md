# ASUS Machine Setup Guide

Partner-facing guide for configuring the ASUS deployment machine.

## Machine Details

- **Host:** `asus@100.68.221.47` (Tailscale IP)
- **Project path:** `~/memory-claw`
- **Python managed by:** `uv` (at `~/.local/bin/uv`)

## Step 1: SSH In

```bash
ssh asus@100.68.221.47
cd ~/memory-claw
```

## Step 2: Pull Latest Code

```bash
git fetch origin main
git checkout main
git pull
```

## Step 3: Install Dependencies

```bash
~/.local/bin/uv sync
```

## Step 4: Create `.env`

```bash
cat > .env << 'EOF'
OLLAMA_BASE_URL=http://127.0.0.1:11434
SLACK_BOT_TOKEN=xoxb-REPLACE-WITH-REAL-TOKEN
SLACK_CHANNEL=#institutional-memory
SLACK_WEBHOOK_URL=
SLACK_APP_TOKEN=xapp-REPLACE-WITH-REAL-TOKEN
EOF
chmod 600 .env
```

### Where to get the tokens

| Token | Where | Steps |
|-------|-------|-------|
| `SLACK_BOT_TOKEN` | [api.slack.com/apps](https://api.slack.com/apps) → Your App → **OAuth & Permissions** → Bot User OAuth Token | Starts with `xoxb-`. Needs scopes: `chat:write`, `channels:history`, `channels:read` |
| `SLACK_APP_TOKEN` | [api.slack.com/apps](https://api.slack.com/apps) → Your App → **Basic Information** → App-Level Tokens → Generate Token | Starts with `xapp-`. Needs scope: `connections:write` (for Socket Mode) |
| `SLACK_CHANNEL` | Name of the Slack channel the bot posts to | e.g. `#institutional-memory`. Bot must be invited to this channel |

### If no Slack app exists yet

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Name it (e.g. "Institutional Memory") and pick the workspace
3. **Socket Mode** → Enable Socket Mode → generate app-level token with `connections:write` → that's your `SLACK_APP_TOKEN`
4. **OAuth & Permissions** → add bot scopes: `chat:write`, `channels:history`, `channels:read`
5. **Event Subscriptions** → Enable Events → Subscribe to bot events: `message.channels`
6. **Install to Workspace** → copy the Bot User OAuth Token → that's your `SLACK_BOT_TOKEN`
7. Invite the bot to the channel: `/invite @Institutional Memory` in Slack

## Step 5: Verify Ollama Is Running

```bash
curl -s http://127.0.0.1:11434/api/tags | head -c 200
```

Should return JSON with available models. If Ollama isn't running:

```bash
ollama serve &
ollama pull qwen3-embedding:8b
```

## Step 6: Run Readiness Check

```bash
~/.local/bin/uv run python scripts/dgx_check.py --skip-backup-video
```

Expected output: `{"ok": true, "blockers": []}`

If blockers appear, fix them before proceeding.

## Step 7: Run Full Test Suite

```bash
~/.local/bin/uv run pytest -q
```

All tests should pass.

## Step 8: Test Slack Posting (Optional)

```bash
./bin/imem send-slack --message "Hello from Institutional Memory"
```

Check the Slack channel for the message.

## Step 9: Start the Slack Listener (Optional)

Only needed if live Slack ingestion is desired:

```bash
~/.local/bin/uv run python scripts/slack_listener.py
```

Requires both `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` to be set. The listener stays running and ingests new messages into `company/inbox/slack/`.

## Important Warnings

- **Do NOT run `git clean -fd`** — it deletes `.env` and other untracked config
- **Do NOT save code changes on ASUS** — edits happen on the dev machine, ASUS is for testing/running only
- After testing, restore tracked files with: `git checkout -- .`
- The `.env` file is gitignored — it won't survive `git clean` but is safe from `git checkout`
