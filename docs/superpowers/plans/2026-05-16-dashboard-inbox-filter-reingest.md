# Dashboard Inbox Filter and Re-ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add client-side inbox type filtering/search on both dashboard inbox surfaces and fix the dashboard re-ingest endpoint/button.

**Architecture:** Keep filtering/search in static browser code with no new inbox API calls. Add small backend helpers in `dashboard/app.py` for document type metadata and path-only Chroma skip semantics before ingesting new corpus files. Preserve existing source IDs by ingesting new files with exported ingest primitives from `institutional_memory.ingest`; the endpoint must not call `ingest_folder()`.

**Tech Stack:** FastAPI, plain HTML/CSS/JavaScript, ChromaDB collection API, pytest.

---

## File Structure

- Modify `dashboard/app.py`
  - Add document type inference helper for inbox data.
  - Add Chroma source extraction and single-file corpus ingest helper.
  - Replace `api_run_ingest()` with JSON success/error behavior.
- Modify `dashboard/static/index.html`
  - Add inbox search and type filter controls.
  - Add client-side filter state, debounce, clear button, and row `data-*` attributes.
  - Update re-ingest button status behavior.
- Modify `dashboard/static/inbox.html`
  - Add same search/filter controls for full inbox cards.
  - Add card `data-*` attributes and filtered empty state.
- Create `tests/test_dashboard.py`
  - Test document type inference.
  - Test Chroma source extraction.
  - Test re-ingest skips existing source paths.
  - Test re-ingest error payload.

## Task 1: Backend Helpers and Re-ingest Endpoint

**Files:**
- Modify: `dashboard/app.py`
- Create: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing backend tests**

Create `tests/test_dashboard.py`:

```python
import dashboard.app as dashboard_app


class FakeCollection:
    def __init__(self, ids=None, fail_get=False):
        self.ids = ids or []
        self.fail_get = fail_get
        self.add_calls = []

    def get(self, include=None, **kwargs):
        if self.fail_get:
            raise RuntimeError("chroma offline")
        return {"ids": self.ids}

    def add(self, **kwargs):
        self.add_calls.append(kwargs)


def test_infer_document_type_matches_required_precedence():
    cases = {
        "company/inbox/security_policy.md": "policy",
        "company/inbox/api_incident.md": "postmortem",
        "company/inbox/vendor_clause.txt": "contract",
        "company/inbox/slack/C123.md": "slack",
        "company/inbox/customer_bid.md": "rfp",
        "company/inbox/new_feature_draft.md": "draft",
        "company/inbox/lunch_notes.md": "other",
    }
    for path, expected in cases.items():
        assert dashboard_app._infer_document_type(path) == expected


def test_existing_chroma_sources_parse_chunk_ids():
    collection = FakeCollection(
        ids=[
            "company/corpus/source.txt:0:0",
            "company/corpus/mock_data/postmortems/source.md:350:1",
            "malformed",
        ]
    )

    assert dashboard_app._existing_chroma_sources(collection) == {
        "company/corpus/source.txt",
        "company/corpus/mock_data/postmortems/source.md",
    }


def test_run_ingest_skips_sources_already_in_chroma(tmp_path, monkeypatch):
    corpus = tmp_path / "company" / "corpus"
    corpus.mkdir(parents=True)
    existing = corpus / "existing.txt"
    existing.write_text(" ".join(f"old{i}" for i in range(20)), encoding="utf-8")
    new = corpus / "new_policy.txt"
    new.write_text(" ".join(f"new{i}" for i in range(20)), encoding="utf-8")
    registry = {}
    collection = FakeCollection(ids=["company/corpus/existing.txt:0:0"])

    monkeypatch.setattr(dashboard_app, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(dashboard_app, "COMPANY_CORPUS_PATH", corpus)
    monkeypatch.setattr(dashboard_app, "get_chroma_collection", lambda: collection)
    monkeypatch.setattr(dashboard_app, "embed_text", lambda text: [0.1, 0.2, 0.3])
    monkeypatch.setattr(dashboard_app, "_load_ingested", lambda: registry)
    monkeypatch.setattr(dashboard_app, "_save_ingested", lambda data: registry.update(data))

    result = dashboard_app.api_run_ingest()

    assert result["ok"] is True
    assert result["added"] == 1
    assert result["skipped"] == 1
    assert result["files_added"] == ["company/corpus/new_policy.txt"]
    assert result["chunks"] == 1
    assert len(collection.add_calls) == 1
    assert collection.add_calls[0]["metadatas"][0]["source"] == "company/corpus/new_policy.txt"


def test_run_ingest_returns_error_payload_when_chroma_fails(monkeypatch):
    collection = FakeCollection(fail_get=True)
    monkeypatch.setattr(dashboard_app, "get_chroma_collection", lambda: collection)

    result = dashboard_app.api_run_ingest()

    assert result["ok"] is False
    assert "chroma offline" in result["error"]
```

- [ ] **Step 2: Run backend tests to verify they fail**

Run:

```bash
uv run pytest tests/test_dashboard.py -v
```

Expected: FAIL because `_infer_document_type`, `_existing_chroma_sources`, and new endpoint behavior do not exist yet.

- [ ] **Step 3: Update imports in `dashboard/app.py`**

Change the ingest import block near the top of `dashboard/app.py` to include the exported primitives used by the new helper:

```python
from institutional_memory.documents import load_document_text
from institutional_memory.ingest import (
    _fingerprint,
    _load_ingested,
    _save_ingested,
    chunk_text,
    embed_text,
    get_chroma_collection,
)
```

Do not import or call `ingest_folder()` from `dashboard/app.py`; the endpoint needs per-file path filtering before Chroma writes.

- [ ] **Step 4: Add document type helper in `dashboard/app.py`**

Add this helper above `_infer_tag`:

```python
def _infer_document_type(rel_path: str) -> str:
    lower = rel_path.lower()
    if "policy" in lower:
        return "policy"
    if "postmortem" in lower or "incident" in lower:
        return "postmortem"
    if "contract" in lower or "clause" in lower:
        return "contract"
    if "slack" in lower:
        return "slack"
    if "rfp" in lower or "bid" in lower:
        return "rfp"
    if "draft" in lower:
        return "draft"
    return "other"
```

Update `_infer_tag()` to preserve existing corpus behavior for non-matching documents:

```python
def _infer_tag(rel_path: str) -> str:
    tag = _infer_document_type(rel_path)
    return "doc" if tag == "other" else tag
```

- [ ] **Step 5: Add `type` to inbox API items**

In `_inbox_item()`, add this key to the returned dict:

```python
"type": _infer_document_type(rel_path),
```

Place it near `"status": status` so UI data is easy to inspect.

- [ ] **Step 6: Add Chroma source and ingest helpers**

Add these helpers above `api_run_ingest()` in `dashboard/app.py`:

```python
def _source_from_chunk_id(chunk_id: str) -> str | None:
    parts = chunk_id.rsplit(":", 2)
    if len(parts) != 3:
        return None
    source, start_word, index = parts
    if not source or not start_word.isdigit() or not index.isdigit():
        return None
    return source


def _existing_chroma_sources(collection: Any) -> set[str]:
    result = collection.get(include=[])
    ids = result.get("ids") or []
    sources: set[str] = set()
    for chunk_id in ids:
        source = _source_from_chunk_id(str(chunk_id))
        if source:
            sources.add(source)
    return sources


def _ingest_corpus_file(path: Path, collection: Any, registry: dict[str, str]) -> dict[str, Any]:
    rel = str(path.resolve().relative_to(PROJECT_ROOT))
    text = load_document_text(path)
    file_chunks = chunk_text(text, rel)
    if not file_chunks:
        return {"file": rel, "chunks": 0, "ingested": False}

    collection.add(
        ids=[chunk["id"] for chunk in file_chunks],
        embeddings=[embed_text(chunk["text"]) for chunk in file_chunks],
        documents=[chunk["text"] for chunk in file_chunks],
        metadatas=[
            {
                "source": chunk["source"],
                "start_word": chunk["start_word"],
                "index": chunk["index"],
            }
            for chunk in file_chunks
        ],
    )
    registry[rel] = _fingerprint(path)
    return {"file": rel, "chunks": len(file_chunks), "ingested": True}
```

- [ ] **Step 7: Replace `api_run_ingest()`**

Replace the existing endpoint body with:

```python
@app.post("/api/run/ingest")
def api_run_ingest() -> dict[str, Any]:
    try:
        collection = get_chroma_collection()
        existing_sources = _existing_chroma_sources(collection)
        registry = _load_ingested()

        files_added: list[str] = []
        chunks = 0
        skipped = 0

        for path in _list_corpus_paths():
            rel = str(path.resolve().relative_to(PROJECT_ROOT))
            if rel in existing_sources:
                skipped += 1
                continue
            result = _ingest_corpus_file(path, collection, registry)
            if result["ingested"]:
                files_added.append(str(result["file"]))
                chunks += int(result["chunks"])

        _save_ingested(registry)
        return {
            "ok": True,
            "added": len(files_added),
            "skipped": skipped,
            "files_added": files_added,
            "chunks": chunks,
            "files": len(files_added),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
```

- [ ] **Step 8: Run backend tests**

Run:

```bash
uv run pytest tests/test_dashboard.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit backend work**

Run:

```bash
git add dashboard/app.py tests/test_dashboard.py
git commit -m "fix: reingest only new corpus sources"
```

## Task 2: Dashboard Inbox Search and Type Filter

**Files:**
- Modify: `dashboard/static/index.html`

- [ ] **Step 1: Add inbox control CSS**

In `dashboard/static/index.html`, add this CSS after `.panel-header` styles:

```css
    .inbox-controls {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin: -2px 0 10px;
    }
    .search-wrap {
      position: relative;
      width: 100%;
    }
    .search-input {
      width: 100%;
      font-family: var(--font);
      font-size: 12px;
      padding: 7px 28px 7px 10px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--panel);
      color: var(--text);
      outline: none;
    }
    .search-input:focus {
      border-color: var(--teal);
      box-shadow: 0 0 0 2px var(--teal-light);
    }
    .search-clear {
      position: absolute;
      right: 6px;
      top: 50%;
      transform: translateY(-50%);
      width: 18px;
      height: 18px;
      border: 0;
      background: transparent;
      color: var(--muted);
      cursor: pointer;
      font-family: var(--font);
      font-size: 13px;
      line-height: 18px;
      display: none;
    }
    .search-clear.visible { display: block; }
    .filter-bar {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .filter-btn {
      font-family: var(--font);
      font-size: 10px;
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid var(--teal);
      background: transparent;
      color: var(--teal-dark);
      cursor: pointer;
    }
    .filter-btn.active {
      background: var(--teal);
      color: #fff;
    }
```

- [ ] **Step 2: Add controls markup below inbox panel header**

In the inbox panel, between `</div>` for `.panel-header` and `<div class="list" id="inbox-list"></div>`, insert:

```html
          <div class="inbox-controls">
            <div class="search-wrap">
              <input class="search-input" id="inbox-search" type="search" placeholder="Search inbox..." autocomplete="off" />
              <button class="search-clear" id="inbox-search-clear" type="button" aria-label="Clear inbox search">X</button>
            </div>
            <div class="filter-bar" id="inbox-filter-bar" aria-label="Inbox document type filters"></div>
          </div>
```

- [ ] **Step 3: Add filter/search state and helpers**

Near the top of the `<script>` after `let auditExpanded = new Set();`, add:

```javascript
    const INBOX_FILTERS = [
      ["all", "All"],
      ["draft", "Draft"],
      ["policy", "Policy"],
      ["contract", "Contract"],
      ["rfp", "RFP"],
      ["postmortem", "Postmortem"],
      ["slack", "Slack"],
      ["other", "Other"],
    ];
    let inboxTypeFilter = "all";
    let inboxSearchTerm = "";
    let inboxSearchTimer = null;
```

Add these helper functions after `sourceBasename()`:

```javascript
    function normalizeSearchText(parts) {
      return parts
        .filter((part) => part != null)
        .map((part) => String(part).toLowerCase())
        .join(" ");
    }

    function renderInboxFilters() {
      document.getElementById("inbox-filter-bar").innerHTML = INBOX_FILTERS
        .map(([value, label]) => `<button type="button" class="filter-btn ${value === inboxTypeFilter ? "active" : ""}" data-filter="${esc(value)}">${esc(label)}</button>`)
        .join("");
      document.querySelectorAll("#inbox-filter-bar .filter-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          inboxTypeFilter = btn.getAttribute("data-filter") || "all";
          renderInboxFilters();
          applyInboxFilters();
        });
      });
    }

    function applyInboxFilters() {
      const list = document.getElementById("inbox-list");
      const rows = [...list.querySelectorAll(".list-item")];
      let visible = 0;
      rows.forEach((row) => {
        const typeMatches = inboxTypeFilter === "all" || row.dataset.type === inboxTypeFilter;
        const textMatches = !inboxSearchTerm || (row.dataset.search || "").includes(inboxSearchTerm);
        const show = typeMatches && textMatches;
        row.hidden = !show;
        if (show) visible += 1;
      });
      const existingEmpty = list.querySelector(".filtered-empty");
      if (existingEmpty) existingEmpty.remove();
      if (rows.length && visible === 0) {
        list.insertAdjacentHTML("beforeend", '<div class="empty filtered-empty">No inbox items match filters</div>');
      }
    }

    function setupInboxSearch() {
      const input = document.getElementById("inbox-search");
      const clear = document.getElementById("inbox-search-clear");
      input.addEventListener("input", () => {
        clear.classList.toggle("visible", input.value.length > 0);
        clearTimeout(inboxSearchTimer);
        inboxSearchTimer = setTimeout(() => {
          inboxSearchTerm = input.value.trim().toLowerCase();
          applyInboxFilters();
        }, 200);
      });
      clear.addEventListener("click", () => {
        input.value = "";
        inboxSearchTerm = "";
        clear.classList.remove("visible");
        clearTimeout(inboxSearchTimer);
        applyInboxFilters();
        input.focus();
      });
    }
```

- [ ] **Step 4: Add row `data-type` and `data-search` attributes**

In `renderInbox(items)`, inside `.map((item) => {`, add:

```javascript
          const itemType = item.type || "other";
          const searchText = normalizeSearchText([
            item.path,
            item.name,
            item.title,
            item.matched_source,
            sourceBasename(item.matched_source),
            item.summary,
          ]);
```

Change the returned row opening from:

```javascript
          return `<div class="list-item clickable" onclick="window.location.href='/inbox#${encodeURIComponent(item.path)}'">
```

to:

```javascript
          return `<div class="list-item clickable" data-type="${esc(itemType)}" data-search="${esc(searchText)}" onclick="window.location.href='/inbox#${encodeURIComponent(item.path)}'">
```

At the end of `renderInbox(items)`, after assigning `el.innerHTML`, call:

```javascript
      applyInboxFilters();
```

- [ ] **Step 5: Initialize controls**

Before `refresh();` at the bottom of the script, add:

```javascript
    renderInboxFilters();
    setupInboxSearch();
```

- [ ] **Step 6: Upgrade re-ingest status CSS**

Replace `.ingest-status` CSS with:

```css
    .ingest-status {
      font-size: 11px;
      color: var(--teal-dark);
      margin-left: 8px;
      transition: opacity 0.4s ease;
    }
    .ingest-status.error { color: var(--red); }
    .ingest-status.fade { opacity: 0; }
    .ingest-spinner { color: var(--muted); }
```

- [ ] **Step 7: Replace `runReingest()`**

Replace the whole `runReingest()` function in `index.html` with:

```javascript
    async function runReingest() {
      const btn = document.getElementById("btn-reingest");
      const statusEl = document.getElementById("ingest-status");
      const frames = ["...", ".. ", ". .", "..."];
      let frame = 0;
      let spinnerTimer = null;

      btn.disabled = true;
      statusEl.classList.remove("fade", "error");
      statusEl.textContent = frames[0];
      spinnerTimer = setInterval(() => {
        frame = (frame + 1) % frames.length;
        statusEl.textContent = frames[frame];
      }, 300);

      try {
        const response = await fetch("/api/run/ingest", { method: "POST" });
        const data = await response.json();
        if (!response.ok || data.ok === false) {
          throw new Error(data.error || `HTTP ${response.status}`);
        }
        clearInterval(spinnerTimer);
        spinnerTimer = null;
        const added = Number(data.added || 0);
        statusEl.textContent = `✓ ${added} doc${added === 1 ? "" : "s"} added`;
        await Promise.all([
          fetch("/api/stats").then((r) => r.json()).then(renderStats),
          fetch("/api/corpus").then((r) => r.json()).then(renderCorpus),
        ]);
        setTimeout(() => statusEl.classList.add("fade"), 4000);
        setTimeout(() => {
          statusEl.textContent = "";
          statusEl.classList.remove("fade");
        }, 4500);
      } catch (e) {
        if (spinnerTimer) clearInterval(spinnerTimer);
        statusEl.classList.add("error");
        statusEl.classList.remove("fade");
        statusEl.textContent = `✗ failed: ${String(e.message || e)}`;
      } finally {
        btn.disabled = false;
      }
    }
```

- [ ] **Step 8: Manual static sanity check**

Run:

```bash
uv run pytest tests/test_dashboard.py -v
```

Expected: PASS, proving backend API changes still hold after static edits.

- [ ] **Step 9: Commit dashboard index work**

Run:

```bash
git add dashboard/static/index.html
git commit -m "feat: add dashboard inbox filters"
```

## Task 3: Full Inbox Page Search and Type Filter

**Files:**
- Modify: `dashboard/static/inbox.html`

- [ ] **Step 1: Add controls CSS to `inbox.html`**

Add this CSS after `.page-sub`:

```css
    .inbox-controls {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 16px;
    }
    .search-wrap {
      position: relative;
      width: 100%;
    }
    .search-input {
      width: 100%;
      font-family: var(--font);
      font-size: 12px;
      padding: 8px 30px 8px 10px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--panel);
      color: var(--text);
      outline: none;
    }
    .search-input:focus {
      border-color: var(--teal);
      box-shadow: 0 0 0 2px var(--teal-light);
    }
    .search-clear {
      position: absolute;
      right: 7px;
      top: 50%;
      transform: translateY(-50%);
      width: 18px;
      height: 18px;
      border: 0;
      background: transparent;
      color: var(--muted);
      cursor: pointer;
      font-family: var(--font);
      font-size: 13px;
      line-height: 18px;
      display: none;
    }
    .search-clear.visible { display: block; }
    .filter-bar {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .filter-btn {
      font-family: var(--font);
      font-size: 10px;
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid var(--teal);
      background: transparent;
      color: var(--teal-dark);
      cursor: pointer;
    }
    .filter-btn.active {
      background: var(--teal);
      color: #fff;
    }
```

- [ ] **Step 2: Add controls markup**

After the `<p class="page-sub">...` line and before `<div id="drafts">`, insert:

```html
    <div class="inbox-controls">
      <div class="search-wrap">
        <input class="search-input" id="inbox-search" type="search" placeholder="Search inbox..." autocomplete="off" />
        <button class="search-clear" id="inbox-search-clear" type="button" aria-label="Clear inbox search">X</button>
      </div>
      <div class="filter-bar" id="inbox-filter-bar" aria-label="Inbox document type filters"></div>
    </div>
```

- [ ] **Step 3: Add shared JS state/helpers**

After `basename(p)` in the script, add:

```javascript
    const INBOX_FILTERS = [
      ["all", "All"],
      ["draft", "Draft"],
      ["policy", "Policy"],
      ["contract", "Contract"],
      ["rfp", "RFP"],
      ["postmortem", "Postmortem"],
      ["slack", "Slack"],
      ["other", "Other"],
    ];
    let inboxTypeFilter = "all";
    let inboxSearchTerm = "";
    let inboxSearchTimer = null;

    function normalizeSearchText(parts) {
      return parts
        .filter((part) => part != null)
        .map((part) => String(part).toLowerCase())
        .join(" ");
    }

    function renderInboxFilters() {
      document.getElementById("inbox-filter-bar").innerHTML = INBOX_FILTERS
        .map(([value, label]) => `<button type="button" class="filter-btn ${value === inboxTypeFilter ? "active" : ""}" data-filter="${esc(value)}">${esc(label)}</button>`)
        .join("");
      document.querySelectorAll("#inbox-filter-bar .filter-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          inboxTypeFilter = btn.getAttribute("data-filter") || "all";
          renderInboxFilters();
          applyInboxFilters();
        });
      });
    }

    function applyInboxFilters() {
      const list = document.getElementById("drafts");
      const cards = [...list.querySelectorAll(".draft-card")];
      let visible = 0;
      cards.forEach((card) => {
        const typeMatches = inboxTypeFilter === "all" || card.dataset.type === inboxTypeFilter;
        const textMatches = !inboxSearchTerm || (card.dataset.search || "").includes(inboxSearchTerm);
        const show = typeMatches && textMatches;
        card.hidden = !show;
        if (show) visible += 1;
      });
      const existingEmpty = list.querySelector(".filtered-empty");
      if (existingEmpty) existingEmpty.remove();
      if (cards.length && visible === 0) {
        list.insertAdjacentHTML("beforeend", '<p class="empty filtered-empty">No inbox items match filters</p>');
      }
    }

    function setupInboxSearch() {
      const input = document.getElementById("inbox-search");
      const clear = document.getElementById("inbox-search-clear");
      input.addEventListener("input", () => {
        clear.classList.toggle("visible", input.value.length > 0);
        clearTimeout(inboxSearchTimer);
        inboxSearchTimer = setTimeout(() => {
          inboxSearchTerm = input.value.trim().toLowerCase();
          applyInboxFilters();
        }, 200);
      });
      clear.addEventListener("click", () => {
        input.value = "";
        inboxSearchTerm = "";
        clear.classList.remove("visible");
        clearTimeout(inboxSearchTimer);
        applyInboxFilters();
        input.focus();
      });
    }
```

- [ ] **Step 4: Add card `data-type` and `data-search` attributes**

At the top of `renderDraft(d)`, after `const pills = [];`, add:

```javascript
      const itemType = d.type || "other";
      const searchText = normalizeSearchText([
        d.path,
        d.name,
        d.title,
        d.matched_source,
        basename(d.matched_source),
        d.summary,
        d.body_markdown,
        d.slack_message,
      ]);
```

Change the article opening from:

```javascript
      return `<article class="draft-card" id="${esc(d.path)}">
```

to:

```javascript
      return `<article class="draft-card" id="${esc(d.path)}" data-type="${esc(itemType)}" data-search="${esc(searchText)}">
```

In `load()`, after `el.innerHTML = items.map(renderDraft).join("");`, add:

```javascript
        applyInboxFilters();
```

- [ ] **Step 5: Initialize controls**

Before `load();` at the bottom, add:

```javascript
    renderInboxFilters();
    setupInboxSearch();
```

- [ ] **Step 6: Commit inbox detail work**

Run:

```bash
git add dashboard/static/inbox.html
git commit -m "feat: add inbox detail filters"
```

## Task 4: Verification

**Files:**
- Verify: `dashboard/app.py`
- Verify: `dashboard/static/index.html`
- Verify: `dashboard/static/inbox.html`
- Verify: `tests/test_dashboard.py`

- [ ] **Step 1: Run targeted dashboard tests**

Run:

```bash
uv run pytest tests/test_dashboard.py -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run existing ingest tests**

Run:

```bash
uv run pytest tests/test_ingest.py -v
```

Expected: all tests PASS. These tests confirm existing `ingest_folder()` behavior remains intact.

- [ ] **Step 3: Run full suite if time permits**

Run:

```bash
uv run pytest
```

Expected: all tests PASS. If failures are unrelated to touched dashboard/ingest behavior, record exact failing test names and failure text in final handoff.

- [ ] **Step 4: Optional local dashboard smoke test**

Run dashboard:

```bash
uv run dashboard
```

Open:

```text
http://127.0.0.1:7842/
```

Smoke checks:

- Inbox panel shows search input above filter buttons.
- `All` active by default.
- `RFP` hides non-RFP inbox rows.
- Search text narrows visible rows and clear `X` restores them.
- `/inbox` page has same controls and behavior.
- Re-ingest disables button, cycles spinner text, then shows success or red error.

- [ ] **Step 5: Final commit if verification required fixes**

If verification required fixes after previous commits, run:

```bash
git add dashboard/app.py dashboard/static/index.html dashboard/static/inbox.html tests/test_dashboard.py
git commit -m "test: verify dashboard inbox and ingest behavior"
```

If no files changed during verification, do not create an empty commit.
