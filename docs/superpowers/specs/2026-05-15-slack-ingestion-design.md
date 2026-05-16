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
- Run the live Socket Mode listener outside OpenClaw. It must not be an
  OpenClaw-facing `./bin/imem` subcommand because it is a blocking long-running
  process.
- Keep inbox and corpus roles explicit. New live Slack threads go to
  `inbox/slack/`; trusted historical memory goes to `corpus/slack/`.
- Do not automatically promote processed inbox threads into corpus in v1.
- Add manual commands for importing Slack into inbox, importing Slack into
  corpus, and promoting selected inbox files into corpus.
- Keep OpenClaw behavior unchanged: it only calls the existing one-shot
  `./bin/imem` commands to list inbox files, read a draft, search memory, send
  Slack, and mark processed.

## Non-Goals

- No public HTTPS webhook server in v1.
- No automatic classification of Slack messages as inbox versus corpus.
- No automatic corpus promotion after processing.
- No broad Slack workspace indexing.
- No production scheduler or daemon manager beyond a listener script that can be
  run by the ASUS webhook script, shell, tmux, launchd, or systemd later.

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
-> scripts/slack_listener.py running outside OpenClaw
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
-> command output reminds operator to run ingest
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

Add this long-running listener entrypoint. It is not OpenClaw-facing:

```bash
uv run python scripts/slack_listener.py
```

Add these one-shot `./bin/imem` operator commands:

```bash
./bin/imem sync-slack --mode inbox --channel C123 --limit 20
./bin/imem sync-slack --mode corpus --channel C123 --limit 100
./bin/imem promote-slack-thread --path inbox/slack/C123_1710000000.000000.md
```

`scripts/slack_listener.py` runs until stopped. It receives live Slack events
through Socket Mode and writes or updates inbox files. OpenClaw must never call
this script through exec.

`sync-slack` fetches recent Slack history on demand. `--mode inbox` writes
active files under `inbox/slack/`. `--mode corpus` writes trusted memory under
`corpus/slack/` and returns JSON with a note telling the operator to run
`uv run python scripts/ingest_corpus.py --force` before the imported Slack
history is searchable.

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

- Re-importing the same unprocessed thread rewrites the same deterministic file.
- Re-importing a thread that is already marked processed must not rewrite the
  processed inbox file unless the operator passes an explicit force flag.
- Bot messages are ignored for intake to avoid loops.
- Message update events should refresh only unprocessed inbox files.
- Deleted or inaccessible Slack messages are skipped with an audit event.
- Existing processed files remain protected by current processed-state behavior.
- `list-new-drafts` must be extended to find supported files under
  `inbox/slack/`, not only top-level inbox files.
- Keep the nested `inbox/slack/` layout rather than flattening Slack files into
  top-level inbox names. `safe_inbox_path()` already allows nested inbox files,
  and recursive discovery keeps source organization cleaner.
- `reset-demo` should get an explicit `--clear-slack-inbox` option, or README
  docs must tell the operator to clear `inbox/slack/*.md` manually before a
  fresh Slack ingestion demo.

## Error Handling

Slack ingestion commands should return JSON, matching the existing CLI style.

Expected failures:

- missing `SLACK_BOT_TOKEN`
- missing `SLACK_APP_TOKEN` for `scripts/slack_listener.py`
- Slack API permission errors
- unknown channel
- network timeout
- path safety rejection

Failures should write audit events and exit without corrupting existing inbox or
corpus files.

## Security

- Never commit Slack tokens or raw `.env`.
- Do not write Slack data outside `inbox/slack/` or `corpus/slack/`.
- Validate promotion source paths under `INBOX_PATH` and destination paths under
  `CORPUS_PATH`; never trust a raw path argument.
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
- `sync-slack --mode corpus` output includes the forced-ingest reminder
- `promote-slack-thread` path safety
- recursive inbox discovery for `inbox/slack/*.md`
- JSON error output for missing tokens or permissions
- broadened Slack source attribution pattern recognizes nested
  `corpus/slack/*.md` paths
- optional `dgx_check.py --check-slack-ingestion` reports missing
  `SLACK_APP_TOKEN` without making base DGX readiness depend on Socket Mode

Integration testing on ASUS should cover:

- `uv run python scripts/slack_listener.py` receives one Slack test message
- a file appears in `inbox/slack/`
- OpenClaw can process that file
- the bot posts only a memory-backed answer, not raw ingested Slack
- a manually promoted thread appears under `corpus/slack/`
- forced corpus ingest indexes the promoted thread
- `uv run python scripts/dgx_check.py --check-slack-ingestion --skip-backup-video`
  catches missing Slack ingestion configuration before live listener testing

## Implementation Notes

- `promote-slack-thread` copies rather than moves.
- The Slack source attribution regex in `institutional_memory/slack.py` must be
  broadened from single-level `.txt` sources to nested `.txt` and `.md` corpus
  sources, including `corpus/slack/<file>.md`.
- `scripts/slack_listener.py` should work manually first. The ASUS webhook
  script, tmux, launchd, or systemd can run it later without changing the
  command contract.
- Keep all Slack ingestion additions behind explicit CLI commands so existing
  demo behavior remains stable until the operator starts Slack intake.
- Do not add `scripts/slack_listener.py` to the OpenClaw exec allowlist.
