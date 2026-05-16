# Better Slack Responses — Design Spec

## Overview

Improve the live Slack listener so Memory Claw stops repeating raw search snippets and instead replies like a grounded teammate. The listener should summarize relevant institutional memory, cite the sources, and provide next-step advice only when the user asks for it or enables advice mode in the current thread.

This design applies to the live Socket Mode listener path in `institutional_memory/listener.py`. It does not change the existing OpenClaw draft-processing path in `SOUL.md`.

## Goals

- Turn repeated "Found relevant context" snippet dumps into useful Slack answers.
- Support per-thread advice behavior without adding persistent state.
- Keep all answers grounded in retrieved ChromaDB hits and Slack thread text.
- Preserve source transparency while respecting manual document restrictions.
- Fall back to deterministic formatting if Ollama generation is unavailable.

## Non-Goals

- Persist thread advice preferences across listener restarts.
- Add per-user identity, role-based access, or channel-specific ACLs.
- Replace ChromaDB search or change ingestion.

## Response Modes

Each active Slack thread has an in-memory advice mode:

| Mode | Behavior |
| --- | --- |
| `offer` | Default. Give grounded context. If the thread appears decision-sensitive, add "I can suggest a next move if useful." |
| `on` | Include a `Suggested next move` section when retrieved context supports one. |
| `off` | Never include advice. Only summarize the relevant memory. |

Thread modes live in `ListenerState.thread_advice_modes`, keyed by `(channel, thread_ts)`. Restarting the listener clears this state. That is acceptable for the current demo and local terminal workflow; users can toggle again with a short Slack message.

## Thread Toggle Commands

The listener should detect simple human messages in active bot threads:

- `advice on` sets the thread mode to `on` and replies with a short confirmation.
- `advice off` sets the thread mode to `off` and replies with a short confirmation.
- `advice offer` sets the thread mode to `offer` and replies with a short confirmation.

Additional natural replies after an offer:

- `yes`, `go ahead`, `advice`, `what should we do`, or similar affirmative advice requests set the thread mode to `on` for that thread.
- `no`, `no advice`, or similar negative replies set the thread mode to `off` for that thread.

Toggle handling happens before memory search so command messages do not produce redundant search replies.

## Intent Handling

The composer should classify the current turn into a small intent set:

| Intent | Examples | Response behavior |
| --- | --- | --- |
| `context` | "interesting", "need more information", "anything else?" | Summarize relevant memory. |
| `advice` | "tips?", "next move?", "should we?", "what do you recommend?" | Include advice directly, even if thread mode is `offer`. |
| `toggle` | "advice on", "advice off" | Update mode and confirm. |
| `no_hit` | No search results | Existing mention no-hit behavior remains. |

Intent classification can be deterministic keyword matching at first. The LLM composer can receive the selected intent and mode rather than deciding policy from scratch.

## Answer Shape

Generated Slack replies should stay short and scannable:

```text
What memory says:
- Vantara wanted custom SSO and white-label, but the prior draft was still internal.
- The sales-eng thread flagged delivery risk around the 8-week timeline.

Suggested next move:
Loop in engineering before signature and confirm SSO scope, white-label requirements, and SLA obligations before committing to 8 weeks.

Sources:
- Vantara_Proposal_Draft_v0.1.md (76%)
- Vantara_Enterprise_Deal_Demo_Thread.md (70%)
```

If advice is not included but the thread appears decision-sensitive:

```text
I can suggest a next move if useful.
```

## Source Policy

Add a manual source policy file under the corpus, for example:

```text
company/corpus/.source_policy.yml
```

Each source can be assigned one of four access levels:

| Level | Behavior |
| --- | --- |
| `restricted` | Invisible to the Slack bot. Filtered before LLM composition, citations, excerpts, and full-source commands. |
| `cite_only` | May appear as a source filename with score, but no content excerpt and no full document output. |
| `excerpt` | Snippets may be passed to the LLM and shown with `show source N`; full document is not shown. |
| `share` | Snippets may be passed to the LLM, and full document may be shown only after explicit `show full source N`. |

Default policy should be conservative. New or unmatched files default to `restricted`. The implementation should add explicit policy entries for demo-safe corpus files that may be cited, excerpted, or shared.

Policy is enforced in deterministic code before any LLM call. Prompt instructions are not treated as a security boundary.

## Source Handling

Sources should be citations by default, with pull-based source inspection.

Each reply should include:

- Source basename, not only full path.
- Match score percentage.
- A short evidence excerpt only for `excerpt` and `share` sources.
- Full corpus path in an audit event for traceability.

Supported follow-up commands:

- `show source 1` posts the relevant excerpt for source 1 if policy is `excerpt` or `share`.
- `show full source 1` posts or attaches the full source only if policy is `share`.
- `show source 1` for `cite_only` replies that the source can be cited but not shown in Slack.
- Any source command for `restricted` should behave as if the source is unavailable.

Do not auto-attach or auto-paste full documents. Even for `share` documents, full output requires an explicit user request.

Replies may include a tiny action footer when useful:

```text
Next: reply "advice", "show source 1", or "show full source 1".
```

Footer rules:

- Include `advice` only when the effective advice mode is `offer`.
- Include `show source N` only for sources with `excerpt` or `share` policy.
- Include `show full source N` only for sources with `share` policy.
- Omit the footer for confirmations like `advice on`.

## Architecture

Add a response composition layer between search and Slack posting:

```text
Slack event
  -> listener filter and dedupe
  -> toggle detection
  -> thread-aware query build
  -> search_memory()
  -> apply source policy
  -> compose_slack_answer()
  -> chat_postMessage()
```

New module:

- `institutional_memory/response_composer.py`

Responsibilities:

- Detect advice/toggle intent from current text.
- Resolve effective advice behavior from thread mode and intent.
- Build a compact, grounded prompt for Ollama using only policy-approved excerpts.
- Validate and trim model output for Slack.
- Provide deterministic fallback formatting.

New module:

- `institutional_memory/source_policy.py`

Responsibilities:

- Load source policy rules from `company/corpus/.source_policy.yml`.
- Assign access levels to search hits.
- Filter `restricted` hits before composition.
- Remove excerpts from `cite_only` hits before LLM prompts.
- Resolve source display commands like `show source 1` and `show full source 1`.

Modified module:

- `institutional_memory/listener.py`

Responsibilities:

- Store `thread_advice_modes`.
- Handle advice toggle commands before search.
- Pass current text, thread context, hits, mode, and intent into the composer.
- Log response mode and intent in `listener_reply`.

## Ollama Composition

Use the existing Ollama dependency already used for embeddings. Add config:

```python
RESPONSE_MODEL = os.getenv("RESPONSE_MODEL", "qwen2.5:7b-instruct")
RESPONSE_TIMEOUT_SECONDS = float(os.getenv("RESPONSE_TIMEOUT_SECONDS", "8"))
```

Prompt rules:

- Use only provided thread context and policy-approved memory excerpts.
- Do not invent facts, dates, owners, or commitments.
- If advice is enabled, phrase advice as a suggested next move grounded in sources.
- If advice is disabled, omit recommendations.
- Keep under a configured Slack-safe character budget.
- Always include source filenames and scores.

If model generation fails, times out, or returns empty text, use deterministic fallback:

- `What memory says`: top 2-3 truncated hit snippets.
- `Sources`: filenames and scores.
- Optional offer line when mode is `offer`.

## Error Handling

- Toggle command parse failure: ignore and continue normal search.
- Source policy file missing or malformed: treat all sources as `restricted` and log a warning.
- Ollama unavailable: fallback composer, no crash.
- `search_memory` failure: existing listener error behavior remains.
- Slack post failure: existing listener error behavior remains.
- Empty generated response: fallback composer.

## Testing

Add focused unit tests:

- `detect_response_intent()` recognizes advice questions.
- `detect_thread_advice_command()` parses `advice on`, `advice off`, and `advice offer`.
- Toggle command updates `ListenerState.thread_advice_modes` and does not call `search_memory`.
- Advice mode `off` omits suggested next move.
- Advice mode `on` includes suggested next move when composer fallback is used.
- Advice mode `offer` adds offer line for decision-sensitive context.
- Composer fallback includes filenames and scores.
- `restricted` sources are removed before composer sees them.
- Unmatched sources default to `restricted`.
- `cite_only` sources are cited without excerpts.
- `excerpt` sources allow `show source N`.
- `share` sources allow `show full source N` only on explicit request.
- Action footer only includes commands allowed by source policy and advice mode.
- Listener audit logs include `response_intent` and `advice_mode`.

## Acceptance Criteria

- In the Vantara thread, "interesting, i need more information on this" produces a grounded summary instead of repeated raw snippets.
- "anything else, any tips on our next move?" produces a suggested next move grounded in retrieved Vantara sources.
- `advice off` in a thread disables suggestions for that thread.
- `advice on` in a thread enables suggestions for that thread.
- Source citations remain visible in Slack.
- Full document output is available only for `share` sources and only after `show full source N`.
- `restricted` sources never appear in Slack replies or LLM prompts.
- Tests pass with Ollama mocked; feature remains usable when generation fails.
