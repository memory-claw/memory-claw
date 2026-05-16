# Institutional Memory Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working OpenClaw agent powered by local Nemotron that monitors `./inbox/`, searches persistent ChromaDB institutional memory, and posts relevant context to Slack.

**Architecture:** OpenClaw controls the workflow and calls one allowlisted local command, `./bin/imem`, through `exec`. `./bin/imem` runs a uv-backed Python CLI that performs deterministic actions: draft discovery, safe file reads, Chroma search, Slack delivery, processed-state writes, audit logging, and demo reset. Nemotron formulates the search query and writes the Slack message; Python tools execute the actions reliably.

**Tech Stack:** OpenClaw, Ollama native provider, `nemotron-3-super:120b`, `qwen3-embedding:8b`, Python 3.12 in this repo unless changed, uv, argparse, ChromaDB, slack-sdk, python-dotenv, pytest.

---

## Current Implementation Status

Local code path is implemented and locally verified. The repository now
contains the `institutional_memory/` package, `./bin/imem` wrapper, corpus,
Chroma ingestion/search, Slack message-file delivery, harness fallback,
OpenClaw prompt files, DGX/OpenClaw setup helpers, readiness gates, audit gates,
final gate blocker reporting, a live handoff checklist, and a NemoClaw bonus
scaffold.
Optional PDF support is also implemented for both corpus ingestion and inbox
draft reading via `pymupdf4llm`; keep the live demo on `.txt` unless the core
path is already clean.
Final gate child commands are time-boxed, so local/DGX-only hangs surface as
explicit timeout blockers.
`scripts/dgx_check.py --skip-model-smoke --skip-backup-video` exists for fast
preflight before models are loaded. Final readiness must run without
`--skip-model-smoke`.
The audit gate now also rejects generic or full-draft-style search queries, so
the live proof must show Nemotron formulated a focused 2-6 word query before
calling Chroma.
It also requires every live tool event in the success and silent-case windows
to be tagged `driver: "openclaw"`; harness-tagged proof is useful fallback
evidence but cannot satisfy the final OpenClaw gate.
`scripts/live_handoff.py` prints the exact ASUS/DGX operator sequence for
preflight, Slack secrets, model bootstrap, OpenClaw success, silent case,
backup video, final gate, and optional NemoClaw proof.
NemoClaw denial probes are implemented as hidden `./bin/imem nemoclaw-probe`
subcommands for `denied-read` and `denied-network`; inside the sandbox they
should return `{"status": "denied", ...}`, while unsandboxed success returns
`unsafe_access_succeeded` and does not prove the bonus.
`scripts/final_gate.py` also runs `scripts/nemoclaw_scaffold_check.py` so local
policy/docs/probe scaffold drift is caught before the live run.

Current local evidence:

- `uv run pytest -q` passes.
- `uv run python scripts/demo_rehearsal.py --skip-ingest` passes with
  `2023_rfp_postmortem.txt` as the top RFP result and `[]` for the clinical
  trial silent query.
- `uv run python scripts/dgx_bootstrap.py --dry-run` prints the expected setup
  sequence.
- `uv run python scripts/nemoclaw_scaffold_check.py` validates that the
  NemoClaw/OpenShell policy scaffold, denial probes, and docs exist. This is
  not live-verified; adapt exact keys on the ASUS/DGX with the event docs
  before claiming bonus track completion.

Live blockers remain and cannot be honestly marked complete from this local
Mac:

- DGX/ASUS hardware must prove `nemotron-3-super:120b` can generate within the
  configured timeouts.
- Slack `.env` must contain a working `SLACK_BOT_TOKEN` and `SLACK_CHANNEL`.
  Optional `SLACK_WEBHOOK_URL` can be used as an emergency delivery fallback,
  but final readiness still requires the bot token.
- OpenClaw success and silent turns must produce `driver: "openclaw"` audit
  proof.
- NemoClaw bonus proof, if attempted, must run on the ASUS/DGX and show real
  allowed demo behavior plus denied filesystem/network attempts in the
  NemoClaw/OpenShell audit trail.
- A real backup video must exist under `demo_artifacts/`.

Do not mark this goal complete until `uv run python scripts/final_gate.py`
passes on the live demo machine.

---

## Current Repo Assumptions

Implementation happens in the current repository root:

```text
/Users/ashwinmurthy/memory-claw
```

Do not create a nested `institutional-memory/` project. Do not run `uv init institutional-memory`.

The existing repo already has a uv project and an older `agent/` scaffold. This plan creates the new production demo package under `institutional_memory/`. The old `agent/` package can remain temporarily, but the final demo path must use `./bin/imem` and `institutional_memory/`.

## Critical Path

```text
Task 1: Project/dependency cleanup
Task 2: CLI hello + bin/imem wrapper
Task 3: OpenClaw can call a production ./bin/imem command
Task 4: State, audit, and path safety
Task 5: Corpus ingestion + Chroma cosine sanity check
Task 6: Search-memory CLI returns demo source
Task 7: Slack + message-file delivery
Task 8: Harness end-to-end fallback
Task 9: SOUL.md, HEARTBEAT.md, SKILL.md
Task 10: OpenClaw heartbeat end-to-end demo
```

Four-person split:

- Person A: OpenClaw config, exec allowlist, production command smoke test, final OpenClaw loop.
- Person B: retrieval, ingestion, Chroma, threshold calibration.
- Person C: CLI, state, audit log, path validation, Slack, harness.
- Person D: demo corpus, SOUL.md, HEARTBEAT.md, SKILL.md, demo script, backup video.

B, C, and D start immediately. Only OpenClaw integration waits on A's smoke test.

---

### Task 1: Project Root And Dependencies

**Files:**
- Modify: `pyproject.toml`
- Create: `.env.example`
- Modify: `.gitignore`
- Create: `institutional_memory/__init__.py`
- Create: `bin/.gitkeep`
- Create: `corpus/.gitkeep`
- Create: `inbox/.gitkeep`
- Create: `.runtime/.gitkeep`

- [ ] **Step 1: Update dependencies and scripts**

Replace the project dependency block in `pyproject.toml` so the demo path uses the required packages and exposes the `imem` console command. Keep `requires-python` as `>=3.12` unless the team intentionally switches the repo to 3.11 and regenerates the lock.

```toml
[project]
name = "institutional-memory-engine"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "chromadb>=1.5.9",
    "ollama>=0.3.0",
    "pymupdf>=1.27.2.3",
    "pymupdf4llm>=1.27.2.3",
    "python-dotenv>=1.2.2",
    "slack-sdk>=3.27.0",
]

[project.scripts]
imem = "institutional_memory.cli:main"

[dependency-groups]
dev = [
    "pytest>=9.0.3",
]

[tool.pytest.ini_options]
pythonpath = ["."]
```

Remove old demo-only dependencies if no current code still needs them: `openai`, `pypdf`, `requests`, `sentence-transformers`, and `watchdog`.

- [ ] **Step 2: Sync dependencies**

Run:

```bash
uv sync
```

Expected: dependency resolution succeeds and `uv.lock` updates.

- [ ] **Step 3: Create required directories**

Create directories with normal filesystem commands or patches:

```text
institutional_memory/
bin/
corpus/
inbox/
processed/
.runtime/
scripts/
skills/institutional-memory/
tests/
```

Add `.gitkeep` files to empty directories that should exist in git.

- [ ] **Step 4: Add environment template**

Create `.env.example`:

```text
OLLAMA_BASE_URL=http://127.0.0.1:11434
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL=#institutional-memory
SLACK_WEBHOOK_URL=
```

- [ ] **Step 5: Update gitignore**

Ensure `.gitignore` includes:

```text
.env
.venv/
__pycache__/
*.pyc
*.egg-info/
dist/
chroma_db/
.runtime/*
!.runtime/.gitkeep
audit_log.jsonl
processed_drafts.json
ingested_files.json
```

- [ ] **Step 6: Commit checkpoint**

Run:

```bash
uv run pytest
git status --short
```

Expected: pytest may still run only old tests, but it must not fail from packaging/import errors.

Commit:

```bash
git add pyproject.toml uv.lock .env.example .gitignore institutional_memory bin corpus inbox .runtime scripts skills tests
git commit -m "chore: set up institutional memory project structure"
```

---

### Task 2: CLI Skeleton And Wrapper

**Files:**
- Create: `bin/imem`
- Create: `institutional_memory/cli.py`
- Create: `tests/test_cli_json.py`

- [ ] **Step 1: Create the wrapper**

Create `bin/imem` with:

```sh
#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec uv run imem "$@"
```

Make it executable:

```bash
chmod +x bin/imem
```

- [ ] **Step 2: Create the initial CLI**

Create `institutional_memory/cli.py`:

```python
"""Institutional Memory Engine CLI."""

from __future__ import annotations

import argparse
import json
from typing import Any


def emit(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False))


def cmd_hello(_: argparse.Namespace) -> int:
    emit({"status": "ok", "message": "hello from Python"})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="imem", description="Institutional Memory Engine")
    sub = parser.add_subparsers(dest="command", required=True)
    hello = sub.add_parser("hello", help="Smoke test")
    hello.set_defaults(func=cmd_hello)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Add CLI JSON smoke test**

Create `tests/test_cli_json.py`:

```python
import json
import subprocess


def test_hello_outputs_valid_json():
    result = subprocess.run(
        ["./bin/imem", "hello"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload == {"status": "ok", "message": "hello from Python"}
```

- [ ] **Step 4: Verify locally**

Run:

```bash
./bin/imem hello
uv run pytest tests/test_cli_json.py -v
```

Expected:

```json
{"status": "ok", "message": "hello from Python"}
```

and pytest passes.

- [ ] **Step 5: Commit checkpoint**

```bash
git add bin/imem institutional_memory/cli.py tests/test_cli_json.py
git commit -m "feat: add imem CLI smoke command"
```

---

### Task 3: OpenClaw Exec Smoke Test

**Files:**
- Create: `skills/institutional-memory/SKILL.md`
- Create: `SOUL.md`
- Create: `HEARTBEAT.md`

- [ ] **Step 1: Create temporary skill docs for an exec smoke test**

Create `skills/institutional-memory/SKILL.md`:

```markdown
---
name: institutional-memory
description: Institutional memory agent tools.
---

# Institutional Memory Tools

## list-new-drafts

Use this tool to verify the local Python tool layer is callable through OpenClaw.

Command: `./bin/imem list-new-drafts`

Expected output: a JSON array such as `[]` or `["inbox/new_rfp_draft.txt"]`.
```

- [ ] **Step 2: Create placeholder SOUL.md and HEARTBEAT.md**

Create `SOUL.md`:

```markdown
# Institutional Memory Agent

You are an institutional memory agent. For now, use `list-new-drafts` to verify
the local Python tool layer is working through OpenClaw.
```

Create `HEARTBEAT.md`:

```markdown
# Heartbeat

For now, do not take autonomous action. The heartbeat behavior will be enabled
after the full tool layer works.
```

- [ ] **Step 3: Configure OpenClaw**

Use OpenClaw's native Ollama provider:

```text
provider: ollama
model: ollama/nemotron-3-super:120b
baseUrl: http://127.0.0.1:11434
```

Do not use `http://127.0.0.1:11434/v1` for OpenClaw.

Allow tools:

```text
exec
```

Set exec policy for final posture:

```text
security=allowlist
ask=off
strictInlineEval=true
```

Allow only the absolute path to this repo's wrapper:

```text
/Users/ashwinmurthy/memory-claw/bin/imem
```

The exact allowlist file and regex are OpenClaw-version-sensitive. Smoke test the real behavior instead of trusting the regex. Do not allowlist `python3`, `uv`, `bash`, or arbitrary shell commands for the final demo.

- [ ] **Step 4: Run OpenClaw smoke test**

Ask OpenClaw:

```text
Call list-new-drafts and tell me exactly what JSON it returned.
```

Pass criteria:

- No approval prompt appears.
- OpenClaw runs `./bin/imem list-new-drafts`.
- OpenClaw receives a JSON array.
- Nemotron describes that JSON result correctly.

If it fails, debug in this order:

```text
1. Is OpenClaw using native Ollama, not /v1?
2. Is exec in tools.allow?
3. Is the absolute bin/imem path allowlisted?
4. Is bin/imem executable?
5. Does bin/imem cd to repo root?
6. Can OpenClaw find uv in its PATH or configured pathPrepend?
```

- [ ] **Step 5: Commit checkpoint**

```bash
git add SOUL.md HEARTBEAT.md skills/institutional-memory/SKILL.md
git commit -m "docs: add OpenClaw exec smoke test instructions"
```

---

### Task 4: Config, Audit, State, And Path Safety

**Files:**
- Create: `institutional_memory/config.py`
- Create: `institutional_memory/audit.py`
- Create: `institutional_memory/state.py`
- Create: `institutional_memory/paths.py`
- Modify: `institutional_memory/cli.py`
- Create: `tests/test_paths.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Add config module**

Create `institutional_memory/config.py`:

```python
"""Central configuration for the institutional memory demo."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
load_dotenv(PROJECT_ROOT / ".env", override=True)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
EMBEDDING_MODEL = "qwen3-embedding:8b"
LLM_MODEL = "nemotron-3-super:120b"

CHROMA_PATH = PROJECT_ROOT / "chroma_db"
CHROMA_COLLECTION = "org_memory"

RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.75"))
TOP_K = int(os.getenv("TOP_K", "5"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

INBOX_PATH = PROJECT_ROOT / "inbox"
CORPUS_PATH = PROJECT_ROOT / "corpus"
RUNTIME_PATH = PROJECT_ROOT / ".runtime"
PROCESSED_REGISTRY = PROJECT_ROOT / "processed_drafts.json"
INGESTED_REGISTRY = PROJECT_ROOT / "ingested_files.json"
AUDIT_LOG = PROJECT_ROOT / "audit_log.jsonl"

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#institutional-memory")
```

No printing or process exits at import time.

- [ ] **Step 2: Add audit logger**

Create `institutional_memory/audit.py`:

```python
"""Append structured events to audit_log.jsonl."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from institutional_memory.config import AUDIT_LOG


def log_event(event_type: str, **fields: Any) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        **fields,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

- [ ] **Step 3: Add processed registry**

Create `institutional_memory/state.py`:

```python
"""Processed draft registry."""

from __future__ import annotations

import json
from pathlib import Path

from institutional_memory.config import PROCESSED_REGISTRY


def load_processed() -> list[str]:
    if not Path(PROCESSED_REGISTRY).exists():
        return []
    return json.loads(Path(PROCESSED_REGISTRY).read_text(encoding="utf-8"))


def mark_as_processed(path: str) -> None:
    processed = load_processed()
    if path not in processed:
        processed.append(path)
        Path(PROCESSED_REGISTRY).write_text(
            json.dumps(processed, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def reset_processed() -> None:
    Path(PROCESSED_REGISTRY).write_text("[]", encoding="utf-8")
```

- [ ] **Step 4: Add safe path utilities**

Create `institutional_memory/paths.py`:

```python
"""Safe path validation for OpenClaw-facing commands."""

from __future__ import annotations

from pathlib import Path

from institutional_memory.config import INBOX_PATH, PROJECT_ROOT, RUNTIME_PATH


class PathNotAllowedError(ValueError):
    pass


def _resolve_under_project(raw: str) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (PROJECT_ROOT / candidate).resolve()
    return resolved


def _ensure_under(candidate: Path, allowed_root: Path, raw: str) -> Path:
    allowed = allowed_root.resolve()
    if candidate != allowed and allowed not in candidate.parents:
        raise PathNotAllowedError(f"Path '{raw}' is outside {allowed_root.relative_to(PROJECT_ROOT)}")
    return candidate


def safe_inbox_path(raw: str) -> Path:
    candidate = _ensure_under(_resolve_under_project(raw), INBOX_PATH, raw)
    if candidate.suffix not in {".txt", ".md", ".pdf"}:
        raise PathNotAllowedError("Only .txt, .md, and .pdf files are allowed")
    return candidate


def safe_runtime_path(raw: str) -> Path:
    return _ensure_under(_resolve_under_project(raw), RUNTIME_PATH, raw)
```

- [ ] **Step 5: Add tests**

Create `tests/test_paths.py`:

```python
from pathlib import Path

import pytest

from institutional_memory.config import PROJECT_ROOT
from institutional_memory.paths import PathNotAllowedError, safe_inbox_path, safe_runtime_path


def test_safe_inbox_allows_txt_under_inbox():
    assert safe_inbox_path("inbox/foo.txt") == (PROJECT_ROOT / "inbox/foo.txt").resolve()


def test_safe_inbox_blocks_traversal():
    with pytest.raises(PathNotAllowedError):
        safe_inbox_path("../etc/passwd")


def test_safe_inbox_allows_pdf_under_inbox():
    assert safe_inbox_path("inbox/doc.pdf") == (PROJECT_ROOT / "inbox/doc.pdf").resolve()


def test_safe_runtime_allows_runtime_file():
    assert safe_runtime_path(".runtime/slack_message.txt") == (
        PROJECT_ROOT / ".runtime/slack_message.txt"
    ).resolve()


def test_safe_runtime_blocks_inbox_file():
    with pytest.raises(PathNotAllowedError):
        safe_runtime_path("inbox/foo.txt")
```

Create `tests/test_state.py`:

```python
from pathlib import Path

from institutional_memory.config import PROCESSED_REGISTRY
from institutional_memory.state import load_processed, mark_as_processed, reset_processed


def test_mark_as_processed_writes_once():
    try:
        reset_processed()
        mark_as_processed("inbox/foo.txt")
        mark_as_processed("inbox/foo.txt")
        assert load_processed() == ["inbox/foo.txt"]
    finally:
        Path(PROCESSED_REGISTRY).unlink(missing_ok=True)
```

- [ ] **Step 6: Verify**

Run:

```bash
uv run pytest tests/test_paths.py tests/test_state.py -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit checkpoint**

```bash
git add institutional_memory/config.py institutional_memory/audit.py institutional_memory/state.py institutional_memory/paths.py tests/test_paths.py tests/test_state.py
git commit -m "feat: add config state audit and safe path validation"
```

---

### Task 5: Draft Tools And CLI Subcommands

**Files:**
- Create: `institutional_memory/drafts.py`
- Modify: `institutional_memory/cli.py`
- Modify: `tests/test_cli_json.py`

- [ ] **Step 1: Add draft discovery module**

Create `institutional_memory/drafts.py`:

```python
"""Inbox draft discovery and reading."""

from __future__ import annotations

from institutional_memory.config import INBOX_PATH, PROJECT_ROOT
from institutional_memory.paths import safe_inbox_path
from institutional_memory.state import load_processed


def list_new_drafts() -> list[str]:
    if not INBOX_PATH.exists():
        return []
    processed = set(load_processed())
    drafts: list[str] = []
    for path in sorted(INBOX_PATH.iterdir()):
        if path.name == ".gitkeep" or path.suffix not in {".txt", ".md", ".pdf"}:
            continue
        rel = str(path.resolve().relative_to(PROJECT_ROOT))
        if rel not in processed:
            drafts.append(rel)
    return drafts


def read_draft(path: str) -> dict[str, str]:
    safe_path = safe_inbox_path(path)
    return {"path": str(safe_path.relative_to(PROJECT_ROOT)), "text": load_document_text(safe_path)}
```

- [ ] **Step 2: Extend CLI with list/read/mark/reset placeholders**

Modify `institutional_memory/cli.py` to add subcommands:

```text
list-new-drafts
read-draft --path <path>
mark-processed --path <path> --status <status> --reason <reason> [--query] [--top-score] [--source]
reset-demo [--clear-audit] [--clear-chroma]
```

Implementation requirements:

- `list-new-drafts` emits a JSON array and logs `draft_listed`.
- `read-draft` emits `{"path": ..., "text": ...}` or `{"error": ...}` and logs `draft_read`.
- `mark-processed` accepts statuses `sent`, `skipped_no_relevant_memory`, `search_failed`, `slack_failed`, `read_failed`, `tool_error`; it writes `processed_drafts.json` and logs `processed`.
- `reset-demo` clears `.runtime/*`, resets `processed_drafts.json`, optionally clears `audit_log.jsonl`, optionally deletes `chroma_db/`, and logs `demo_reset` with a timestamp unless `--clear-audit` is meant to leave a fully empty log.
- All JSON uses `ensure_ascii=False`.

- [ ] **Step 3: Add CLI tests**

Extend `tests/test_cli_json.py` with tests that:

- `./bin/imem list-new-drafts` returns valid JSON.
- `./bin/imem read-draft --path ../etc/passwd` returns valid JSON with an `error`.
- `./bin/imem reset-demo --clear-audit` returns valid JSON.

- [ ] **Step 4: Verify**

Run:

```bash
./bin/imem reset-demo --clear-audit
./bin/imem list-new-drafts
./bin/imem read-draft --path ../etc/passwd
uv run pytest tests/test_cli_json.py -v
```

Expected: no tracebacks, all stdout is parseable JSON, path traversal is blocked.

- [ ] **Step 5: Commit checkpoint**

```bash
git add institutional_memory/drafts.py institutional_memory/cli.py tests/test_cli_json.py
git commit -m "feat: add draft state CLI commands"
```

---

### Task 6: Corpus And Ingestion

**Files:**
- Create: `institutional_memory/ingest.py`
- Create: `scripts/ingest_corpus.py`
- Create: `tests/test_chunking.py` or update existing test
- Create/Modify: `corpus/*.txt`
- Create/Modify: `inbox/new_rfp_draft.txt`

- [ ] **Step 1: Add demo corpus**

Create at least 10 `.txt` files under `corpus/`. Required file:

```text
corpus/2023_rfp_postmortem.txt
```

It must mention:

```text
liability caps in clause 7.4
indemnification
lost the Meridian bid in 2023
```

Create at least 9 unrelated docs covering HR, office planning, marketing, roadmap, security, board notes, and engineering retros.

Create the trigger draft:

```text
inbox/new_rfp_draft.txt
```

It must mention a new RFP draft, indemnification provisions, liability framework, and clause 7.4.

- [ ] **Step 2: Implement chunking and embedding ingestion**

Create `institutional_memory/ingest.py` with:

- `chunk_text(text: str, source: str) -> list[dict]`
- `embed_text(text: str) -> list[float]`
- `get_chroma_collection()`
- `ingest_folder(folder: Path, force: bool = False)`

Requirements:

- chunk size 400 words, overlap 50 words
- skip tiny trailing chunks below 10 words
- use `ollama.Client(host=OLLAMA_BASE_URL).embed(model=EMBEDDING_MODEL, input=text)`
- use persistent Chroma client at `CHROMA_PATH`
- create collection with cosine distance:

```python
client.get_or_create_collection(
    name=CHROMA_COLLECTION,
    configuration={"hnsw": {"space": "cosine"}},
)
```

- normal ingest skips files in `ingested_files.json`
- `force=True` deletes `chroma_db/` and `ingested_files.json` before ingesting; do not call `collection.add` over existing duplicate IDs

- [ ] **Step 3: Add ingest script**

Create `scripts/ingest_corpus.py`:

```text
uv run python scripts/ingest_corpus.py
uv run python scripts/ingest_corpus.py --force
```

It should call `ingest_folder(CORPUS_PATH, force=args.force)` and print file/chunk counts.

- [ ] **Step 4: Add chunking tests**

Ensure `tests/test_chunking.py` verifies:

- overlap is present between adjacent chunks
- tiny trailing chunks are skipped
- chunk IDs include the source and word offset or index

- [ ] **Step 5: Verify ingestion**

Run:

```bash
ollama list
uv run python scripts/ingest_corpus.py --force
```

Expected: corpus files ingest, chunks are stored, no duplicate ID errors.

- [ ] **Step 6: Verify cosine sanity**

Run a script or one-liner that embeds a known text and queries the same embedding. Expected score: approximately `1.0`.

If score is not close to `1.0`, delete `chroma_db/`, confirm cosine configuration, and re-ingest.

- [ ] **Step 7: Commit checkpoint**

```bash
git add institutional_memory/ingest.py scripts/ingest_corpus.py tests/test_chunking.py corpus inbox
git commit -m "feat: add corpus ingestion with Chroma cosine embeddings"
```

---

### Task 7: Search-Memory

**Files:**
- Create: `institutional_memory/search.py`
- Modify: `institutional_memory/cli.py`

- [ ] **Step 1: Implement search module**

Create `institutional_memory/search.py` with:

- `embed_query(query: str) -> list[float]`
- `search_memory(query: str, threshold: float = RELEVANCE_THRESHOLD, top_k: int = TOP_K, draft_text: str | None = None) -> list[dict]`

Requirements:

- query path embeds the agent-formulated query
- optional `draft_text` is debug/harness only
- Chroma query includes documents, metadatas, distances
- convert score as `round(1.0 - distance, 4)`
- filter by threshold
- dedupe by source, keeping highest score
- sort descending by score

- [ ] **Step 2: Add CLI subcommand**

Add:

```bash
./bin/imem search-memory --query "RFP liability indemnification clause"
./bin/imem search-memory --query "RFP liability" --draft-path inbox/new_rfp_draft.txt
```

OpenClaw-facing docs must only mention `--query`. `--draft-path` is debug/harness only.

CLI behavior:

- success with hits emits JSON array
- no hits emits `[]`
- search failure emits `{"error": "search failed: ..."}`
- every search logs `memory_searched`
- failures log `tool_error` or `memory_searched` with error

- [ ] **Step 3: Verify search**

Run:

```bash
./bin/imem search-memory --query "RFP liability indemnification clause"
```

Expected: top result source is `2023_rfp_postmortem.txt`.

Run:

```bash
./bin/imem search-memory --query "cafeteria seating office furniture"
```

Expected: `[]` or no RFP result above threshold. If it returns RFP above threshold, calibrate threshold after printing raw scores.

- [ ] **Step 4: Commit checkpoint**

```bash
git add institutional_memory/search.py institutional_memory/cli.py
git commit -m "feat: add search-memory CLI backed by Chroma"
```

---

### Task 8: Slack Delivery And Runtime Message File

**Files:**
- Create: `institutional_memory/slack.py`
- Modify: `institutional_memory/cli.py`

- [ ] **Step 1: Implement Slack module**

Create `institutional_memory/slack.py`:

- read Slack token from `SLACK_BOT_TOKEN`
- default channel from `SLACK_CHANNEL`
- optionally fall back to `SLACK_WEBHOOK_URL` if the bot token is missing or
  rejected; do not treat this as a substitute for final bot-token readiness
- `send_slack_message(channel: str | None, message_file: str | None, message: str | None) -> dict`
- validate `message_file` with `safe_runtime_path`
- return `{"status": "sent", "channel": channel}` on success
- return `{"status": "slack_failed", "error": "..."}`

- [ ] **Step 2: Add CLI subcommand**

Add:

```bash
./bin/imem send-slack --message-file .runtime/slack_message.txt
./bin/imem send-slack --message "short manual test"
```

`--channel` is optional and defaults to `SLACK_CHANNEL`.

CLI logs `slack_sent`.

- [ ] **Step 3: Verify safe file path**

Run:

```bash
mkdir -p .runtime
printf 'Test from imem message file' > .runtime/slack_message.txt
./bin/imem send-slack --message-file .runtime/slack_message.txt
```

Expected: Slack message posts, JSON status is `sent`.

Run:

```bash
./bin/imem send-slack --message-file inbox/new_rfp_draft.txt
```

Expected: JSON status is `slack_failed` with a path safety error.

- [ ] **Step 4: Commit checkpoint**

```bash
git add institutional_memory/slack.py institutional_memory/cli.py
git commit -m "feat: add Slack delivery through runtime message file"
```

---

### Task 9: Fallback Harness

**Files:**
- Create: `scripts/harness.py`

- [ ] **Step 1: Implement harness**

Create `scripts/harness.py` that:

- calls `./bin/imem list-new-drafts`
- processes only the first draft
- calls `read-draft`
- calls `search-memory --query <query> --draft-path <path>`
- uses local `ollama.Client(host=OLLAMA_BASE_URL).chat(model=LLM_MODEL, ...)` to have Nemotron write the Slack message
- writes message to `.runtime/slack_message.txt`
- calls `send-slack --message-file .runtime/slack_message.txt`
- calls `mark-processed` with final status and reason

The harness exists only as emergency backup and debugging. Do not call it the minimum acceptable judged demo.

- [ ] **Step 2: Add dry-run mode**

`uv run python scripts/harness.py --dry-run` should:

- execute through search
- generate and print the Nemotron message
- write audit events
- not post to Slack

- [ ] **Step 3: Verify harness**

Run:

```bash
./bin/imem reset-demo --clear-audit
uv run python scripts/harness.py --dry-run
uv run python scripts/harness.py
tail -20 audit_log.jsonl
```

Expected:

- dry run completes
- live run posts to Slack
- audit includes `draft_listed`, `draft_read`, `memory_searched`, `slack_sent`, `processed`

- [ ] **Step 4: Commit checkpoint**

```bash
git add scripts/harness.py
git commit -m "feat: add Nemotron fallback harness"
```

---

### Task 10: Final OpenClaw Prompt Files

**Files:**
- Modify: `SOUL.md`
- Modify: `HEARTBEAT.md`
- Modify: `skills/institutional-memory/SKILL.md`

- [ ] **Step 1: Rewrite SOUL.md**

`SOUL.md` must instruct the agent to:

- call `list-new-drafts`
- stop if result is `[]`
- process only the first path
- call `read-draft`
- formulate a focused 2-6 word query
- call `search-memory --query "<query>"`
- on `[]`, mark `skipped_no_relevant_memory`
- on error, mark `search_failed`, `read_failed`, or `tool_error`
- if results exist, write a 2-3 sentence Slack message as a knowledgeable colleague
- include source filename
- avoid "detected", "triggered", "alert", "notification", "As an AI"
- write the message to `.runtime/slack_message.txt` using OpenClaw `write`
- call `send-slack --message-file .runtime/slack_message.txt`
- always call `mark-processed` as final action

- [ ] **Step 2: Rewrite HEARTBEAT.md**

Set demo heartbeat to 1-2 minutes and instruct one draft per turn.

- [ ] **Step 3: Rewrite SKILL.md**

Document only these OpenClaw-facing commands:

```bash
./bin/imem list-new-drafts
./bin/imem read-draft --path <path>
./bin/imem search-memory --query "<query>"
./bin/imem send-slack --message-file .runtime/slack_message.txt
./bin/imem mark-processed --path <path> --status <status> --reason "<reason>" [--query "<query>"] [--top-score <score>] [--source "<source>"]
```

Do not document `--draft-path`.

- [ ] **Step 4: Commit checkpoint**

```bash
git add SOUL.md HEARTBEAT.md skills/institutional-memory/SKILL.md
git commit -m "docs: define OpenClaw institutional memory agent behavior"
```

---

### Task 11: OpenClaw End-To-End Demo

**Files:**
- No code files unless prompt/config fixes are needed.

- [ ] **Step 1: Reset and ingest**

Run:

```bash
./bin/imem reset-demo --clear-audit
uv run python scripts/ingest_corpus.py --force
./bin/imem search-memory --query "RFP liability indemnification clause"
```

Expected: top result is `2023_rfp_postmortem.txt`.

- [ ] **Step 2: Test manual OpenClaw turn**

Ask OpenClaw:

```text
Check the inbox now and process one new draft.
```

Watch:

```bash
tail -f audit_log.jsonl
```

Expected sequence:

```text
draft_listed
draft_read
memory_searched
slack_sent
processed
```

Slack should receive a human-sounding message with source attribution.

- [ ] **Step 3: Test silent case**

Run:

```bash
./bin/imem reset-demo
cat > inbox/000_silent_clinical_trial_protocol.txt <<'EOF'
Clinical Trial Protocol Draft

Participants will receive a randomized dosage schedule for a dermatology study.
The protocol defines consent language, adverse event reporting, and placebo
control procedures for a university research board review.
EOF
```

Ask OpenClaw to check the inbox.

Expected: `skipped_no_relevant_memory`, no Slack message.

- [ ] **Step 4: Test heartbeat**

Reset demo state, place only the RFP draft in inbox, wait for heartbeat.

Expected: Slack message appears without manual triggering.

- [ ] **Step 5: Commit checkpoint**

If only docs/config changed:

```bash
git add SOUL.md HEARTBEAT.md skills/institutional-memory/SKILL.md
git commit -m "test: verify OpenClaw end-to-end agent loop"
```

---

### Task 12: Demo Prep

**Files:**
- Modify: `institutional_memory/config.py` if threshold is tuned
- Modify: `SOUL.md` if message tone is tuned

- [ ] **Step 1: Calibrate threshold**

Temporarily run search with threshold `0.0` from a Python one-liner or env override. Print sources and scores. Set `RELEVANCE_THRESHOLD` or `.env` value just above the noise cluster.

- [ ] **Step 2: Rehearse twice**

For each rehearsal:

```bash
./bin/imem reset-demo --clear-audit
tail -f audit_log.jsonl
```

Drop or restore `inbox/new_rfp_draft.txt`, wait for heartbeat or manually trigger OpenClaw.

Pass criteria:

- completes within 90 seconds after trigger
- Slack message appears
- audit log shows all event types
- message has source attribution
- unrelated file stays silent

- [ ] **Step 3: Record backup video**

Record:

- OpenClaw running
- audit log tail
- inbox file drop
- Slack message appearing

- [ ] **Step 4: Final verification**

Run:

```bash
uv run pytest
./bin/imem hello
./bin/imem list-new-drafts
./bin/imem search-memory --query "RFP liability indemnification clause"
git status --short
```

Expected: tests pass; CLI works; no `.env`, Chroma DB, audit log, or processed registry staged.

- [ ] **Step 5: Commit checkpoint**

```bash
git add institutional_memory/config.py SOUL.md HEARTBEAT.md skills/institutional-memory/SKILL.md corpus inbox tests
git commit -m "chore: prepare final hackathon demo"
```

---

## Verification Checklist

- [ ] `ollama list` shows `nemotron-3-super:120b`
- [ ] `ollama list` shows `qwen3-embedding:8b`
- [ ] `uv sync` succeeds
- [ ] `uv run pytest` passes
- [ ] `./bin/imem hello` prints valid JSON
- [ ] OpenClaw can call `./bin/imem list-new-drafts`
- [ ] Chroma self-query score is approximately `1.0`
- [ ] `search-memory` returns `2023_rfp_postmortem.txt` for the demo query
- [ ] `send-slack --message-file .runtime/slack_message.txt` posts to Slack
- [ ] path traversal attempts return JSON errors
- [ ] `scripts/harness.py --dry-run` works
- [ ] `scripts/harness.py` sends Slack
- [ ] OpenClaw manual turn sends Slack
- [ ] OpenClaw heartbeat sends Slack
- [ ] silent unrelated file produces `skipped_no_relevant_memory`
- [ ] backup video recorded
- [ ] `.env` is not committed

## Cut Decisions

- If OpenClaw smoke test is still failing after 90 minutes, B/C/D continue local tool layer and harness; A keeps debugging OpenClaw.
- If retrieval is weak, tune threshold and use `--draft-path` only in harness/debug mode.
- If OpenClaw tool order is wrong after 45 minutes of SOUL.md tuning, use harness as emergency backup.
- PDF support is implemented as stretch coverage. Do not spend demo-prep time
  on PDF-specific tuning unless the full OpenClaw demo is already solid.
- MCP, native JS plugin, multiple Slack channels, and Slack blocks are cut.
- NemoClaw runtime proof is cut unless the core demo has passed two full
  rehearsals. The local scaffold can be kept because it does not risk the core
  path.

## Emergency Backup Wording

Do not say harness is the minimum acceptable demo. Say:

```text
The OpenClaw agent normally orchestrates this same allowlisted tool layer. If the live runtime fails, this harness demonstrates the exact deterministic tools, persistent memory, local Nemotron message generation, Slack action, and audit trail that OpenClaw drives.
```
