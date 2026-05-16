# Slack Answer Loop — Design Spec

## Overview

Add a real-time Slack listener that watches the entire workspace, searches institutional memory when messages arrive, and replies in-thread when relevant context is found.

**Approach:** slack-bolt Socket Mode app (Approach 1).

## Architecture

```
Slack WebSocket (Socket Mode)
    │
    ▼
slack-bolt App (listener.py)
    │
    ├── Filter: skip bot messages, skip message_changed/deleted subtypes
    │
    ├── Determine context:
    │   ├── Is @ mention? → threshold = 0.60
    │   ├── In bot's active thread? → threshold = 0.65
    │   └── Top-level, no mention? → threshold = 0.80
    │
    ├── Build search query:
    │   ├── Top-level → raw message text
    │   └── In thread → message text + parent thread context (last 5-10 replies)
    │
    ├── search_memory(query, threshold=X)
    │
    ├── If hits found → format reply → post as thread reply
    │
    └── If no hits / below threshold → silence
```

## Files

**New:**
- `institutional_memory/listener.py` — bolt app, event handler, threshold logic, reply formatting
- `scripts/run_listener.py` — alternative entry point

**Modified:**
- `pyproject.toml` — add `slack-bolt>=1.18.0`
- `institutional_memory/config.py` — add `UNPROMPTED_THRESHOLD` (0.80), `THREAD_THRESHOLD` (0.65)
- `institutional_memory/cli.py` — add `listen` subcommand

**Reused as-is:**
- `search_memory()` from `search.py`
- `should_ignore_event()` from `slack_ingest.py`
- `log_event()` from `audit.py`
- `SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN` from `config.py`

## Event Handling

| Event type | Action |
|---|---|
| `message` (no subtype) | Process |
| `message` with `bot_id` or subtype `bot_message` | Skip |
| `message` subtypes (`message_changed`, `message_deleted`, `channel_join`, etc.) | Skip |
| `app_mention` | Process — guaranteed reply at normal threshold |

### @ Mention Detection

- `app_mention` event → process at 0.60 threshold
- `message` event containing `<@BOT_USER_ID>` in text → same treatment (deduplicate — if both events fire for same message, process only once)
- `message` event without mention → 0.80 (or 0.65 if active thread)

Deduplication: track last processed `(channel, ts)` pair. If already handled via `app_mention`, skip the duplicate `message` event.

### Thread Tracking

In-memory `set[str]` of `thread_ts` values the bot has replied to. After bot replies, add that `thread_ts`. If incoming message's `thread_ts` is in the set, use lower threshold (0.65).

Resets on restart — acceptable for hackathon.

### Thread Context Building

When message has `thread_ts`:
- Fetch parent + recent replies via `conversations.replies` (limit 10)
- Concatenate as context prefix to search query
- Enables follow-up questions like "what about Q4?" to be meaningful

### Bot Responds in Own Threads

If a user follows up in a thread the bot started, bot searches again and replies. `should_ignore_event` already filters bot's own messages to prevent loops.

## Reply Format

Single hit:
```
📎 Found relevant context (87% match):

> "Our retention strategy shifted to product-led growth in Q3, focusing on..."

— company/corpus/q3_strategy.md
```

Multiple hits (top 2-3):
```
📎 Found relevant context:

> "Our retention strategy shifted to product-led growth in Q3..."
— company/corpus/q3_strategy.md (87%)

> "PLG metrics showed 23% improvement in activation..."
— company/corpus/plg_results.md (74%)
```

**Rules:**
- Max 3 sources per reply
- Snippet truncated to ~150 chars
- Score shown as percentage
- Source path for transparency

## Channel-Level vs Thread Posts

| Trigger | Where it posts |
|---|---|
| Listener responds to a message | Thread reply under their message |
| OpenClaw processes draft via `send-slack` | Top-level channel message (existing behavior) |

## Audit Logging

Uses existing `log_event()`:

```json
{"event": "listener_reply", "channel": "C123", "thread_ts": "...", "query": "...", "top_score": 0.87, "sources": [...], "triggered_by": "mention|unprompted|thread"}
{"event": "listener_skip", "channel": "C123", "reason": "below_threshold", "top_score": 0.42}
```

## Entry Point

```bash
uv run imem listen
```

### Startup:
1. Validate `SLACK_APP_TOKEN` and `SLACK_BOT_TOKEN` present (exit with clear error if not)
2. Fetch bot's own user ID via `auth.test`
3. Connect Socket Mode
4. Log "listener started" to audit log
5. Print human-readable startup message to stdout

### Shutdown:
- SIGINT/SIGTERM → disconnect cleanly, log "listener stopped"

### Deployment (hackathon):
```bash
ssh asus@100.68.221.47
tmux new -s listener
uv run imem listen
```

## Dependencies

Add to `pyproject.toml`:
- `slack-bolt>=1.18.0`

## Config Additions

```python
UNPROMPTED_THRESHOLD = float(os.getenv("UNPROMPTED_THRESHOLD", "0.80"))
THREAD_THRESHOLD = float(os.getenv("THREAD_THRESHOLD", "0.65"))
```

## Testing

### Unit tests (`tests/test_listener.py`):
- Threshold selection: event attrs → correct threshold
- Query building: top-level vs thread with context
- Reply formatting: single hit, multiple hits, truncation
- Event filtering: skips bots/subtypes, processes normal messages
- Active thread tracking: set management, threshold lowering

### Mocking:
- `search_memory` — controlled hits
- `WebClient` — mock Slack API
- No Ollama/ChromaDB mocks needed (behind `search_memory`)

### Integration (needs tokens, ASUS box):
- Send test message → verify bot replies in thread
- Manual or scripted via slack-sdk

### Developing without tokens:
All logic testable without `SLACK_APP_TOKEN`. Only actual Socket Mode connection requires credentials.
