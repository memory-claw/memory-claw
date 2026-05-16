# Slack Ingestion Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the shared Slack-ingestion foundation that later branches need: config, path safety, recursive inbox discovery, tracked Slack directories, and nested corpus source attribution.

**Architecture:** This is the first branch in the stack and should merge before the sync/CLI and listener branches. It does not add Slack API calls or a listener. It only prepares safe filesystem behavior and source recognition.

**Tech Stack:** Python 3.12+, argparse-adjacent existing CLI tests, pytest, existing `institutional_memory` package.

---

## Branch

- Branch: `codex/slack-ingestion-foundation`
- Base: current `main`
- Merge first.
- Do not edit `institutional_memory/slack_ingest.py` or `scripts/slack_listener.py`; those belong to later branches.

## File Ownership

- Create: `inbox/slack/.gitkeep`
- Create: `corpus/slack/.gitkeep`
- Modify: `.env.example`
- Modify: `institutional_memory/config.py`
- Modify: `institutional_memory/paths.py`
- Modify: `institutional_memory/drafts.py`
- Modify: `institutional_memory/slack.py`
- Test: `tests/test_paths.py`
- Test: `tests/test_drafts.py`
- Test: `tests/test_slack.py`

---

### Task 1: Slack Config And Corpus Path Safety

- [ ] **Step 1: Write failing path tests**

Add to `tests/test_paths.py`:

```python
from institutional_memory.config import PROJECT_ROOT
from institutional_memory.paths import PathNotAllowedError, safe_corpus_path


def test_safe_corpus_allows_markdown_under_slack_corpus():
    assert safe_corpus_path("corpus/slack/C123_1710000000.000000.md") == (
        PROJECT_ROOT / "corpus/slack/C123_1710000000.000000.md"
    ).resolve()


def test_safe_corpus_blocks_traversal():
    with pytest.raises(PathNotAllowedError):
        safe_corpus_path("corpus/../.env")
```

- [ ] **Step 2: Run failing tests**

```bash
uv run pytest tests/test_paths.py::test_safe_corpus_allows_markdown_under_slack_corpus tests/test_paths.py::test_safe_corpus_blocks_traversal -q
```

Expected: fail because `safe_corpus_path` is missing.

- [ ] **Step 3: Implement config and path helper**

In `institutional_memory/config.py`, add near the Slack settings:

```python
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
```

In `institutional_memory/paths.py`, import `CORPUS_PATH` and add `safe_corpus_path`:

```python
from institutional_memory.config import CORPUS_PATH, INBOX_PATH, PROJECT_ROOT, RUNTIME_PATH


def safe_corpus_path(raw: str) -> Path:
    candidate = _ensure_under(_resolve_under_project(raw), CORPUS_PATH, raw)
    if candidate.suffix.lower() not in {".txt", ".md", ".pdf"}:
        raise PathNotAllowedError("Only .txt, .md, and .pdf corpus files are allowed")
    return candidate
```

In `.env.example`, add:

```text
SLACK_APP_TOKEN=xapp-your-token-here
```

Create placeholder files:

```text
inbox/slack/.gitkeep
corpus/slack/.gitkeep
```

- [ ] **Step 4: Verify**

```bash
uv run pytest tests/test_paths.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add .env.example corpus/slack/.gitkeep inbox/slack/.gitkeep institutional_memory/config.py institutional_memory/paths.py tests/test_paths.py
git commit -m "feat: add Slack ingestion config paths"
```

---

### Task 2: Recursive Inbox Discovery

- [ ] **Step 1: Write failing recursive inbox test**

Create or update `tests/test_drafts.py`:

```python
from institutional_memory import drafts


def test_list_new_drafts_finds_nested_slack_markdown(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    nested = inbox / "slack"
    nested.mkdir(parents=True)
    draft = nested / "C123_1710000000.000000.md"
    draft.write_text("hello", encoding="utf-8")
    (nested / ".DS_Store").write_text("noise", encoding="utf-8")

    monkeypatch.setattr(drafts, "INBOX_PATH", inbox)
    monkeypatch.setattr(drafts, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(drafts, "load_processed_records", lambda: [])

    assert drafts.list_new_drafts() == ["inbox/slack/C123_1710000000.000000.md"]
```

- [ ] **Step 2: Run failing test**

```bash
uv run pytest tests/test_drafts.py::test_list_new_drafts_finds_nested_slack_markdown -q
```

Expected: fail because `list_new_drafts()` only scans top-level inbox files.

- [ ] **Step 3: Implement recursive discovery**

In `institutional_memory/drafts.py`, replace the `INBOX_PATH.iterdir()` loop with:

```python
    for path in sorted(INBOX_PATH.rglob("*")):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(INBOX_PATH).parts):
            continue
        if path.suffix.lower() not in {".txt", ".md", ".pdf"}:
            continue
        rel = str(path.resolve().relative_to(PROJECT_ROOT))
        if rel not in processed:
            drafts.append(rel)
```

- [ ] **Step 4: Verify**

```bash
uv run pytest tests/test_drafts.py tests/test_cli_json.py::test_list_new_drafts_returns_json_array -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add institutional_memory/drafts.py tests/test_drafts.py
git commit -m "feat: discover nested inbox drafts"
```

---

### Task 3: Nested Corpus Source Attribution

- [ ] **Step 1: Write failing attribution test**

Add to `tests/test_slack.py`:

```python
def test_source_attributions_find_nested_markdown_sources():
    text = "See corpus/slack/C123_1710000000.000000.md and corpus/mock_data/postmortems/source.md."

    assert slack.source_attributions(text) == [
        "corpus/mock_data/postmortems/source.md",
        "corpus/slack/C123_1710000000.000000.md",
    ]
```

- [ ] **Step 2: Run failing test**

```bash
uv run pytest tests/test_slack.py::test_source_attributions_find_nested_markdown_sources -q
```

Expected: fail because current regex only matches single-level `.txt`.

- [ ] **Step 3: Broaden regex**

In `institutional_memory/slack.py`, replace `SOURCE_PATTERN`:

```python
SOURCE_PATTERN = re.compile(r"\bcorpus/[A-Za-z0-9_./,-]+\.(?:txt|md)\b")
```

- [ ] **Step 4: Verify**

```bash
uv run pytest tests/test_slack.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add institutional_memory/slack.py tests/test_slack.py
git commit -m "fix: recognize nested corpus source attributions"
```

---

### Task 4: Branch Verification

- [ ] **Step 1: Run focused tests**

```bash
uv run pytest tests/test_paths.py tests/test_drafts.py tests/test_slack.py tests/test_cli_json.py::test_list_new_drafts_returns_json_array -q
```

Expected: pass.

- [ ] **Step 2: Push branch**

```bash
git push -u origin codex/slack-ingestion-foundation
```

Expected: branch pushed and ready to merge before the other two branches.
