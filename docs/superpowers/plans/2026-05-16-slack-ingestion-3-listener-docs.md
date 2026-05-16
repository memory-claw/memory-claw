# Slack Ingestion Listener And Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the long-running Socket Mode listener, optional ASUS readiness checks, docs, and final handoff for Slack ingestion.

**Architecture:** This branch builds on the sync/CLI branch. The listener runs outside OpenClaw and calls `handle_message_event()` from `institutional_memory.slack_ingest`. OpenClaw still only calls existing one-shot `./bin/imem` commands.

**Tech Stack:** Python 3.12+, `slack-sdk` Socket Mode, pytest, README handoff docs, ASUS manual verification.

---

## Branch

- Branch: `codex/slack-ingestion-listener-docs`
- Base: `codex/slack-ingestion-sync-cli` after it is pushed or merged.
- Merge third.
- Owned files: `scripts/slack_listener.py`, `scripts/dgx_check.py`, `tests/test_dgx_check.py`, `README.md`, `tests/test_readme_handoff.py`.
- Do not edit `institutional_memory/cli.py` or `institutional_memory/slack_ingest.py`; branch 2 owns those.

---

### Task 1: Socket Mode Listener

- [ ] **Step 1: Confirm branch 2 contract exists**

Run:

```bash
uv run pytest tests/test_slack_ingest.py::test_handle_socket_event_writes_inbox_thread -q
```

Expected: pass. If this fails, rebase onto the latest `codex/slack-ingestion-sync-cli` branch before continuing.

- [ ] **Step 2: Create listener script**

Create `scripts/slack_listener.py`:

```python
"""Long-running Slack Socket Mode listener.

Run outside OpenClaw:
    uv run python scripts/slack_listener.py
"""

from __future__ import annotations

import json
import sys
from threading import Event

from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from institutional_memory.audit import log_event
from institutional_memory.config import SLACK_APP_TOKEN, SLACK_BOT_TOKEN
from institutional_memory.slack_ingest import handle_message_event


def process(client: SocketModeClient, request: SocketModeRequest) -> None:
    if request.type == "events_api":
        client.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))
        event = request.payload.get("event", {})
        try:
            result = handle_message_event(event, client=WebClient(token=SLACK_BOT_TOKEN))
        except Exception as exc:
            result = {"status": "error", "error": str(exc)}
        log_event("slack_event_ingested", **result)
        print(json.dumps(result, ensure_ascii=False), flush=True)


def main() -> int:
    if not SLACK_APP_TOKEN:
        print(json.dumps({"status": "error", "error": "SLACK_APP_TOKEN missing"}), file=sys.stderr)
        return 1
    if not SLACK_BOT_TOKEN:
        print(json.dumps({"status": "error", "error": "SLACK_BOT_TOKEN missing"}), file=sys.stderr)
        return 1
    client = SocketModeClient(app_token=SLACK_APP_TOKEN, web_client=WebClient(token=SLACK_BOT_TOKEN))
    client.socket_mode_request_listeners.append(process)
    client.connect()
    print(json.dumps({"status": "listening"}), flush=True)
    Event().wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/test_slack_ingest.py -q
git add scripts/slack_listener.py
git commit -m "feat: add Slack Socket Mode listener"
```

---

### Task 2: Optional DGX Slack Ingestion Check

- [ ] **Step 1: Write failing readiness test**

Add to `tests/test_dgx_check.py`:

```python
def test_slack_ingestion_blockers_require_app_token(monkeypatch):
    import scripts.dgx_check as dgx_check

    monkeypatch.delenv("SLACK_APP_TOKEN", raising=False)

    assert dgx_check.slack_ingestion_blockers() == ["SLACK_APP_TOKEN missing"]
```

- [ ] **Step 2: Implement readiness helper and flag**

In `scripts/dgx_check.py`, add:

```python
def slack_ingestion_blockers(app_token: str | None = None) -> list[str]:
    if app_token is None:
        app_token = os.getenv("SLACK_APP_TOKEN")
    if not app_token:
        return ["SLACK_APP_TOKEN missing"]
    if app_token == "xapp-your-token-here":
        return ["SLACK_APP_TOKEN is still the .env.example placeholder"]
    return []
```

Add parser flag:

```python
    parser.add_argument("--check-slack-ingestion", action="store_true")
```

After `blockers.extend(slack_secret_blockers())`, add:

```python
    if args.check_slack_ingestion:
        blockers.extend(slack_ingestion_blockers())
```

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/test_dgx_check.py -q
git add scripts/dgx_check.py tests/test_dgx_check.py
git commit -m "feat: add optional Slack ingestion readiness check"
```

---

### Task 3: README Handoff

- [ ] **Step 1: Write failing README test**

Add to `tests/test_readme_handoff.py`:

```python
def test_readme_documents_slack_ingestion():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "SLACK_APP_TOKEN" in readme
    assert "uv run python scripts/slack_listener.py" in readme
    assert "./bin/imem sync-slack --mode inbox" in readme
    assert "./bin/imem sync-slack --mode corpus" in readme
    assert "./bin/imem promote-slack-thread" in readme
    assert "uv run python scripts/ingest_corpus.py --force" in readme
    assert "--clear-slack-inbox" in readme
```

- [ ] **Step 2: Update README**

Add this section after `## Slack Behavior`:

````markdown
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
./bin/imem promote-slack-thread --path inbox/slack/C123_1710000000.000000.md
uv run python scripts/ingest_corpus.py --force
```

For a clean Slack ingestion demo:

```bash
./bin/imem reset-demo --clear-audit --clear-slack-inbox
```

Do not add `scripts/slack_listener.py` to OpenClaw's exec allowlist.
````

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/test_readme_handoff.py -q
git add README.md tests/test_readme_handoff.py
git commit -m "docs: document Slack ingestion handoff"
```

---

### Task 4: ASUS Manual Verification

- [ ] **Step 1: Pull merged stack on ASUS**

```bash
cd ~/memory-claw
git pull origin main
export PATH=$HOME/.local/bin:$PATH
uv sync
```

Expected: checkout has Slack ingestion files.

- [ ] **Step 2: Configure ASUS `.env`**

```text
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_CHANNEL=#institutional-memory
```

- [ ] **Step 3: Run readiness check**

```bash
uv run python scripts/dgx_check.py --skip-backup-video --check-slack-ingestion
```

Expected: no Slack ingestion blockers.

- [ ] **Step 4: Run listener manually**

```bash
uv run python scripts/slack_listener.py
```

Expected stdout:

```json
{"status": "listening"}
```

- [ ] **Step 5: Send Slack test and confirm inbox**

Send this in the configured Slack channel:

```text
Do we have old NHS liability cap precedent?
```

Then run:

```bash
./bin/imem list-new-drafts
```

Expected: JSON array includes `inbox/slack/<channel>_<thread_ts>.md`.

- [ ] **Step 6: Promote one useful thread**

```bash
./bin/imem promote-slack-thread --path inbox/slack/<channel>_<thread_ts>.md
uv run python scripts/ingest_corpus.py --force
```

Expected: copied file exists in `corpus/slack/` and becomes searchable after ingest.

- [ ] **Step 7: Push branch**

```bash
git push -u origin codex/slack-ingestion-listener-docs
```

Expected: branch pushed and ready to merge after sync/CLI.
