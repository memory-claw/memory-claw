# Dashboard Inbox Filtering, Search, and Re-ingest Design

Date: 2026-05-16

## Scope

Add three dashboard features without changing page navigation or requiring page reloads:

- Inbox document type filtering on the dashboard and inbox detail page.
- Inbox search on both pages, combined with type filtering.
- A working `POST /api/run/ingest` endpoint and richer re-ingest button status behavior.

This design follows the current dashboard structure in `dashboard/app.py`, `dashboard/static/index.html`, and `dashboard/static/inbox.html`. It also follows the ingestion entrypoint used by `scripts/ingest_corpus.py`: `ingest_folder(COMPANY_CORPUS_PATH, force=False)`.

## Existing Context

`institutional_memory/ingest.py` exports `ingest_folder`, `get_chroma_collection`, `chunk_text`, `embed_text`, `_load_ingested`, `_save_ingested`, and `_fingerprint`. `ingest_folder` walks a folder, creates relative source IDs such as `company/corpus/file.txt`, chunks text, embeds chunks, writes them into Chroma, and updates `ingested_files.json`.

`institutional_memory/config.py` defines `COMPANY_CORPUS_PATH`, `COMPANY_INBOX_PATH`, `PROJECT_ROOT`, Chroma settings, chunk settings, and Slack/dashboard settings.

The dashboard currently renders inbox and corpus lists client-side after fetching `/api/inbox`, `/api/inbox/full`, and `/api/corpus`. The corpus panel already uses a server-side `_infer_tag()` helper, but inbox rows do not yet carry document type metadata.

## Inbox Type Filtering

Add a shared client-side type classifier in both `index.html` and `inbox.html`. The classifier uses filename/path text with this precedence:

1. Contains `policy` -> `policy` / `Policy`
2. Contains `postmortem` or `incident` -> `postmortem` / `Postmortem`
3. Contains `contract` or `clause` -> `contract` / `Contract`
4. Contains `slack` -> `slack` / `Slack`
5. Contains `rfp` or `bid` -> `rfp` / `RFP`
6. Contains `draft` -> `draft` / `Draft`
7. Otherwise -> `other` / `Other`

The UI shows buttons in this exact order:

`All | Draft | Policy | Contract | RFP | Postmortem | Slack | Other`

`All` is selected by default. Active filter buttons use teal background and white text. Inactive filter buttons are outlined with no fill. Filtering is local only and does not issue new network requests.

Each rendered inbox row/card gets a `data-type` attribute so filtering uses the rendered row metadata rather than reparsing filename during every filter pass.

## Inbox Search

Add a search input above the filter bar in both inbox surfaces:

- Placeholder: `Search inbox...`
- Clear button: an inline `X` button shown only when text exists.
- Debounce: 200ms.
- Matching: case-insensitive substring match.
- Logic: search and type filters are combined with AND logic.

Dashboard search text includes filename/path, title, matched source, and summary. The full inbox page includes those fields plus body text and Slack message text where present.

Rendered rows/cards get a `data-search` attribute assembled at render time. Filtering reads `data-search` and `data-type`, then toggles row/card visibility. When all items are hidden by active filters, the page shows a small filtered-empty message. When there are no inbox files at all, it keeps the existing empty message.

## Re-ingest Endpoint

The endpoint should no longer assume a nonexistent ingestion API. It should mirror `scripts/ingest_corpus.py` for the core path/function choice: `COMPANY_CORPUS_PATH` and `ingest_folder(..., force=False)`.

Before ingesting, it queries Chroma through `get_chroma_collection().get(include=[])` to get existing IDs cheaply. Existing source paths are inferred from chunk IDs because `ingest.py` creates IDs as:

`{source}:{start_word}:{index}`

For path-only skip semantics, any corpus file whose relative source path already appears in Chroma is skipped, even if the file contents changed since the last ingest.

For new files, the endpoint ingests only those files while preserving normal source IDs. It should use the same primitives as `ingest_folder`: document loading, chunking, embedding, and `collection.add`. The helper should update `ingested_files.json` for newly ingested files so existing readiness tooling stays consistent.

The full endpoint is wrapped in `try/except` and always returns clear JSON:

- Success: `{ "ok": true, "added": N, "skipped": M, "files_added": [...], "chunks": C }`
- Failure: `{ "ok": false, "error": "<reason>" }`

Failures should not become silent 500 responses.

## Re-ingest Button

The dashboard button behavior:

- Disable button while `POST /api/run/ingest` is in flight.
- Show inline spinner text cycling every 300ms: `...`, `.. `, `. .`, `...`.
- On success, show `✓ N docs added` in teal and fade out after 4 seconds.
- After success, re-fetch `/api/stats` and `/api/corpus` so those panels update without full page reload.
- On error, show `✗ failed: <reason>` in red and keep it visible until the next click.
- Re-enable button when the request completes.

The implementation should treat non-2xx responses and `{ "ok": false }` payloads as errors.

## Testing

Add focused tests around behavior that is easiest to regress:

- Type inference includes `draft` and `other`, while preserving existing corpus categories.
- Re-ingest source extraction from Chroma chunk IDs skips already-present source paths.
- The endpoint returns `{ "ok": false, "error": ... }` when Chroma or ingestion fails.
- The endpoint only ingests corpus files whose relative source path is absent from Chroma.

Run targeted tests after implementation:

```bash
uv run pytest tests/test_ingest.py
```

If dashboard endpoint tests are added in a new file, also run that file directly.

## Non-goals

- No new inbox API query parameters.
- No server-side inbox filtering.
- No full page reload after filtering, searching, or successful re-ingest.
- No re-ingestion of changed files when their source path already exists in Chroma.
