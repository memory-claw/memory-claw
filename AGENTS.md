# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Institutional Memory Engine — a RAG pipeline for OpenClaw. Ingests company documents into ChromaDB via Ollama embeddings, then an OpenClaw agent processes inbox drafts, searches memory, and posts relevant context to Slack.

## Commands

```bash
# Install / sync
uv sync

# Run all tests
uv run pytest

# Run single test
uv run pytest tests/test_drafts.py
uv run pytest tests/test_drafts.py::test_function_name -v

# CLI (two equivalent ways)
./bin/imem <subcommand>
uv run imem <subcommand>

# Ingest corpus into ChromaDB
uv run python scripts/ingest_corpus.py --force

# Reset demo state
./bin/imem reset-demo --clear-audit --clear-chroma

# Full demo reset cycle
./bin/imem reset-demo --clear-audit --clear-chroma
uv run python scripts/ingest_corpus.py --force
uv run python scripts/cosine_sanity.py

# Readiness checks
uv run python scripts/dgx_check.py          # ASUS/DGX hardware check
uv run python scripts/live_handoff.py        # live demo checklist
uv run python scripts/final_gate.py          # final gate before demo
```

## Architecture

**Pipeline flow:** `company/inbox/ → drafts → search ChromaDB → Slack post → mark processed`

Core package: `institutional_memory/`

| Module | Role |
|--------|------|
| `cli.py` | CLI entry point (`imem`). All subcommands emit JSON to stdout. |
| `config.py` | Central config from `.env` + defaults. All paths and thresholds live here. |
| `paths.py` | Path validation — prevents OpenClaw from escaping `company/inbox/` or `.runtime/`. |
| `drafts.py` | Discovers unprocessed inbox files, reads them, extracts Slack metadata. |
| `ingest.py` | Chunks documents and embeds via Ollama into ChromaDB. |
| `search.py` | Cosine similarity search over ChromaDB, deduped by source, filtered by threshold. |
| `slack.py` | Sends messages via Bot Token (primary) or Webhook (fallback). |
| `state.py` | JSON registry of processed drafts (`processed_drafts.json`). |
| `audit.py` | Appends JSONL events to `audit_log.jsonl`. |
| `documents.py` | Text extraction — plain text for `.txt`/`.md`, pymupdf4llm for `.pdf`. |

**Key directories:**
- `company/inbox/` — drafts for OpenClaw to process (`.txt`, `.md`, `.pdf`)
- `company/corpus/` — historical documents ingested into ChromaDB
- `.runtime/` — ephemeral working files (e.g., `slack_message.txt`)
- `scripts/` — standalone scripts for ingestion, checks, demo setup

**OpenClaw integration:** `SOUL.md` defines agent behavior. `bin/imem` is the tool interface — OpenClaw calls subcommands and gets JSON back. Path validation in `paths.py` constrains file access to `company/inbox/` and `.runtime/`.

## Key Design Decisions

- All CLI output is JSON (consumed by OpenClaw, not humans)
- Chroma uses cosine distance; scores are `1.0 - distance`
- Search deduplicates hits by source file, keeping highest score per source
- `RELEVANCE_THRESHOLD` (default 0.60) gates whether memory is "relevant enough" to post
- Slack delivery: Bot Token → Webhook fallback → error. Thread replies supported via `--thread-ts`
- Draft metadata (Slack channel, thread_ts, permalink) is parsed from markdown frontmatter-style headers in the first 40 lines

## Environment

Requires `.env` (copy from `.env.example`). Key vars:
- `OLLAMA_BASE_URL` — Ollama server (default `http://127.0.0.1:11434`)
- `EMBEDDING_MODEL` — embedding model (default `qwen3-embedding:8b`)
- `SLACK_BOT_TOKEN` / `SLACK_CHANNEL` / `SLACK_WEBHOOK_URL` — Slack delivery
- `RELEVANCE_THRESHOLD`, `TOP_K`, `CHUNK_SIZE`, `CHUNK_OVERLAP` — search tuning
