# Better Slack Responses — Design Spec

## Overview

Improve the live Slack listener so Memory Claw stops repeating raw search snippets and instead replies like a grounded teammate. The listener should summarize relevant institutional memory, cite the sources, and provide next-step advice only when the user asks for it or enables advice mode in the current thread.

This design applies to the live Socket Mode listener path in `institutional_memory/listener.py`. It does not change the existing OpenClaw draft-processing path in `SOUL.md`.

## Goals

- Turn repeated "Found relevant context" snippet dumps into useful Slack answers.
- Support per-thread advice behavior without adding persistent state.
- Keep all answers grounded in retrieved ChromaDB hits and Slack thread text.
- Compare the current situation to prior precedent when users ask "what happened last time?" or similar.
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
| `offer` | Default. Give grounded context. On the first substantive bot reply in a thread, include a tiny action footer that offers advice and source commands. |
| `on` | Include a `Suggested next move` section when retrieved context supports one. |
| `off` | Never include advice. Only summarize the relevant memory. |

Thread modes live in `ListenerState.thread_advice_modes`, keyed by `(channel, thread_ts)`. Restarting the listener clears this state. That is acceptable for the current demo and local terminal workflow; users can toggle again with a short Slack message.

## Thread Toggle Commands

The listener should detect simple human messages in active bot threads:

- `advice on` sets the thread mode to `on` and replies with a short confirmation.
- `advice off` sets the thread mode to `off` and replies with a short confirmation.
- `advice offer` sets the thread mode to `offer` and replies with a short confirmation.

Additional natural replies after an offer:

- `yes`, `go ahead`, or similar short affirmative replies set the thread mode to `on` only if the previous bot reply in that same thread included an advice offer.
- `no`, `no advice`, or similar short negative replies set the thread mode to `off` only if the previous bot reply in that same thread included an advice offer.
- Direct advice requests such as `advice`, `what should we do`, or `next move?` are handled as advice intent regardless of pending offer state.

Toggle handling happens before memory search so command messages do not produce redundant search replies.

## Intent Handling

The composer should classify the current turn into a small intent set:

| Intent | Examples | Response behavior |
| --- | --- | --- |
| `context` | "interesting", "need more information", "anything else?" | Summarize relevant memory. |
| `advice` | "tips?", "next move?", "should we?", "what do you recommend?" | Include advice directly, even if thread mode is `offer`. |
| `precedent` | "compare to precedent", "what happened last time?", "similar prior deal?", "any previous examples?" | Contrast the current situation with the closest prior memory. Do not include advice unless advice mode or wording requires it. |
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

When the user asks for precedent, include a comparison block:

```text
Closest precedent:
- Similarity: prior enterprise deal also involved custom SSO, white-label scope, and timeline pressure.
- Difference: prior thread treated engineering review as a pre-signature blocker, not a post-signature follow-up.
- Lesson: do not lock timeline or contract language before scope validation.
```

In `offer` mode, the first substantive bot reply in a thread may include a tiny action footer:

```text
Next: reply "advice", "show source 1", or "show full source 1".
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

Rules use glob-style paths relative to the repository root. Last matching rule wins, so a broad demo-safe rule can be overridden by a specific restricted rule.

Demo policy should intentionally make common mock documents shareable while showing that restrictions work:

```yaml
default: restricted
rules:
  - pattern: "company/corpus/mock_data/**"
    access: share
  - pattern: "company/corpus/2023_rfp_postmortem.txt"
    access: share
  - pattern: "company/corpus/mock_data/policy_docs/Secrets_Management_Policy.md"
    access: cite_only
  - pattern: "company/corpus/mock_data/incidents/GitHub_Credentials_Leak_2023.md"
    access: restricted
```

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
- Show the footer only once per active thread unless the available command set changes. The command set changes only when the visible source policies change, for example when a later reply has a `share` source after the first reply had only `excerpt` sources.
- Mark the thread as having a pending advice offer only when the footer includes `advice`.
- Omit the footer for confirmations like `advice on`.

Full-source commands should be rate-limited per thread. A simple 30-second cooldown for `show full source N` is enough for the first implementation.

## Architecture

Add a response composition layer between search and Slack posting:

```text
Slack event
  -> listener filter and dedupe
  -> toggle detection
  -> source display command detection
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
- Build precedent comparisons from current Slack text plus top allowed memory hits.
- Build a compact, grounded prompt for Ollama using only policy-approved excerpts.
- Build action footers from advice mode plus source policy.
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
- Enforce source command policy and return a user-safe refusal for `cite_only` or unavailable sources.

Modified module:

- `institutional_memory/listener.py`

Responsibilities:

- Store `thread_advice_modes`.
- Store `thread_footer_shown` and `thread_advice_offer_pending` flags.
- Store `thread_source_refs` for the most recent visible source list in each active thread.
- Store `thread_full_source_cooldowns` for simple source command rate limiting.
- Handle advice toggle commands before search.
- Handle source display commands before search.
- Pass current text, thread context, hits, mode, and intent into the composer.
- Log response mode and intent in `listener_reply`.

## Thread Context Window

Retrieval and composition should share one bounded human thread context:

- Fetch at most the last 10 Slack replies.
- Exclude bot messages and messages from Memory Claw.
- Strip Memory Claw mention tokens.
- Cap total human thread context at 2,000 characters.
- Prefer the most recent messages when trimming is needed.

This keeps prompts small, avoids repeating bot output back into the model, and makes retrieval/composition use the same context window.

## Ollama Composition

Use the existing Ollama dependency already used for embeddings. Add config:

```python
RESPONSE_MODEL = os.getenv("RESPONSE_MODEL", "qwen2.5:7b-instruct")
RESPONSE_TIMEOUT_SECONDS = float(os.getenv("RESPONSE_TIMEOUT_SECONDS", "15"))
```

Prompt rules:

- Use only provided thread context and policy-approved memory excerpts.
- Do not invent facts, dates, owners, or commitments.
- For precedent requests, explicitly separate similarities, differences, and lessons from retrieved memory.
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
- Source display command with no remembered source list: reply with a short "I do not have a recent source list for this thread" message.
- Full-source command inside cooldown: reply with a short cooldown message and do not repost the document.
- Ollama unavailable: fallback composer, no crash.
- `search_memory` failure: existing listener error behavior remains.
- Slack post failure: existing listener error behavior remains.
- Empty generated response: fallback composer.

## Testing

Add focused unit tests:

- `detect_response_intent()` recognizes advice questions.
- `detect_response_intent()` recognizes precedent comparison requests.
- `detect_thread_advice_command()` parses `advice on`, `advice off`, and `advice offer`.
- Short `yes`/`no` replies only change advice mode when `thread_advice_offer_pending` is set for that thread.
- Toggle command updates `ListenerState.thread_advice_modes` and does not call `search_memory`.
- Advice mode `off` omits suggested next move.
- Advice mode `on` includes suggested next move when composer fallback is used.
- Advice mode `offer` adds the action footer only once per active thread.
- Thread context sent to the composer is capped at 10 human messages and 2,000 characters.
- Precedent responses include closest precedent, similarity, difference, and lesson sections.
- Composer fallback includes filenames and scores.
- `restricted` sources are removed before composer sees them.
- Unmatched sources default to `restricted`.
- `cite_only` sources are cited without excerpts.
- `excerpt` sources allow `show source N`.
- `share` sources allow `show full source N` only on explicit request.
- Action footer only includes commands allowed by source policy and advice mode.
- `show full source N` observes the per-thread cooldown.
- Listener audit logs include `response_intent` and `advice_mode`.
- Full mocked integration test covers event handling through toggle check, search, source policy filtering, composition fallback, Slack post, and audit metadata.

## Acceptance Criteria

- In the Vantara thread, "interesting, i need more information on this" produces a grounded summary instead of repeated raw snippets.
- "anything else, any tips on our next move?" produces a suggested next move grounded in retrieved Vantara sources.
- "compare this to precedent" produces a concise comparison between the current situation and closest prior relevant memory.
- `advice off` in a thread disables suggestions for that thread.
- `advice on` in a thread enables suggestions for that thread.
- Short `yes` does not enable advice unless the bot just offered advice in that thread.
- Source citations remain visible in Slack.
- Full document output is available only for `share` sources and only after `show full source N`.
- `restricted` sources never appear in Slack replies or LLM prompts.
- Action footer appears on the first useful bot reply in a thread, then stays quiet for repeated replies.
- Tests pass with Ollama mocked; feature remains usable when generation fails.
