# Slack Ingestion Design

## Goal

Add Slack as an input source for the institutional memory engine while keeping
the current OpenClaw workflow intact.

The first version should support live Slack intake on the ASUS without requiring
a public URL, plus manual Slack import commands for demos, recovery, and
historical backfill.

## Core Decisions

- Use Slack Socket Mode for live events because the ASUS is private behind
  Tailscale and cannot receive public Slack Events API callbacks directly.
- Keep inbox and corpus roles explicit. New live Slack threads go to
  `inbox/slack/`; trusted historical memory goes to `corpus/slack/`.
- Do not automatically promote processed inbox threads into corpus in v1.
- Add manual commands for importing Slack into inbox, importing Slack into
  corpus, and promoting selected inbox files into corpus.
- Keep OpenClaw behavior unchanged: it checks inbox files, searches corpus, and
  posts a memory-backed Slack answer only when relevant memory exists.

## Non-Goals

- No public HTTPS webhook server in v1.
- No automatic classification of Slack messages as inbox versus corpus.
- No automatic corpus promotion after processing.
- No broad Slack workspace indexing.
- No production scheduler or daemon manager beyond a command that can be run by
  the ASUS webhook script, shell, tmux, launchd, or systemd later.

## Required Slack Configuration

Existing outbound posting uses:

```text
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL=#institutional-memory
```

Live Socket Mode intake also requires:

```text
SLACK_APP_TOKEN=xapp-...
```

The Slack app needs bot scopes for reading the target channel history and
posting replies. Use this initial permission set:

- Bot token scopes: `chat:write`, `channels:read`, `channels:history`
- Add if private channels are used: `groups:read`, `groups:history`
- App-level token scope for Socket Mode: `connections:write`
- Event subscriptions: `message.channels`; add `message.groups` if private
  channels are used

## Data Flow

Live event flow:

```text
Slack message or thread event
-> ./bin/imem slack-listen
-> inbox/slack/<channel>_<thread_ts>.md
-> OpenClaw checks inbox
-> OpenClaw searches corpus
-> OpenClaw posts memory-backed answer if useful
-> processed_drafts.json records outcome
```

Manual historical import flow:

```text
./bin/imem sync-slack --mode corpus --channel C123 --limit 100
-> corpus/slack/<channel>_<thread_ts>.md
-> uv run python scripts/ingest_corpus.py --force
```

Manual active import flow:

```text
./bin/imem sync-slack --mode inbox --channel C123 --limit 20
-> inbox/slack/<channel>_<thread_ts>.md
-> OpenClaw checks inbox
```

Manual promotion flow:

```text
./bin/imem promote-slack-thread --path inbox/slack/<file>.md
-> corpus/slack/<file>.md
-> uv run python scripts/ingest_corpus.py --force
```

## Commands

Add these CLI commands:

```bash
./bin/imem slack-listen
./bin/imem sync-slack --mode inbox --channel C123 --limit 20
./bin/imem sync-slack --mode corpus --channel C123 --limit 100
./bin/imem promote-slack-thread --path inbox/slack/C123_1710000000.000000.md
```

`slack-listen` runs until stopped. It receives live Slack events through Socket
Mode and writes or updates inbox files.

`sync-slack` fetches recent Slack history on demand. `--mode inbox` writes
active files under `inbox/slack/`. `--mode corpus` writes trusted memory under
`corpus/slack/`.

`promote-slack-thread` copies a selected processed inbox Slack file into
`corpus/slack/`. Copying is safer for auditability because the original inbox
artifact remains tied to `processed_drafts.json`. It should not ingest
automatically; the operator still runs `uv run python scripts/ingest_corpus.py
--force`.

## File Format

Slack-imported files should be markdown so humans can review them before
processing or promotion.

Each file should include stable metadata:

```markdown
# Slack Thread: <short preview>

**Channel:** C123
**Thread TS:** 1710000000.000000
**Imported At:** 2026-05-15T00:00:00+00:00
**Source:** Slack
**Permalink:** https://...

## Messages

- 2026-05-15T00:00:00+00:00 U123: message text
- 2026-05-15T00:01:00+00:00 U456: reply text
```

File names should be deterministic from channel and thread timestamp:

```text
inbox/slack/<channel>_<thread_ts>.md
corpus/slack/<channel>_<thread_ts>.md
```

Thread timestamp should use the parent thread timestamp when present, otherwise
the message timestamp. This keeps replies in one file.

## Idempotency And State

Slack sync should be safe to rerun.

- Re-importing the same thread rewrites the same deterministic file.
- Bot messages are ignored for intake to avoid loops.
- Deleted or inaccessible Slack messages are skipped with an audit event.
- Existing processed files remain protected by current processed-state behavior.
- `list-new-drafts` must be extended to find supported files under
  `inbox/slack/`, not only top-level inbox files.

## Error Handling

Slack ingestion commands should return JSON, matching the existing CLI style.

Expected failures:

- missing `SLACK_BOT_TOKEN`
- missing `SLACK_APP_TOKEN` for `slack-listen`
- Slack API permission errors
- unknown channel
- network timeout
- path safety rejection

Failures should write audit events and exit without corrupting existing inbox or
corpus files.

## Security

- Never commit Slack tokens or raw `.env`.
- Do not write Slack data outside `inbox/slack/` or `corpus/slack/`.
- Ignore bot-originated events to avoid reply loops.
- Keep Slack import explicit by channel and limit; do not crawl the workspace.
- Imported data may contain sensitive content, so the README should warn users
  to redact secrets and production PII before promoting to corpus.

## Testing

Unit tests should cover:

- deterministic Slack thread filename generation
- markdown rendering from Slack messages
- bot-message filtering
- `sync-slack --mode inbox` path selection
- `sync-slack --mode corpus` path selection
- `promote-slack-thread` path safety
- recursive inbox discovery for `inbox/slack/*.md`
- JSON error output for missing tokens or permissions

Integration testing on ASUS should cover:

- `./bin/imem slack-listen` receives one Slack test message
- a file appears in `inbox/slack/`
- OpenClaw can process that file
- the bot posts only a memory-backed answer, not raw ingested Slack
- a manually promoted thread appears under `corpus/slack/`
- forced corpus ingest indexes the promoted thread

## Implementation Notes

- `promote-slack-thread` copies rather than moves.
- `slack-listen` should work manually first. The ASUS webhook script, tmux,
  launchd, or systemd can run it later without changing the command contract.
- Keep all Slack ingestion additions behind explicit CLI commands so existing
  demo behavior remains stable until the operator starts Slack intake.
