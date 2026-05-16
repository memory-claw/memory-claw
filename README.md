# memory-claw

Institutional Memory Engine demo for OpenClaw + local Ollama.

Spec: `2026-05-15-institutional-memory-engine.md`.

## Local Mac Status

This Mac has the tool layer implemented and tested. It is not the final live
demo machine. Final readiness still requires ASUS/DGX-only proof:

- `SLACK_BOT_TOKEN` and `SLACK_CHANNEL` in `.env`
- `nemotron-3-super:120b` responding within timeout
- OpenClaw audit events tagged `driver=openclaw`
- non-empty backup video under `demo_artifacts/`

## ASUS Setup

Run these commands on ASUS:

```bash
cd ~/memory-claw
git pull origin main
export PATH=$HOME/.local/bin:$PATH
uv sync
cp -n .env.example .env
```

Edit `.env` and set real Slack values:

```bash
nano .env
```

Required:

```text
OLLAMA_BASE_URL=http://127.0.0.1:11434
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL=#institutional-memory
SLACK_WEBHOOK_URL=
```

Pull/check models:

```bash
ollama pull qwen3-embedding:8b
ollama pull nemotron-3-super:120b
uv run python scripts/dgx_check.py --skip-backup-video
```

Expected:

```json
{"ok": true, "blockers": []}
```

Install OpenClaw workspace files:

```bash
mkdir -p ~/.openclaw/workspace/skills/institutional-memory
cp SOUL.md ~/.openclaw/workspace/SOUL.md
cp HEARTBEAT.md ~/.openclaw/workspace/HEARTBEAT.md
cp skills/institutional-memory/SKILL.md ~/.openclaw/workspace/skills/institutional-memory/SKILL.md
```

Then start OpenClaw with the existing ASUS script:

```bash
~/run_openclaw.sh
```

## ASUS Inbox

OpenClaw reads drafts from the repo inbox:

```text
~/memory-claw/company/inbox/
```

Mock data is split by role:

```text
company/corpus/mock_data/                         # old institutional memory to ingest
company/inbox/000_nhs_northeast_liability_demo.md # active draft/thread to process
company/inbox/010_cloudnest_vendor_onboarding_demo.md
company/inbox/020_meridian_pricing_demo.md
company/inbox/999_lunch_plans_noise_thread.md     # noise case, should not send Slack
docs/mock_data.md                         # dataset explanation, not ingested
```

Add a draft on ASUS:

```bash
cp ~/Downloads/mock_data.txt ~/memory-claw/company/inbox/
```

Or copy from Mac to ASUS:

```bash
scp -i ~/.ssh/asus_deploy ~/Downloads/mock_data.txt asus@100.68.221.47:/home/asus/memory-claw/company/inbox/
```

Supported demo input types are `.txt`, `.md`, and `.pdf`.

## Company Data

Use one parent folder for company documents:

```text
company/
|-- corpus/ # historical memory: postmortems, policies, contracts, Slack exports
`-- inbox/  # active drafts/threads that need a response
```

Put stable company knowledge in `company/corpus/`. Good examples:

- postmortems and incident reports
- won/lost bid writeups
- legal memos and approved clauses
- security/vendor policies
- exported Slack threads that describe decisions
- meeting notes with named owners and outcomes

Put active company drafts or threads in `company/inbox/`. The inbox scanner only
reads from `company/inbox/`, so all company-facing documents now live together
under `company/`.

Do not put secrets, credentials, private keys, raw customer PII, or production
tokens in `company/`, `company/corpus/`, or `company/inbox/`. Redact first.

Recommended file format:

```markdown
# Short Human Title

**Date:** 2024-03-01
**Owner:** Name / team
**Outcome:** What happened or what policy changed
**Risk:** Low/Medium/High/Critical

## Context
What happened, who was involved, and why it matters.

## Decision or Lesson
What future teams should remember.

## Source Attribution
Original system, channel, meeting, or document reference.
```

After adding company memory:

```bash
uv run python scripts/ingest_corpus.py --force
```

After adding a new draft/thread to check:

```bash
./bin/imem list-new-drafts
```

Then ask OpenClaw to check the inbox. The bot posts to Slack only when retrieved
memory passes the relevance threshold.

## Slack Behavior

Two paths share Chroma search but differ on triggers:

| Path | Trigger | Reply channel |
|------|---------|---------------|
| **Listener** (`scripts/slack_listener.py`) | Live Slack events | Same channel as the message (in-thread) |
| **OpenClaw** (`HEARTBEAT.md` + SOUL) | New files under `company/inbox/` | `SLACK_CHANNEL`, or draft `slack_channel_id` / `slack_thread_ts` when set |

`SLACK_BOT_TOKEN` lets `./bin/imem send-slack` post OpenClaw's final
memory-backed answer. For Slack-ingested inbox threads, SOUL passes
`--channel` and `--thread-ts` from draft metadata so replies land in the
original thread.

Listener env (see `.env.example`):

- `LISTENER_CHANNELS=*` — unprompted replies in any channel the bot is in
- `UNPROMPTED_THRESHOLD` — default `0.80`; use `0.65` for demos
- `LISTENER_CHANNEL_THRESHOLDS` — optional per-channel overrides
- `OPENCLAW_WAKE_CMD` — optional shell hook after listener writes inbox files

The bot should not post raw ingested Slack messages. It posts only when an
active inbox draft/thread matches useful institutional memory from `company/corpus/`.
The message should summarize the relevant context and include source
attribution, for example `company/corpus/2023_rfp_postmortem.txt`.

**@mentions** work in any channel the bot is invited to. **Unprompted** replies
require `LISTENER_CHANNELS=*` or an explicit channel list, plus a strong corpus match.

Slack ingestion uses Slack as an input source:

- resolved historical Slack threads belong in `company/corpus/slack/`, then run
  `uv run python scripts/ingest_corpus.py --force`
- active Slack messages or threads that need help belong in `company/inbox/`, then ask
  OpenClaw to check the inbox
- noise or casual threads should be marked `skipped_no_relevant_memory` and
  should not send Slack

## Slack Ingestion

Slack ingestion has two paths.

Live intake runs outside OpenClaw:

```bash
uv run python scripts/slack_listener.py
```

The listener requires:

```text
SLACK_APP_TOKEN=xapp-...
SLACK_BOT_TOKEN=xoxb-...
```

Manual active import writes Slack threads to inbox:

```bash
./bin/imem sync-slack --mode inbox --channel C123 --limit 20
```

Manual historical import writes trusted Slack threads to corpus:

```bash
./bin/imem sync-slack --mode corpus --channel C123 --limit 100
uv run python scripts/ingest_corpus.py --force
```

Manual promotion copies a processed Slack inbox file into corpus:

```bash
./bin/imem promote-slack-thread --path company/inbox/slack/C123_1710000000.000000.md
uv run python scripts/ingest_corpus.py --force
```

### Slack Auto-Promotion

Set `PROMOTION_ALLOWED_CHANNELS` to the comma-separated Slack channel IDs where
reaction-based promotion is allowed. In the Slack app config, enable
Event Subscriptions and subscribe to the `reaction_added` event so the listener
can receive promotion reactions.

React with `:memo:` or `:brain:` on an allowed Slack message/thread to promote
it. Promoted corpus files are written under `company/corpus/slack/promoted/`,
with evidence snapshots under `company/evidence/slack/`.

After promotion, reingest the corpus:

```bash
uv run python scripts/ingest_corpus.py --force
```

For a clean Slack ingestion demo:

```bash
./bin/imem reset-demo --clear-audit --clear-slack-inbox
```

Do not add `scripts/slack_listener.py` to OpenClaw's exec allowlist.

## ASUS Run

From OpenClaw, ask:

```text
Check the inbox now and process one new draft.
```

The expected RFP path posts a Slack message with source attribution to
`company/corpus/2023_rfp_postmortem.txt`. The expected silent path processes the draft
with `skipped_no_relevant_memory` and sends no Slack message.

Print the full live checklist any time:

```bash
uv run python scripts/live_handoff.py
```

## ASUS Rerun

Reset demo state:

```bash
./bin/imem reset-demo --clear-audit --clear-chroma
uv run python scripts/ingest_corpus.py --force
uv run python scripts/cosine_sanity.py
```

Create the RFP demo draft:

```bash
uv run python scripts/demo_case.py rfp
```

Create the silent/no-Slack demo draft:

```bash
uv run python scripts/demo_case.py silent
```

For every fresh OpenClaw demo run:

```bash
./bin/imem reset-demo --clear-audit
uv run python scripts/demo_case.py rfp
~/run_openclaw.sh
```

Then ask OpenClaw to check the inbox.

Record a backup `.mp4` or `.mov` under:

```text
demo_artifacts/
```

Final gate:

```bash
uv run python scripts/final_gate.py
```

Do not call the goal complete until that command passes on ASUS.

## ASUS Deploy

Use SSH key auth over Tailscale. Do not store the ASUS login password in this
repo or in a workflow. GitHub Actions auto-deploy is intentionally disabled
because ASUS already has an ASUS webhook script.

One-time ASUS SSH key setup from this Mac:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/asus_deploy
ssh-copy-id -i ~/.ssh/asus_deploy.pub asus@100.68.221.47
tailscale ping 100.68.221.47
ASUS_SSH_KEY=~/.ssh/asus_deploy scripts/deploy_asus.sh
```

The script fetches the target branch on ASUS and checks it out over the old
checkout. It also updates the OpenClaw workspace with `SOUL.md`,
`HEARTBEAT.md`, and the institutional-memory skill. Override `ASUS_USER_HOST`,
`ASUS_TAILSCALE_IP`, `ASUS_REPO`, `ASUS_BRANCH`, `ASUS_SSH_KEY`, or
`OPENCLAW_WORKSPACE` for manual runs if the ASUS checkout or OpenClaw workspace
differs from `~/memory-claw` and `~/.openclaw/workspace`.
