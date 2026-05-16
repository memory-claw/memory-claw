# Dashboard Inbox Filter and Re-ingest Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add client-side inbox search/filter on both dashboard surfaces and harden the re-ingest endpoint with error handling.

**Architecture:** Extend existing `_infer_tag` to cover all document types (adding `draft` and `other`). Expose `type` field on inbox API items. Client-side JS filters/search on both pages using shared CSS loaded from a single file. Re-ingest keeps existing `ingest_folder()` — just add `try/except` and `ok` field.

**Tech Stack:** FastAPI, plain HTML/CSS/JavaScript, pytest.

---

## File Structure

- Modify `dashboard/app.py`
  - Rename `_infer_tag` → `_infer_document_type`, add `draft` and `other` returns.
  - Add `type` field to `_inbox_item()` return dict.
  - Wrap `api_run_ingest()` in try/except, add `ok` field to response.
- Create `dashboard/static/controls.css`
  - Shared search input, filter button, and clear button styles.
- Modify `dashboard/static/index.html`
  - Link `controls.css`. Add search/filter markup and JS. Add `data-type`/`data-search` to inbox rows.
  - Upgrade `runReingest()` to handle `ok: false` with red error text.
- Modify `dashboard/static/inbox.html`
  - Link `controls.css`. Add search/filter markup and JS. Add `data-type`/`data-search` to draft cards.
- Create `tests/test_dashboard.py`
  - Test `_infer_document_type` covers all types including new `draft` and `other`.
  - Test `api_run_ingest` error payload.

## Task 1: Backend — Document Type and Re-ingest Error Handling

**Goal:** Extend `_infer_tag` to return all document types, expose `type` on inbox items, and add error handling to re-ingest endpoint.

**Files:**
- Modify: `dashboard/app.py:332-344` (`_infer_tag`), `dashboard/app.py:478-492` (`_inbox_item`), `dashboard/app.py:713-737` (`api_run_ingest`)
- Create: `tests/test_dashboard.py`

**Acceptance Criteria:**
- [ ] `_infer_document_type("company/inbox/draft_notes.md")` returns `"draft"`
- [ ] `_infer_document_type("company/inbox/lunch.md")` returns `"other"`
- [ ] `_infer_document_type("company/inbox/security_policy.md")` returns `"policy"`
- [ ] Inbox API items include `"type"` key
- [ ] Re-ingest returns `{"ok": true, ...}` on success
- [ ] Re-ingest returns `{"ok": false, "error": "..."}` when Chroma/Ollama is down

**Verify:** `uv run pytest tests/test_dashboard.py -v`

**Steps:**

- [ ] **Step 1: Write tests**

Create `tests/test_dashboard.py`:

```python
import dashboard.app as dashboard_app


def test_infer_document_type_all_categories():
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
        assert dashboard_app._infer_document_type(path) == expected, f"{path} → expected {expected}"


def test_run_ingest_returns_ok_field(monkeypatch):
    monkeypatch.setattr(
        dashboard_app,
        "ingest_folder",
        lambda folder, force: {"files": 0, "chunks": 0},
    )
    monkeypatch.setattr(dashboard_app, "_load_ingested", lambda: {})
    monkeypatch.setattr(dashboard_app, "_list_corpus_paths", lambda: [])

    result = dashboard_app.api_run_ingest()
    assert result["ok"] is True


def test_run_ingest_returns_error_on_exception(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("chroma offline")

    monkeypatch.setattr(dashboard_app, "_load_ingested", boom)

    result = dashboard_app.api_run_ingest()
    assert result["ok"] is False
    assert "chroma offline" in result["error"]
```

- [ ] **Step 2: Run tests — confirm they fail**

Run: `uv run pytest tests/test_dashboard.py -v`

Expected: FAIL — `_infer_document_type` doesn't exist, `api_run_ingest` doesn't return `ok`, no try/except.

- [ ] **Step 3: Rename `_infer_tag` → `_infer_document_type` and add cases**

In `dashboard/app.py`, replace `_infer_tag` (line 332) with:

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

Update all call sites of `_infer_tag` to use `_infer_document_type`. Grep for `_infer_tag` — it's called in `_corpus_item()` and possibly other corpus-related functions. Those callers previously got `"doc"` for unmatched files; now they get `"other"`. If any caller needs the old `"doc"` value, map it: but check first — the CSS class `.tag.doc` exists in `index.html`, so either add `.tag.other` CSS or keep returning `"doc"` for corpus items specifically.

**Resolution:** The simplest approach — `_infer_document_type` returns the canonical type. For corpus tag display, the caller maps `"other"` → `"doc"`:

Find every call site of `_infer_tag` and replace with `_infer_document_type`. In the corpus item builder where it sets `"tag"`, use:

```python
doc_type = _infer_document_type(rel)
"tag": "doc" if doc_type == "other" else doc_type,
```

This preserves existing `.tag.doc` CSS without adding a new class.

- [ ] **Step 4: Add `type` to `_inbox_item` return dict**

In `_inbox_item()` (line 478), add to the returned dict:

```python
"type": _infer_document_type(rel_path),
```

Place it after the `"status"` key.

- [ ] **Step 5: Wrap `api_run_ingest` in try/except, add `ok` field**

Replace `api_run_ingest()` body (line 714) with:

```python
@app.post("/api/run/ingest")
def api_run_ingest() -> dict[str, Any]:
    try:
        registry_before = dict(_load_ingested())
        eligible = _list_corpus_paths()
        skipped = 0
        for path in eligible:
            rel = str(path.resolve().relative_to(PROJECT_ROOT))
            if registry_before.get(rel) == _fingerprint(path):
                skipped += 1

        result = ingest_folder(COMPANY_CORPUS_PATH, force=False)
        registry_after = _load_ingested()
        files_added = [
            rel
            for rel, fp in registry_after.items()
            if registry_before.get(rel) != fp
        ]

        return {
            "ok": True,
            "added": len(files_added),
            "skipped": skipped,
            "files_added": files_added,
            "chunks": result.get("chunks", 0),
            "files": result.get("files", 0),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
```

- [ ] **Step 6: Run tests — confirm they pass**

Run: `uv run pytest tests/test_dashboard.py -v`

Expected: all 3 PASS.

- [ ] **Step 7: Commit**

```bash
git add dashboard/app.py tests/test_dashboard.py
git commit -m "feat: add document type inference and reingest error handling"
```

## Task 2: Shared Controls CSS

**Goal:** Create one CSS file for search/filter controls, linked from both dashboard pages.

**Files:**
- Create: `dashboard/static/controls.css`

**Acceptance Criteria:**
- [ ] File contains all search input, filter button, and clear button styles
- [ ] No duplicate CSS across pages

**Verify:** File exists and is valid CSS.

**Steps:**

- [ ] **Step 1: Create `dashboard/static/controls.css`**

```css
.inbox-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
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
.filtered-empty {
  text-align: center;
  color: var(--muted);
  padding: 24px 12px;
  font-size: 12px;
}
.ingest-status.error { color: var(--red); }
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/static/controls.css
git commit -m "feat: add shared controls CSS for inbox filter"
```

## Task 3: Dashboard Index — Inbox Filter/Search and Re-ingest UX

**Goal:** Add search input, type filter buttons, and error-aware re-ingest to the main dashboard inbox panel.

**Files:**
- Modify: `dashboard/static/index.html`

**Acceptance Criteria:**
- [ ] Search input with clear button above inbox list
- [ ] Type filter buttons (All, Draft, Policy, Contract, RFP, Postmortem, Slack, Other)
- [ ] Filtering hides non-matching rows, shows empty state when zero visible
- [ ] Search debounces at 200ms
- [ ] Re-ingest shows red error text when `ok: false`
- [ ] Inbox rows have `data-type` and `data-search` attributes

**Verify:** `uv run python -m dashboard` → open `http://127.0.0.1:7842/` → filter/search/re-ingest work.

**Steps:**

- [ ] **Step 1: Link shared CSS**

In `<head>`, after the closing `</style>` tag, add:

```html
<link rel="stylesheet" href="/static/controls.css" />
```

- [ ] **Step 2: Add controls markup**

Between the inbox `</div>` for `.panel-header` (after line 321) and `<div class="list" id="inbox-list">`, insert:

```html
          <div class="inbox-controls">
            <div class="search-wrap">
              <input class="search-input" id="inbox-search" type="search" placeholder="Search inbox..." autocomplete="off" />
              <button class="search-clear" id="inbox-search-clear" type="button" aria-label="Clear search">X</button>
            </div>
            <div class="filter-bar" id="inbox-filter-bar"></div>
          </div>
```

- [ ] **Step 3: Add filter/search JS state and helpers**

After `let auditExpanded = new Set();` (line 370), add:

```javascript
    const INBOX_FILTERS = [
      ["all", "All"], ["draft", "Draft"], ["policy", "Policy"],
      ["contract", "Contract"], ["rfp", "RFP"], ["postmortem", "Postmortem"],
      ["slack", "Slack"], ["other", "Other"],
    ];
    let inboxTypeFilter = "all";
    let inboxSearchTerm = "";
    let inboxSearchTimer = null;
```

After `sourceBasename()` function, add:

```javascript
    function renderInboxFilters() {
      document.getElementById("inbox-filter-bar").innerHTML = INBOX_FILTERS
        .map(([val, label]) =>
          `<button type="button" class="filter-btn ${val === inboxTypeFilter ? "active" : ""}" data-filter="${esc(val)}">${esc(label)}</button>`
        ).join("");
      document.querySelectorAll("#inbox-filter-bar .filter-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          inboxTypeFilter = btn.dataset.filter || "all";
          renderInboxFilters();
          applyInboxFilters();
        });
      });
    }

    function applyInboxFilters() {
      const rows = [...document.querySelectorAll("#inbox-list .list-item")];
      let visible = 0;
      rows.forEach((row) => {
        const typeOk = inboxTypeFilter === "all" || row.dataset.type === inboxTypeFilter;
        const textOk = !inboxSearchTerm || (row.dataset.search || "").includes(inboxSearchTerm);
        row.hidden = !(typeOk && textOk);
        if (!row.hidden) visible++;
      });
      const old = document.querySelector("#inbox-list .filtered-empty");
      if (old) old.remove();
      if (rows.length && !visible) {
        document.getElementById("inbox-list").insertAdjacentHTML("beforeend",
          '<div class="filtered-empty">No inbox items match filters</div>');
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
        applyInboxFilters();
        input.focus();
      });
    }
```

- [ ] **Step 4: Add `data-type` and `data-search` to inbox rows**

In `renderInbox(items)`, inside the `.map((item) => {` callback, add before the `return`:

```javascript
          const itemType = item.type || "other";
          const searchText = [item.path, item.name, item.title, item.matched_source, sourceBasename(item.matched_source), item.summary]
            .filter(Boolean).map(s => String(s).toLowerCase()).join(" ");
```

Change the row opening div from:

```javascript
          return `<div class="list-item clickable" onclick="...">
```

to:

```javascript
          return `<div class="list-item clickable" data-type="${esc(itemType)}" data-search="${esc(searchText)}" onclick="...">
```

At the end of `renderInbox(items)`, after `el.innerHTML = ...`, add:

```javascript
      applyInboxFilters();
```

- [ ] **Step 5: Upgrade `runReingest()` error handling**

In `runReingest()`, change the try block's fetch handling to check `ok`:

```javascript
        const response = await fetch("/api/run/ingest", { method: "POST" });
        const data = await response.json();
        if (!response.ok || data.ok === false) {
          throw new Error(data.error || `HTTP ${response.status}`);
        }
```

Change the catch block to show red error:

```javascript
      } catch (e) {
        statusEl.classList.add("error");
        statusEl.textContent = `✗ ${e.message || "ingest failed"}`;
```

Remove the `statusEl.classList.remove("fade")` from the existing `finally` block's first `setTimeout`, since errors should stay visible. Only fade on success.

- [ ] **Step 6: Initialize controls**

Before `refresh();` at end of script, add:

```javascript
    renderInboxFilters();
    setupInboxSearch();
```

- [ ] **Step 7: Commit**

```bash
git add dashboard/static/index.html
git commit -m "feat: add inbox search/filter and reingest error UX"
```

## Task 4: Inbox Detail Page — Search and Type Filter

**Goal:** Add same search/filter controls to full inbox page at `/inbox`.

**Files:**
- Modify: `dashboard/static/inbox.html`

**Acceptance Criteria:**
- [ ] Search input with clear button above draft cards
- [ ] Same type filter buttons as dashboard
- [ ] Filtering hides non-matching cards, shows empty state
- [ ] Draft cards have `data-type` and `data-search` attributes

**Verify:** `uv run python -m dashboard` → open `http://127.0.0.1:7842/inbox` → filter/search work.

**Steps:**

- [ ] **Step 1: Link shared CSS**

In `<head>`, after `</style>`, add:

```html
<link rel="stylesheet" href="/static/controls.css" />
```

- [ ] **Step 2: Add controls markup**

After `<p class="page-sub">...</p>` and before `<div id="drafts">`, insert:

```html
    <div class="inbox-controls">
      <div class="search-wrap">
        <input class="search-input" id="inbox-search" type="search" placeholder="Search inbox..." autocomplete="off" />
        <button class="search-clear" id="inbox-search-clear" type="button" aria-label="Clear search">X</button>
      </div>
      <div class="filter-bar" id="inbox-filter-bar"></div>
    </div>
```

- [ ] **Step 3: Add JS state and helpers**

After `basename(p)` function, add:

```javascript
    const INBOX_FILTERS = [
      ["all", "All"], ["draft", "Draft"], ["policy", "Policy"],
      ["contract", "Contract"], ["rfp", "RFP"], ["postmortem", "Postmortem"],
      ["slack", "Slack"], ["other", "Other"],
    ];
    let inboxTypeFilter = "all";
    let inboxSearchTerm = "";
    let inboxSearchTimer = null;

    function renderInboxFilters() {
      document.getElementById("inbox-filter-bar").innerHTML = INBOX_FILTERS
        .map(([val, label]) =>
          `<button type="button" class="filter-btn ${val === inboxTypeFilter ? "active" : ""}" data-filter="${esc(val)}">${esc(label)}</button>`
        ).join("");
      document.querySelectorAll("#inbox-filter-bar .filter-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          inboxTypeFilter = btn.dataset.filter || "all";
          renderInboxFilters();
          applyInboxFilters();
        });
      });
    }

    function applyInboxFilters() {
      const cards = [...document.querySelectorAll("#drafts .draft-card")];
      let visible = 0;
      cards.forEach((card) => {
        const typeOk = inboxTypeFilter === "all" || card.dataset.type === inboxTypeFilter;
        const textOk = !inboxSearchTerm || (card.dataset.search || "").includes(inboxSearchTerm);
        card.hidden = !(typeOk && textOk);
        if (!card.hidden) visible++;
      });
      const old = document.querySelector("#drafts .filtered-empty");
      if (old) old.remove();
      if (cards.length && !visible) {
        document.getElementById("drafts").insertAdjacentHTML("beforeend",
          '<p class="filtered-empty">No inbox items match filters</p>');
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
        applyInboxFilters();
        input.focus();
      });
    }
```

- [ ] **Step 4: Add `data-type` and `data-search` to draft cards**

In `renderDraft(d)`, after `const pills = [];`, add:

```javascript
      const itemType = d.type || "other";
      const searchText = [d.path, d.name, d.title, d.matched_source, basename(d.matched_source), d.summary, d.body_markdown, d.slack_message]
        .filter(Boolean).map(s => String(s).toLowerCase()).join(" ");
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

Before `load();` at bottom of script, add:

```javascript
    renderInboxFilters();
    setupInboxSearch();
```

- [ ] **Step 6: Commit**

```bash
git add dashboard/static/inbox.html
git commit -m "feat: add inbox detail page search and filter"
```

## Task 5: Verification

**Goal:** Confirm all tests pass and no regressions.

**Files:**
- Verify: all modified files

**Acceptance Criteria:**
- [ ] `tests/test_dashboard.py` passes
- [ ] `tests/test_ingest.py` passes (existing behavior intact)
- [ ] Full test suite passes

**Verify:** `uv run pytest`

**Steps:**

- [ ] **Step 1: Run dashboard tests**

Run: `uv run pytest tests/test_dashboard.py -v`

Expected: 3 tests PASS.

- [ ] **Step 2: Run ingest tests**

Run: `uv run pytest tests/test_ingest.py -v`

Expected: all PASS — `ingest_folder()` unchanged.

- [ ] **Step 3: Run full suite**

Run: `uv run pytest`

Expected: all PASS. If unrelated failures, note them but don't block.

- [ ] **Step 4: Smoke test dashboard**

Run: `uv run python -m dashboard`

Open `http://127.0.0.1:7842/`:
- Inbox shows search input + filter buttons
- "All" active by default
- Clicking "Policy" hides non-policy rows
- Typing in search narrows rows, X clears
- Re-ingest shows spinner, success message, or red error
- `/inbox` page has same filter/search behavior
