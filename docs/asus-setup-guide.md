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
| `SLACK_BOT_TOKEN` | [api.slack.com/apps](https://api.slack.com/apps) → Your App → **OAuth & Permissions** → Bot User OAuth Token | Starts with `xoxb-`. Needs scopes: `chat:write`, `channels:history`, `channels:read`, `app_mentions:read` |
| `SLACK_APP_TOKEN` | [api.slack.com/apps](https://api.slack.com/apps) → Your App → **Basic Information** → App-Level Tokens → Generate Token | Starts with `xapp-`. Needs scope: `connections:write` (for Socket Mode) |
| `SLACK_CHANNEL` | Name of the Slack channel the bot posts to | e.g. `#institutional-memory`. Bot must be invited to this channel |

### New app from scratch (interactive token paste on ASUS)

After completing the browser steps below, on ASUS run:

```bash
cd ~/memory-claw
~/.local/bin/uv run python scripts/prompt_slack_tokens.py
~/.local/bin/uv run python scripts/slack_setup_verify.py
```

### If no Slack app exists yet

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Name it (e.g. "Institutional Memory") and pick the workspace
3. **Socket Mode** → Enable Socket Mode → generate app-level token with `connections:write` → that's your `SLACK_APP_TOKEN`
4. **OAuth & Permissions** → add bot scopes: `chat:write`, `channels:history`, `channels:read` (private channels: also `groups:history`, `groups:read`)
5. **Event Subscriptions** → Enable Events → Subscribe to bot events: `message.channels`, `app_mention` (private: `message.groups`)
6. **Install to Workspace** → copy the Bot User OAuth Token → that's your `SLACK_BOT_TOKEN`
7. Invite the bot to the channel: `/invite @Institutional Memory` in Slack

### Recommended demo `.env` (listener + OpenClaw)

See [`.env.example`](../.env.example). For autonomous Slack in any channel the bot is invited to:

```text
LISTENER_CHANNELS=*
UNPROMPTED_THRESHOLD=0.65
THREAD_THRESHOLD=0.65
```

`UNPROMPTED_THRESHOLD` defaults to `0.80` in code when unset; lower it for demos so on-topic messages match mock corpus more often.

Optional per-channel overrides: `LISTENER_CHANNEL_THRESHOLDS=#general:0.85` (stricter in noisy channels).

Optional faster inbox processing after live Slack ingest: `OPENCLAW_WAKE_CMD` (shell command; empty = heartbeat-only).

## Two systems: who intervenes when

| Component | Role | Runs on its own? | Slack behavior |
|-----------|------|------------------|----------------|
| `scripts/slack_listener.py` | Socket Mode: ingest + answer loop | Yes, if `SLACK_APP_TOKEN` + process running | @mention in **any** channel; unprompted only per `LISTENER_CHANNELS` (`*` = all invited channels) |
| OpenClaw + `HEARTBEAT.md` | Every 1–2 min: `list-new-drafts` → SOUL workflow | Yes, if gateway + heartbeat enabled | Posts via `send-slack`; uses draft `slack_channel_id` / `slack_thread_ts` when present |

```text
Slack message → listener (search + in-thread reply in same channel)
              → company/inbox/slack/*.md → OpenClaw heartbeat (SOUL message in thread or SLACK_CHANNEL)
```

**Autonomous intervention checklist**

1. `uv run python scripts/slack_listener_status.py` → listening
2. `systemctl --user status memory-claw-slack-listener` (or `./scripts/start_slack_listener.sh`)
3. OpenClaw gateway running; `HEARTBEAT.md` in `~/.openclaw/workspace/`
4. `uv run python scripts/ingest_corpus.py --force`
5. Bot invited in target channels (`/invite @YourBot`)
6. Tune skips: `tail -f audit_log.jsonl | grep listener_skip`
7. Restart listener after `.env` changes

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

## Step 8b: Ingest Corpus (Required for Search Replies)

```bash
~/.local/bin/uv run python scripts/ingest_corpus.py --force
```

Without this, the listener and OpenClaw search return no hits.

## Step 9: Start the Slack Listener (required for @mentions)

`./bin/imem send-slack` posts messages **without** the listener. **@mentions only work** while `scripts/slack_listener.py` is running (Socket Mode + `SLACK_APP_TOKEN`).

Check status anytime:

```bash
~/.local/bin/uv run python scripts/slack_listener_status.py
```

Exit code `0` = listener process running; `1` = not running.

### Option A — systemd user service (recommended)

Stop any tmux/foreground listener first (only one instance).

```bash
pkill -f 'python3 scripts/slack_listener.py' || true
tmux kill-session -t slack 2>/dev/null || true

mkdir -p ~/.config/systemd/user
cp deploy/systemd/memory-claw-slack-listener.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now memory-claw-slack-listener.service
loginctl enable-linger "$USER"   # keeps service up after logout
systemctl --user status memory-claw-slack-listener.service
```

Logs: `journalctl --user -u memory-claw-slack-listener.service -f`

Restart after `.env` changes: `systemctl --user restart memory-claw-slack-listener.service`

### Option B — helper script (background, no systemd)

```bash
./scripts/start_slack_listener.sh
```

### Option C — tmux (manual)

```bash
tmux new -s slack
cd ~/memory-claw
~/.local/bin/uv run python scripts/slack_listener.py
# Detach: Ctrl+b then d  (do NOT Ctrl+C — that stops @mention replies)
```

The listener ingests messages into `company/inbox/slack/` and runs the answer loop (search + in-thread replies on @mention).

Verify Slack tokens:

```bash
~/.local/bin/uv run python scripts/dgx_check.py --skip-backup-video --check-slack-ingestion
~/.local/bin/uv run python scripts/slack_setup_verify.py
```

## Step 10: Manual Slack tests (mock corpus)

Channel: **`#institutional-memory`**. Use a real @mention (pick **@Memory Claw** from autocomplete — blue highlight).

| ID | What to post | Pass |
|----|----------------|------|
| G1 | @Memory Claw … Vantara deal, loop engineering after signed, 8 weeks | Thread reply; sources under `company/corpus/mock_data/...` (Helix/Vantara) |
| G2 | @Memory Claw … add rate limiting after launch | Rate limit / export outage docs |
| G3 | @Memory Claw … send them our `.env` | Secrets / credentials incident |
| G4 | @Memory Claw random xyz123 | “didn't find anything relevant” |
| N1 | Dark mode opinion (**no** @bot) | **No** reply (off-topic); with `LISTENER_CHANNELS=*` and low threshold, on-topic unprompted text **may** reply |

CLI preflight:

```bash
./bin/imem search-memory --query "Vantara enterprise deal loop in engineering"
~/.local/bin/uv run python scripts/slack_listener_status.py
~/.local/bin/uv run python scripts/golden_listener_simulate.py   # handler dry-run (no Slack post)
tail -5 audit_log.jsonl   # expect listener_reply after each @mention test
```

Demo lines: see `company/corpus/mock_data/README.md`.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|--------|-----|
| `send-slack` works, @mention silent | Listener not running | `systemctl --user start memory-claw-slack-listener` or `./scripts/start_slack_listener.sh` |
| Listener was running, then stopped | Ctrl+C in tmux/terminal | Use systemd or tmux detach (`Ctrl+b` `d`) |
| `slack_listener_status` shows multiple PIDs | Duplicate listeners | `pkill -f 'python3 scripts/slack_listener.py'`; start one via systemd |
| No events at all | Missing `app_mention` bot event | Slack app → Event Subscriptions → add `app_mention`, `message.channels`, reinstall |
| “didn't find anything” on good questions | Stale index | `uv run python scripts/ingest_corpus.py --force` |
| No unprompted reply in other channels | Channel not allowlisted (before `*`) or bot not invited | Set `LISTENER_CHANNELS=*` or add channel names; `/invite @bot` |
| `listener_skip` `not_in_allowlist` | Unprompted outside allowlist | Use `LISTENER_CHANNELS=*` or @mention |
| `listener_skip` `below_threshold` | Corpus match too weak | Lower `UNPROMPTED_THRESHOLD`; post on-topic text; re-ingest corpus |
| OpenClaw posts only to `#institutional-memory` | Non-Slack draft or missing metadata | Slack inbox files include `**Channel:**` / `**Thread TS:**`; SOUL uses `--channel` / `--thread-ts` |
| Inbox file but no SOUL post for 1–2 min | Heartbeat off or gateway down | Start gateway; copy `HEARTBEAT.md`; optional `OPENCLAW_WAKE_CMD` |

## Important Warnings

- **Do NOT run `git clean -fd`** — it deletes `.env` and other untracked config
- **Do NOT save code changes on ASUS** — edits happen on the dev machine, ASUS is for testing/running only
- After testing, restore tracked files with: `git checkout -- .`
- The `.env` file is gitignored — it won't survive `git clean` but is safe from `git checkout`
