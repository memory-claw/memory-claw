# Slack Answer Loop — Design Spec (v2)

## Overview

Add real-time memory search and reply to the existing Socket Mode listener. When messages arrive in authorized channels, the bot searches institutional memory and replies in-thread when relevant context is found.

**Approach:** Extend existing `scripts/slack_listener.py` (raw `slack_sdk.socket_mode.SocketModeClient`). No new framework dependencies.

**Scope:** Hackathon demo. All channels are controlled. No multi-tenant or ACL concerns.

## Required Slack Scopes & Events

**Bot Token scopes:**
- `app_mentions:read` — receive @ mention events
- `channels:history` — read public channel messages
- `groups:history` — read private channel messages (if needed)
- `chat:write` — post replies
- `channels:read` — resolve channel names to IDs at startup

**App-level token:**
- `connections:write` — Socket Mode

**Event subscriptions:**
- `message.channels` (public)
- `message.groups` (private, if needed)
- `app_mention`

## Architecture

```
Slack WebSocket (Socket Mode via slack_sdk.socket_mode)
    │
    ▼
scripts/slack_listener.py (entry point)
    │
    ▼
institutional_memory/listener.py (core logic)
    │
    ├── Ack immediately (SocketModeResponse) before any processing
    │
    ├── Filter:
    │   ├── Skip bot messages (bot_id OR user == BOT_USER_ID)
    │   ├── Skip all message subtypes (message_changed, deleted, join, etc.)
    │   ├── Skip messages < 5 chars
    │   ├── Dedupe: skip if (channel, ts) already in LRU set
    │   └── Channel allowlist: unprompted replies only in LISTENER_CHANNELS
    │
    ├── Determine threshold:
    │   ├── @ mention (any channel) → 0.60
    │   ├── Active thread (bot already replied) → 0.65
    │   └── Unprompted (allowed channel, no mention) → 0.80
    │
    ├── Build search query:
    │   ├── Top-level → raw message text (strip <@BOT_ID> token)
    │   └── In thread → message text + human-only thread context (cap 2000 chars)
    │
    ├── search_memory(query, threshold=X)
    │
    ├── If hits found → format reply → post as thread reply to event["channel"]
    │   ├── Add (channel, thread_ts) to active threads set
    │   └── Audit log: listener_reply
    │
    ├── If mention but no hits → reply "I didn't find anything relevant"
    │
    └── If unprompted and no hits → silence
        └── Audit log: listener_skip
```

## Files

**New:**
- `institutional_memory/listener.py` — core logic: event filtering, threshold selection, query building, reply formatting, thread/dedupe tracking

**Modified:**
- `scripts/slack_listener.py` — extend to import and call listener.py logic (remains the canonical entry point)
- `institutional_memory/config.py` — add threshold and channel config
- `.env.example` — add new env vars

**Reused as-is:**
- `search_memory()` from `search.py`
- `log_event()` from `audit.py`
- `SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN` from `config.py`

**Not modified:**
- `pyproject.toml` — no new dependencies (slack_sdk already installed)
- `cli.py` — no `imem listen` subcommand (listener runs outside OpenClaw surface)

## Event Handling

| Event type | Action |
|---|---|
| `message` (no subtype, human) | Process if in allowed channel or active thread |
| `message` with `bot_id` or `user == BOT_USER_ID` | Skip |
| `message` with any subtype | Skip |
| `app_mention` | Process — always, any channel |
| Message < 5 chars | Skip |
| Duplicate `(channel, ts)` | Skip |

### Listener-Specific Event Filter

`should_ignore_event()` from `slack_ingest.py` is insufficient — it only checks `bot_id` and `bot_message` subtype. The listener needs a stricter filter in `listener.py`:

```python
def should_skip(event: dict, bot_user_id: str) -> bool:
    if event.get("bot_id"):
        return True
    if event.get("user") == bot_user_id:
        return True
    if event.get("subtype"):
        return True
    if len(str(event.get("text", "")).strip()) < 5:
        return True
    return False
```

### @ Mention Detection

- `app_mention` event → process at 0.60 threshold, any channel
- `message` event containing `<@BOT_USER_ID>` in text → same treatment
- Deduplicate: LRU set keyed by `(channel, ts)`. If already processed via `app_mention`, skip duplicate `message` event.

### Mention Reply Guarantee

@ mention guarantees *processing*. If hits found → reply with context. If no hits → reply "I didn't find anything relevant in institutional memory." Unprompted messages with no hits → silence.

### Channel Allowlist

```python
LISTENER_CHANNELS = os.getenv("LISTENER_CHANNELS", "")  # comma-separated, names or IDs
```

- If empty, defaults to `SLACK_CHANNEL` value
- At startup, resolve any `#channel-name` entries to channel IDs via `conversations.list`
- All runtime comparisons use channel IDs only
- Unprompted replies restricted to allowlisted channels
- @ mentions and active thread follow-ups work in any channel the bot can see

### Deduplication

Bounded LRU set keyed by `(channel, ts)`, max 200 entries, 60s TTL. Covers:
- Slack retries
- `app_mention` + `message` dual events for same message
- Out-of-order delivery

### Thread Tracking

In-memory `dict` keyed by `(channel, thread_ts)` storing the set of threads the bot has replied in. If incoming message's `(channel, thread_ts)` is tracked, use thread threshold (0.65) — even if channel is not in `LISTENER_CHANNELS` (bot was invited to the thread via mention).

Resets on restart — acceptable for hackathon.

### Thread Context Building

When message has `thread_ts`:
- Fetch replies via `conversations.replies` (limit 10)
- Filter out bot messages (by `bot_id` or `user == BOT_USER_ID`)
- Strip `<@BOT_USER_ID>` tokens from text
- Concatenate human messages as context prefix
- Cap total context at 2000 chars
- Append current message text as the search query

### Ack-First Pattern

Existing `scripts/slack_listener.py` already acks via `SocketModeResponse` before processing. This pattern must be preserved. All search/reply logic runs after ack. Prevents Slack retries under Ollama latency.

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

No-hit mention reply:
```
🔍 I didn't find anything relevant in institutional memory.
```

**Rules:**
- Max 3 sources per reply
- Snippet truncated to ~150 chars
- Score shown as percentage
- Source path for transparency
- Reply always to `event["channel"]` (channel ID from the event), never routed through `SLACK_CHANNEL` config

## Channel-Level vs Thread Posts

| Trigger | Where it posts |
|---|---|
| Listener responds to a message | Thread reply under their message |
| OpenClaw processes draft via `send-slack` | Top-level channel message (existing behavior, unchanged) |

## Audit Logging

Uses existing `log_event()`. Field is `"type"` (matching existing audit schema):

```json
{"type": "listener_reply", "channel": "C123", "thread_ts": "...", "query": "...", "top_score": 0.87, "sources": ["company/corpus/q3_strategy.md"], "triggered_by": "mention|unprompted|thread"}
{"type": "listener_skip", "channel": "C123", "reason": "below_threshold", "top_score": 0.42}
{"type": "listener_skip", "channel": "C123", "reason": "not_in_allowlist"}
```

## Entry Point

```bash
uv run python scripts/slack_listener.py
```

### Startup:
1. Validate `SLACK_APP_TOKEN` and `SLACK_BOT_TOKEN` present (exit with JSON error to stderr)
2. Fetch bot's own user ID via `auth.test`
3. Resolve `LISTENER_CHANNELS` names → channel IDs
4. Connect Socket Mode
5. Log `{"type": "listener_started"}` to audit log
6. Print `{"status": "listening", "channels": [...], "bot_user_id": "U..."}` to stdout (JSONL, not human-readable)

### Shutdown:
- SIGINT/SIGTERM → disconnect cleanly, log `{"type": "listener_stopped"}` to audit

### Deployment (hackathon):
```bash
ssh asus@100.68.221.47
tmux new -s listener
uv run python scripts/slack_listener.py
```

## Config Additions

```python
UNPROMPTED_THRESHOLD = float(os.getenv("UNPROMPTED_THRESHOLD", "0.80"))
THREAD_THRESHOLD = float(os.getenv("THREAD_THRESHOLD", "0.65"))
LISTENER_CHANNELS = os.getenv("LISTENER_CHANNELS", "")  # comma-separated names or IDs; empty = SLACK_CHANNEL
```

## Error Handling

- `conversations.replies` fails → search with message text only (no thread context), log warning
- `chat.postMessage` fails → log `SlackApiError`, do not crash
- `search_memory` fails → log error, do not reply, do not crash
- `conversations.list` fails at startup (channel name resolution) → exit with clear error
- All errors logged via `log_event()` with error details

## Testing

### Unit tests (`tests/test_listener.py`):
- `should_skip`: bot messages, subtypes, short messages, own user ID
- Threshold selection: mention vs active thread vs unprompted
- Channel allowlist: ID normalization, name-to-ID resolution, enforcement
- Query building: top-level vs thread, bot message filtering, mention stripping, char cap
- Reply formatting: single hit, multiple hits, truncation, no-hit mention reply
- Dedupe: LRU set behavior, (channel, ts) keying, TTL expiry
- Active thread tracking: keyed by (channel, thread_ts), threshold lowering, cross-channel via mention

### Mocking:
- `search_memory` — controlled hits/misses
- `WebClient` — mock Slack API calls (conversations.replies, chat.postMessage, auth.test, conversations.list)

### Integration (needs tokens, ASUS box):
- Send message in allowed channel → verify bot replies in thread
- Send @ mention in non-allowed channel → verify bot replies
- Follow up in bot's thread → verify lower threshold applies
- Manual or scripted via slack-sdk

### Developing without tokens:
All logic in `listener.py` is testable without credentials. Only Socket Mode connection in `scripts/slack_listener.py` requires real tokens.
