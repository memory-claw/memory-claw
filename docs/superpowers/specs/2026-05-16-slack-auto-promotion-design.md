# Slack Auto-Promotion Design

## Overview

Add opt-in Slack memory capture: when a human reacts to a Slack message with an approved emoji, Memory Claw promotes that Slack thread into corpus memory.

The promoted corpus entry should not be a raw transcript by itself. It should be an indexed memory card backed by a raw evidence snapshot. The memory card gives retrieval a clean, reusable summary. The evidence snapshot preserves the original Slack thread for audit and debugging without letting casual Slack chatter pollute vector search.

## Goals

- Let humans curate Slack threads into institutional memory with `:memo:` or `:brain:`.
- Store a concise, searchable memory card in `company/corpus/slack/promoted/`.
- Store the full Slack thread as non-indexed evidence in `company/evidence/slack/`.
- Capture a resolution only when the thread explicitly contains one.
- Keep manual corpus ingest behavior explicit unless a separate ingest automation is added.
- Prevent bot replies alone from promoting noisy or sensitive threads.
- Keep promotion disabled unless an explicit promotion channel allowlist is configured.

## Non-Goals

- Do not promote based only on "bot responded".
- Do not promote every thread with source attribution.
- Do not invent decisions, owners, resolutions, or lessons.
- Do not classify thread status in v1.
- Do not replace existing manual `promote-slack-thread`.
- Do not auto-ingest on every reaction in the first implementation unless explicitly enabled later.

## Trigger Signals

### Version 1 Trigger

Only `reaction_added` from a human user in a configured promotion channel can trigger auto-promotion.

Allowed reactions:

- `memo`
- `brain`

The reaction may be added to any message in a thread. The promoted unit is the parent thread, not just the reacted message.

Promotion is disabled when `PROMOTION_ALLOWED_CHANNELS` is empty. This differs from listener replies, where `LISTENER_CHANNELS` may fall back to `SLACK_CHANNEL`. Memory capture needs an explicit allowlist.

`PROMOTION_ALLOWED_CHANNELS` is comma-separated and accepts channel IDs or names:

```text
PROMOTION_ALLOWED_CHANNELS=C123,#engineering,#support
```

At listener startup, channel names are resolved to IDs through the existing Slack client. Runtime comparisons use channel IDs only. A reaction in a channel not in this allowlist returns `status: ignored`, reason `channel_not_allowed`.

### Signals Not Used As Triggers

These signals are useful metadata but are not enough to promote by themselves:

- Bot replied in thread.
- Bot reply cited one or more corpus sources.
- Thread crossed a search relevance threshold.

If a matching `listener_reply` audit event exists for the same channel and thread, its source list should be included in the memory card as related sources. This lookup is best-effort only. Missing, malformed, or old audit data must not block promotion.

## Approaches Considered

### Recommended: Memory Card Plus Raw Evidence

Write an indexed markdown memory card and a non-indexed JSON evidence snapshot.

Benefits:

- Best retrieval quality.
- Preserves audit trail.
- Lets the summary focus on what happened and any explicit resolution.

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
-> reject if channel not in PROMOTION_ALLOWED_CHANNELS
-> reject if user or global promotion rate limit is exceeded
-> fetch parent thread via conversations.replies
-> fetch permalink via chat.getPermalink
-> find related listener_reply audit sources for channel/thread_ts, best effort
-> compose memory card
-> write company/corpus/slack/promoted/<channel>_<thread_ts>.md
-> write company/evidence/slack/<channel>_<thread_ts>.json
-> log slack_thread_auto_promoted
-> return JSON status
```

The listener should keep its current ack-first pattern. Slack API calls, summary generation, file writes, and audit logging run only after the Socket Mode acknowledgement.

## Artifact Format

Indexed memory card:

```markdown
# Slack Memory: Need precedent for vendor liability clause

Promoted At: 2026-05-16T00:00:00+00:00
Promoted By: U123
Reaction: :memo:
Channel: C123
Thread TS: 1710000000.000000
Permalink: https://example.slack.com/archives/C123/p1710000000000000

## What Happened

Short factual summary of the thread.

## Resolution

The resolution stated in the thread.

If none is stated: No resolution captured.

## Reusable Takeaway

Only include this section when the thread explicitly states a reusable lesson, rule, or decision pattern.

## Related Sources

- company/corpus/example.md

## Evidence

Raw Slack thread snapshot: company/evidence/slack/C123_1710000000.000000.json
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

The JSON evidence file is stored outside `company/corpus/` so future ingest suffix changes cannot accidentally index raw Slack transcripts.

## Title Generation

The card title is deterministic:

- Pick the first substantive human message in the parent thread.
- HTML-unescape it.
- Strip Slack mention tokens.
- Collapse whitespace.
- Truncate to 80 characters.
- Fall back to `Slack thread <channel> <thread_ts>` when no substantive human text exists.

The LLM must not generate the title in v1.

## Summary Rules

The memory card composer must be conservative:

- Use only Slack thread text and related source filenames.
- Do not invent resolution if the thread does not contain one.
- Always include `Resolution`; write `No resolution captured` unless the thread explicitly states a decision, fix, answer, or outcome.
- Omit `Reusable Takeaway` unless the thread explicitly states a reusable lesson, rule, or decision pattern.
- Use a bounded composition window for the card: first substantive message, last 10 human messages, and at most 4,000 characters total.
- Store the full unbounded thread in the evidence JSON.
- Keep the card short enough to be a useful retrieval target, with a target maximum of 2,000 characters.

An LLM may draft the card body, but deterministic post-processing must enforce required fields and safe fallbacks. If generation fails, write a deterministic card with the title, a compact message preview, and `No resolution captured`.

## Rate Limiting

Promotion uses in-memory listener rate limiting in v1:

- `PROMOTION_USER_COOLDOWN_SECONDS`, default `60`
- `PROMOTION_GLOBAL_MAX_PER_MINUTE`, default `10`

If a user exceeds the cooldown, return `status: ignored`, reason `rate_limited_user`. If the listener exceeds the global cap, return `status: ignored`, reason `rate_limited_global`.

The limits reset when the listener restarts. That is acceptable for the current local demo service. Persisted rate-limit state is a non-goal for v1.

## Idempotency

Promotion is keyed by `(channel, thread_ts)`.

- If the memory card already exists, return `status: exists`.
- Do not rewrite existing cards unless an explicit force/update path is added later.
- Multiple approved reactions on the same thread should not create duplicate cards.
- Audit each trigger attempt with status `promoted`, `exists`, `ignored`, or `error`.
- Manual `promote-slack-thread` and auto-promotion do not collide. Manual promotion keeps copying raw Slack markdown to `company/corpus/slack/<channel>_<thread_ts>.md`; auto-promotion writes memory cards to `company/corpus/slack/promoted/<channel>_<thread_ts>.md` and evidence to `company/evidence/slack/<channel>_<thread_ts>.json`.

## Ingest Behavior

Promotion writes the memory card to corpus, but it does not become searchable until corpus ingest runs. Evidence JSON is outside corpus and is never intended to be searchable.

Version 1 should return a reminder matching current behavior:

```text
run uv run python scripts/ingest_corpus.py --force to make promoted Slack memory searchable
```

Future automation can add a systemd timer, cron, dashboard-triggered ingest, or a debounced listener-side ingest worker. That automation is separate from the reaction promotion design to avoid running expensive embedding work inside Slack event handling.

## Security And Safety

- Ignore reactions from bots.
- Process only configured emoji names.
- Process only channels explicitly listed in `PROMOTION_ALLOWED_CHANNELS`.
- Default `PROMOTION_ALLOWED_CHANNELS` to empty, meaning promotion is disabled.
- Validate all output paths under `company/corpus/slack/promoted/` and `company/evidence/slack/`.
- Store Slack user IDs as provided by Slack; do not attempt identity enrichment in v1.
- Do not paste full evidence back into Slack.
- If source policy is present, memory cards created by this path should default to restricted until an explicit policy rule allows them to be cited or shown.

## Integration Points

New module:

- `institutional_memory/slack_promotion.py`

Responsibilities:

- Identify promotion reactions.
- Enforce promotion channel allowlist.
- Enforce per-user and global promotion rate limits.
- Resolve the parent thread timestamp.
- Fetch thread messages and permalink.
- Build deterministic card titles.
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
- `institutional_memory.paths.safe_corpus_path()` for memory card path safety.
- A new `safe_evidence_path()` helper for evidence path safety under `company/evidence/`.
- `institutional_memory.audit.log_event()` for promotion audit events.
- Existing ingest pipeline for making promoted markdown searchable after ingest.

Config additions:

```python
PROMOTION_ALLOWED_CHANNELS = os.getenv("PROMOTION_ALLOWED_CHANNELS", "")
PROMOTION_USER_COOLDOWN_SECONDS = float(os.getenv("PROMOTION_USER_COOLDOWN_SECONDS", "60"))
PROMOTION_GLOBAL_MAX_PER_MINUTE = int(os.getenv("PROMOTION_GLOBAL_MAX_PER_MINUTE", "10"))
COMPANY_EVIDENCE_PATH = COMPANY_DOCS_PATH / "evidence"
```

## Error Handling

- Slack API failure while fetching thread: log `slack_thread_auto_promote_failed`, return `status: error`.
- Missing permalink: continue with empty permalink and log a warning field.
- Empty thread: return `status: ignored`, reason `empty_thread`.
- Channel not allowed: return `status: ignored`, reason `channel_not_allowed`.
- Unsupported reaction: return `status: ignored`, reason `unsupported_reaction`.
- Bot reaction: return `status: ignored`, reason `bot_reaction`.
- Rate limit exceeded: return `status: ignored`, reason `rate_limited_user` or `rate_limited_global`.
- Existing card: return `status: exists` and do not rewrite.
- Summary failure: write deterministic fallback card and include `summary_mode: fallback`.
- Related audit source lookup failure: continue without related sources and include `related_sources_mode: unavailable`.

## Tests

Add focused unit tests:

- Approved reactions trigger promotion.
- Unsupported reactions are ignored.
- Bot reactions are ignored.
- Reactions are ignored when `PROMOTION_ALLOWED_CHANNELS` is empty.
- Reactions are ignored in channels outside `PROMOTION_ALLOWED_CHANNELS`.
- Channel names in `PROMOTION_ALLOWED_CHANNELS` resolve to IDs at startup.
- Per-user cooldown blocks rapid repeat promotions.
- Global per-minute cap blocks bursts.
- Reaction on a thread reply promotes the parent thread.
- Promotion writes one `.md` card and one `.json` evidence file.
- Evidence JSON is written under `company/evidence/slack/`, not `company/corpus/`.
- Existing promotion returns `exists` without rewriting.
- Memory card contains required metadata fields.
- Missing resolution writes `No resolution captured`.
- Explicit reusable takeaway appears only when thread text supports it.
- Related sources from a matching `listener_reply` audit event appear in the card.
- Missing or malformed audit data does not block promotion.
- Long threads store full evidence but compose the card from a bounded window.
- Deterministic title uses the first substantive human message.
- Slack API failure returns JSON-safe error status.
- Listener routes `reaction_added` events without invoking message search/reply logic.

## Acceptance Criteria

- Adding `:memo:` to a Slack thread creates a memory card under `company/corpus/slack/promoted/`.
- Adding `:brain:` behaves the same, with the reaction recorded in metadata.
- Promotion only runs in channels explicitly listed in `PROMOTION_ALLOWED_CHANNELS`.
- The full thread is preserved as JSON evidence under `company/evidence/slack/`.
- The card states a resolution only when the thread text supports one.
- The card omits reusable takeaway unless thread text supports one.
- The card title is deterministic from the first substantive human message.
- Repeating the reaction does not create duplicate corpus entries.
- Rapid reaction bursts are rate-limited.
- The promoted card becomes searchable after `uv run python scripts/ingest_corpus.py --force`.
- No promotion occurs from bot response alone.
