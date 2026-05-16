# Slack Auto-Promotion Design

## Overview

Add opt-in Slack memory capture: when a human reacts to a Slack message with an approved emoji, Memory Claw promotes that Slack thread into corpus memory.

The promoted corpus entry should not be a raw transcript by itself. It should be an indexed memory card backed by a raw evidence snapshot. The memory card gives retrieval a clean, reusable summary. The evidence snapshot preserves the original Slack thread for audit and debugging without letting casual Slack chatter pollute vector search.

## Goals

- Let humans curate Slack threads into institutional memory with `:memo:` or `:brain:`.
- Store a concise, searchable memory card in `company/corpus/slack/promoted/`.
- Store the full Slack thread as non-indexed evidence in `company/corpus/slack/evidence/`.
- Capture resolution only when the thread contains one.
- Keep manual corpus ingest behavior explicit unless a separate ingest automation is added.
- Prevent bot replies alone from promoting noisy or sensitive threads.

## Non-Goals

- Do not promote based only on "bot responded".
- Do not promote every thread with source attribution.
- Do not invent decisions, owners, resolutions, or lessons.
- Do not replace existing manual `promote-slack-thread`.
- Do not auto-ingest on every reaction in the first implementation unless explicitly enabled later.

## Trigger Signals

### Version 1 Trigger

Only `reaction_added` from a human user can trigger auto-promotion.

Allowed reactions:

- `memo`
- `brain`

The reaction may be added to any message in a thread. The promoted unit is the parent thread, not just the reacted message.

### Signals Not Used As Triggers

These signals are useful metadata but are not enough to promote by themselves:

- Bot replied in thread.
- Bot reply cited one or more corpus sources.
- Thread crossed a search relevance threshold.

If a matching `listener_reply` audit event exists for the same channel and thread, its source list should be included in the memory card as related sources.

## Approaches Considered

### Recommended: Memory Card Plus Raw Evidence

Write an indexed markdown memory card and a non-indexed JSON evidence snapshot.

Benefits:

- Best retrieval quality.
- Preserves audit trail.
- Lets the summary focus on decision, resolution, and reusable lesson.

Trade-off:

- Requires a small summarization/composition step.

### Alternative: Raw Thread Only

Copy the rendered Slack thread markdown directly into corpus.

Benefits:

- Very simple.
- Already close to manual promotion behavior.

Trade-off:

- Noisy Slack messages become searchable. Retrieval may match jokes, acknowledgements, or side comments instead of the durable lesson.

### Alternative: Summary Only

Index only a generated summary and discard or ignore the raw transcript.

Benefits:

- Clean retrieval.
- Smaller corpus footprint.

Trade-off:

- Weak auditability. If summarization is wrong, there is no local evidence trail to inspect.

## Data Flow

```text
Slack reaction_added event
-> scripts/slack_listener.py acks event
-> institutional_memory/slack_promotion.py validates reaction and user
-> fetch parent thread via conversations.replies
-> fetch permalink via chat.getPermalink
-> find related listener_reply audit sources for channel/thread_ts
-> compose memory card
-> write company/corpus/slack/promoted/<channel>_<thread_ts>.md
-> write company/corpus/slack/evidence/<channel>_<thread_ts>.json
-> log slack_thread_auto_promoted
-> return JSON status
```

The listener should keep its current ack-first pattern. Slack API calls, summary generation, file writes, and audit logging run only after the Socket Mode acknowledgement.

## Artifact Format

Indexed memory card:

```markdown
# Slack Memory: <short title>

Promoted At: 2026-05-16T00:00:00+00:00
Promoted By: U123
Reaction: :memo:
Channel: C123
Thread TS: 1710000000.000000
Permalink: https://example.slack.com/archives/C123/p1710000000000000
Status: open | decision | resolved | unknown

## What Happened

Short factual summary of the thread.

## Decision Or Resolution

The decision or resolution stated in the thread. If none is stated: No resolution captured.

## Key Lesson

Reusable takeaway for future searches. If no lesson is supported: No reusable lesson captured.

## Related Sources

- company/corpus/example.md

## Evidence

Raw Slack thread snapshot: company/corpus/slack/evidence/C123_1710000000.000000.json
```

Raw evidence snapshot:

```json
{
  "channel": "C123",
  "thread_ts": "1710000000.000000",
  "permalink": "https://example.slack.com/archives/C123/p1710000000000000",
  "promoted_by": "U123",
  "reaction": "memo",
  "messages": [
    {"ts": "1710000000.000000", "user": "U123", "text": "Need precedent"}
  ]
}
```

The JSON evidence file is stored under `company/corpus/` for locality but is not indexed by the current ingest pipeline because ingest only reads `.txt`, `.md`, and `.pdf`.

## Summary Rules

The memory card composer must be conservative:

- Use only Slack thread text and related source filenames.
- Do not invent resolution if the thread does not contain one.
- Use `Status: resolved` only when completion or fix is explicit.
- Use `Status: decision` when the thread contains a clear choice but no completed outcome.
- Use `Status: open` when follow-up work remains.
- Use `Status: unknown` when the thread is ambiguous.
- Keep the card short enough to be a useful retrieval target.

An LLM may draft the card, but deterministic post-processing must enforce required fields and safe fallbacks. If generation fails, write a deterministic card with the first substantive message, `Status: unknown`, and `No resolution captured`.

## Idempotency

Promotion is keyed by `(channel, thread_ts)`.

- If the memory card already exists, return `status: exists`.
- Do not rewrite existing cards unless an explicit force/update path is added later.
- Multiple approved reactions on the same thread should not create duplicate cards.
- Audit each trigger attempt with status `promoted`, `exists`, `ignored`, or `error`.

## Ingest Behavior

Promotion writes files to corpus, but those files do not become searchable until corpus ingest runs.

Version 1 should return a reminder matching current behavior:

```text
run uv run python scripts/ingest_corpus.py --force to make promoted Slack memory searchable
```

Future automation can add a systemd timer, cron, dashboard-triggered ingest, or a debounced listener-side ingest worker. That automation is separate from the reaction promotion design to avoid running expensive embedding work inside Slack event handling.

## Security And Safety

- Ignore reactions from bots.
- Process only configured emoji names.
- Process only channels the bot is allowed to read.
- Validate all output paths under `company/corpus/slack/promoted/` and `company/corpus/slack/evidence/`.
- Store Slack user IDs as provided by Slack; do not attempt identity enrichment in v1.
- Do not paste full evidence back into Slack.
- If source policy is present, memory cards created by this path should default to restricted until an explicit policy rule allows them to be cited or shown.

## Integration Points

New module:

- `institutional_memory/slack_promotion.py`

Responsibilities:

- Identify promotion reactions.
- Resolve the parent thread timestamp.
- Fetch thread messages and permalink.
- Compose memory card markdown.
- Write card and evidence files.
- Return JSON-safe status dictionaries.

Modified module:

- `scripts/slack_listener.py`

Responsibilities:

- Route `reaction_added` events to `slack_promotion.py`.
- Preserve ack-first behavior.
- Continue routing message events through existing Slack ingest and answer loop.

Existing module reuse:

- `institutional_memory.slack_ingest.thread_ts()` for parent thread naming semantics.
- `institutional_memory.paths.safe_corpus_path()` for path safety.
- `institutional_memory.audit.log_event()` for promotion audit events.
- Existing ingest pipeline for making promoted markdown searchable after ingest.

## Error Handling

- Slack API failure while fetching thread: log `slack_thread_auto_promote_failed`, return `status: error`.
- Missing permalink: continue with empty permalink and log a warning field.
- Empty thread: return `status: ignored`, reason `empty_thread`.
- Unsupported reaction: return `status: ignored`, reason `unsupported_reaction`.
- Bot reaction: return `status: ignored`, reason `bot_reaction`.
- Existing card: return `status: exists` and do not rewrite.
- Summary failure: write deterministic fallback card and include `summary_mode: fallback`.

## Tests

Add focused unit tests:

- Approved reactions trigger promotion.
- Unsupported reactions are ignored.
- Bot reactions are ignored.
- Reaction on a thread reply promotes the parent thread.
- Promotion writes one `.md` card and one `.json` evidence file.
- Existing promotion returns `exists` without rewriting.
- Memory card contains required metadata fields.
- Missing resolution writes `No resolution captured`.
- Related sources from a matching `listener_reply` audit event appear in the card.
- JSON evidence is not included in ingestable file suffixes.
- Slack API failure returns JSON-safe error status.
- Listener routes `reaction_added` events without invoking message search/reply logic.

## Acceptance Criteria

- Adding `:memo:` to a Slack thread creates a memory card under `company/corpus/slack/promoted/`.
- Adding `:brain:` behaves the same, with the reaction recorded in metadata.
- The full thread is preserved as JSON evidence under `company/corpus/slack/evidence/`.
- The card states a resolution only when the thread text supports one.
- Repeating the reaction does not create duplicate corpus entries.
- The promoted card becomes searchable after `uv run python scripts/ingest_corpus.py --force`.
- No promotion occurs from bot response alone.
