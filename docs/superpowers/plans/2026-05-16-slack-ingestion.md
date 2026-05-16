# Slack Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Slack ingestion so ASUS can turn Slack threads into inbox drafts or trusted corpus memory without changing OpenClaw's one-shot command workflow.

**Architecture:** Keep OpenClaw isolated from long-running listeners. A separate Socket Mode listener writes live Slack threads to `inbox/slack/`; one-shot `./bin/imem` operator commands sync Slack history and promote selected inbox artifacts into `corpus/slack/`. Existing OpenClaw commands continue to list/read inbox files, search corpus, post Slack answers, and mark processed.

**Tech Stack:** Python 3.12+, `slack-sdk`, Socket Mode, argparse, markdown files, pytest, existing `institutional_memory` package.

---

## File Structure

- Create `institutional_memory/slack_ingest.py`: Slack thread models, filename generation, markdown rendering, bot filtering, Slack WebClient history/reply fetch, write-to-inbox/corpus helpers, promotion helper.
- Create `scripts/slack_listener.py`: long-running Socket Mode process, never OpenClaw-facing.
- Modify `institutional_memory/config.py`: add `SLACK_APP_TOKEN`.
- Modify `institutional_memory/paths.py`: add `safe_corpus_path`.
- Modify `institutional_memory/drafts.py`: recursively discover inbox files, including `inbox/slack/*.md`.
- Modify `institutional_memory/cli.py`: add one-shot `sync-slack`, `promote-slack-thread`, and `reset-demo --clear-slack-inbox`.
- Modify `institutional_memory/slack.py`: broaden source attribution regex to nested `.txt` and `.md` corpus paths.
- Modify `scripts/dgx_check.py`: add optional `--check-slack-ingestion`.
- Create `inbox/slack/.gitkeep` and `corpus/slack/.gitkeep`: make Slack import directories exist on fresh clones.
- Modify `.env.example` and `README.md`: document Slack app token, listener, manual sync, promotion, and re-ingest.
- Add tests in `tests/test_slack_ingest.py`, `tests/test_drafts.py`, `tests/test_cli_json.py`, `tests/test_paths.py`, `tests/test_slack.py`, `tests/test_dgx_check.py`, and `tests/test_readme_handoff.py`.

---

### Task 1: Config And Safe Corpus Paths

**Files:**
- Create: `inbox/slack/.gitkeep`
- Create: `corpus/slack/.gitkeep`
- Modify: `institutional_memory/config.py`
- Modify: `institutional_memory/paths.py`
- Modify: `.env.example`
- Test: `tests/test_paths.py`

- [ ] **Step 1: Write failing path tests**

Add these tests to `tests/test_paths.py`:

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

Run:

```bash
uv run pytest tests/test_paths.py::test_safe_corpus_allows_markdown_under_slack_corpus tests/test_paths.py::test_safe_corpus_blocks_traversal -q
```

Expected: fail because `safe_corpus_path` is missing.

- [ ] **Step 3: Implement config and path helper**

In `institutional_memory/config.py`, add near the Slack settings:

```python
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
```

In `institutional_memory/paths.py`, import `CORPUS_PATH` and add:

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

Create empty placeholder files:

```text
inbox/slack/.gitkeep
corpus/slack/.gitkeep
```

- [ ] **Step 4: Verify tests pass**

Run:

```bash
uv run pytest tests/test_paths.py -q
```

Expected: all path tests pass.

- [ ] **Step 5: Commit**

```bash
git add .env.example corpus/slack/.gitkeep inbox/slack/.gitkeep institutional_memory/config.py institutional_memory/paths.py tests/test_paths.py
git commit -m "feat: add Slack ingestion config paths"
```

---

### Task 2: Recursive Inbox Discovery And Slack Reset

**Files:**
- Modify: `institutional_memory/drafts.py`
- Modify: `institutional_memory/cli.py`
- Test: `tests/test_drafts.py`
- Test: `tests/test_cli_json.py`

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

- [ ] **Step 2: Write failing reset test**

Add to `tests/test_cli_json.py`:

```python
def test_reset_demo_can_clear_slack_inbox(tmp_path, monkeypatch, capsys):
    from institutional_memory import cli

    runtime = tmp_path / ".runtime"
    runtime.mkdir()
    inbox = tmp_path / "inbox"
    slack_inbox = inbox / "slack"
    slack_inbox.mkdir(parents=True)
    (slack_inbox / "C123_1710000000.000000.md").write_text("thread", encoding="utf-8")

    monkeypatch.setattr(cli, "RUNTIME_PATH", runtime)
    monkeypatch.setattr(cli, "CHROMA_PATH", tmp_path / "chroma_db")
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "AUDIT_LOG", tmp_path / "audit_log.jsonl")
    monkeypatch.setattr(cli, "reset_processed", lambda: None)

    args = cli.build_parser().parse_args(["reset-demo", "--clear-slack-inbox"])
    assert args.func(args) == 0
    assert not (slack_inbox / "C123_1710000000.000000.md").exists()
```

- [ ] **Step 3: Run failing tests**

Run:

```bash
uv run pytest tests/test_drafts.py tests/test_cli_json.py::test_reset_demo_can_clear_slack_inbox -q
```

Expected: recursive draft test fails on missing nested discovery; reset test fails until `--clear-slack-inbox` exists.

- [ ] **Step 4: Implement recursive discovery**

In `institutional_memory/drafts.py`, replace the loop in `list_new_drafts()` with:

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

- [ ] **Step 5: Implement Slack inbox reset**

In `institutional_memory/cli.py`, import `INBOX_PATH` from config. In `cmd_reset_demo()`, add after runtime cleanup:

```python
    if args.clear_slack_inbox:
        slack_inbox = PROJECT_ROOT / "inbox" / "slack"
        if slack_inbox.exists():
            for child in slack_inbox.rglob("*"):
                if child.is_file() and child.name != ".gitkeep":
                    child.unlink(missing_ok=True)
```

In `build_parser()`, add:

```python
    reset.add_argument("--clear-slack-inbox", action="store_true")
```

Update reset JSON:

```python
    emit({
        "status": "reset",
        "clear_audit": args.clear_audit,
        "clear_chroma": args.clear_chroma,
        "clear_slack_inbox": args.clear_slack_inbox,
    })
```

- [ ] **Step 6: Verify tests pass**

Run:

```bash
uv run pytest tests/test_drafts.py tests/test_cli_json.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add institutional_memory/drafts.py institutional_memory/cli.py tests/test_drafts.py tests/test_cli_json.py
git commit -m "feat: discover nested Slack inbox drafts"
```

---

### Task 3: Source Attribution For Nested Corpus Markdown

**Files:**
- Modify: `institutional_memory/slack.py`
- Test: `tests/test_slack.py`

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

Expected: fail because the regex only matches single-level `.txt`.

- [ ] **Step 3: Broaden the regex**

In `institutional_memory/slack.py`, replace `SOURCE_PATTERN` with:

```python
SOURCE_PATTERN = re.compile(r"\bcorpus/[A-Za-z0-9_./,-]+\.(?:txt|md)\b")
```

- [ ] **Step 4: Verify tests pass**

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

### Task 4: Slack Ingestion Core Module

**Files:**
- Create: `institutional_memory/slack_ingest.py`
- Test: `tests/test_slack_ingest.py`

- [ ] **Step 1: Write failing core tests**

Create `tests/test_slack_ingest.py`:

```python
import pytest

from institutional_memory import slack_ingest


def test_thread_file_name_uses_channel_and_parent_thread_ts():
    event = {"channel": "C123", "ts": "1710000001.000000", "thread_ts": "1710000000.000000"}

    assert slack_ingest.thread_file_name(event) == "C123_1710000000.000000.md"


def test_thread_file_name_uses_message_ts_without_thread_ts():
    event = {"channel": "C123", "ts": "1710000001.000000"}

    assert slack_ingest.thread_file_name(event) == "C123_1710000001.000000.md"


def test_should_ignore_bot_message():
    assert slack_ingest.should_ignore_event({"bot_id": "B123"}) is True
    assert slack_ingest.should_ignore_event({"subtype": "bot_message"}) is True
    assert slack_ingest.should_ignore_event({"user": "U123", "text": "hello"}) is False


def test_render_thread_markdown_contains_metadata_and_messages():
    messages = [
        {"user": "U123", "text": "Need NHS &amp; liability precedent", "ts": "1710000000.000000"},
        {"user": "U456", "text": "Check old postmortem", "ts": "1710000001.000000"},
    ]

    text = slack_ingest.render_thread_markdown(
        channel="C123",
        thread_ts_value="1710000000.000000",
        messages=messages,
        permalink="https://example.slack.com/archives/C123/p1710000000000000",
        imported_at="2026-05-16T00:00:00+00:00",
    )

    assert "# Slack Thread: Need NHS & liability precedent" in text
    assert "**Channel:** C123" in text
    assert "**Thread TS:** 1710000000.000000" in text
    assert "**Permalink:** https://example.slack.com/archives/C123/p1710000000000000" in text
    assert "- 1710000000.000000 U123: Need NHS & liability precedent" in text
    assert "- 1710000001.000000 U456: Check old postmortem" in text


def test_promote_slack_thread_rejects_non_slack_inbox_file(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    corpus = tmp_path / "corpus"
    inbox.mkdir()
    corpus.mkdir()
    (inbox / "ordinary.md").write_text("not a Slack import", encoding="utf-8")
    monkeypatch.setattr(slack_ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(slack_ingest, "INBOX_PATH", inbox)
    monkeypatch.setattr(slack_ingest, "CORPUS_PATH", corpus)

    with pytest.raises(slack_ingest.PathNotAllowedError):
        slack_ingest.promote_slack_thread("inbox/ordinary.md")
```

- [ ] **Step 2: Run failing tests**

```bash
uv run pytest tests/test_slack_ingest.py -q
```

Expected: fail because `institutional_memory.slack_ingest` does not exist.

- [ ] **Step 3: Implement core module**

Create `institutional_memory/slack_ingest.py`:

```python
"""Slack ingestion helpers for inbox and corpus imports."""

from __future__ import annotations

import html
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from institutional_memory.config import CORPUS_PATH, INBOX_PATH, PROJECT_ROOT, SLACK_BOT_TOKEN
from institutional_memory.paths import PathNotAllowedError, safe_corpus_path, safe_inbox_path
from institutional_memory.state import load_processed_records

Mode = Literal["inbox", "corpus"]
INGEST_REMINDER = "run uv run python scripts/ingest_corpus.py --force to make imported Slack corpus files searchable"


def thread_ts(event: dict[str, Any]) -> str:
    value = event.get("thread_ts") or event.get("ts")
    if not value:
        raise ValueError("Slack event missing ts")
    return str(value)


def thread_file_name(event: dict[str, Any]) -> str:
    channel = str(event["channel"])
    return f"{channel}_{thread_ts(event)}.md"


def should_ignore_event(event: dict[str, Any]) -> bool:
    return bool(event.get("bot_id") or event.get("subtype") == "bot_message")


def _preview(messages: list[dict[str, Any]]) -> str:
    text = next((str(item.get("text", "")).strip() for item in messages if item.get("text")), "Slack thread")
    text = html.unescape(text)
    text = " ".join(text.split())
    return text[:80] if text else "Slack thread"


def render_thread_markdown(
    *,
    channel: str,
    thread_ts_value: str,
    messages: list[dict[str, Any]],
    permalink: str | None,
    imported_at: str | None = None,
) -> str:
    imported = imported_at or datetime.now(timezone.utc).isoformat()
    lines = [
        f"# Slack Thread: {_preview(messages)}",
        "",
        f"**Channel:** {channel}",
        f"**Thread TS:** {thread_ts_value}",
        f"**Imported At:** {imported}",
        "**Source:** Slack",
        f"**Permalink:** {permalink or ''}",
        "",
        "## Messages",
        "",
    ]
    for message in messages:
        user = message.get("user") or message.get("username") or "unknown"
        text = html.unescape(str(message.get("text", "")).replace("\n", " ")).strip()
        lines.append(f"- {message.get('ts')} {user}: {text}")
    lines.append("")
    return "\n".join(lines)


def destination_path(mode: Mode, filename: str) -> Path:
    if mode == "inbox":
        return safe_inbox_path(str(INBOX_PATH / "slack" / filename))
    if mode == "corpus":
        return safe_corpus_path(str(CORPUS_PATH / "slack" / filename))
    raise ValueError(f"invalid Slack sync mode: {mode}")


def processed_paths() -> set[str]:
    return {str(record.get("path")) for record in load_processed_records() if record.get("path")}


def is_processed(path: Path, processed: set[str]) -> bool:
    rel = str(path.resolve().relative_to(PROJECT_ROOT))
    return rel in processed


def write_thread_file(
    mode: Mode,
    event: dict[str, Any],
    messages: list[dict[str, Any]],
    permalink: str | None,
    force: bool = False,
    processed: set[str] | None = None,
) -> Path:
    path = destination_path(mode, thread_file_name(event))
    processed = processed_paths() if processed is None else processed
    if mode == "inbox" and path.exists() and is_processed(path, processed) and not force:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_thread_markdown(
            channel=str(event["channel"]),
            thread_ts_value=thread_ts(event),
            messages=messages,
            permalink=permalink,
        ),
        encoding="utf-8",
    )
    return path


def promote_slack_thread(path: str, force: bool = False) -> dict[str, Any]:
    source = safe_inbox_path(path)
    rel = source.resolve().relative_to(INBOX_PATH.resolve())
    if not rel.parts or rel.parts[0] != "slack":
        raise PathNotAllowedError("Only files under inbox/slack/ can be promoted with promote-slack-thread")
    destination = safe_corpus_path(str(CORPUS_PATH / rel))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return {"status": "exists", "source": str(source.relative_to(PROJECT_ROOT)), "destination": str(destination.relative_to(PROJECT_ROOT)), "note": INGEST_REMINDER}
    shutil.copy2(source, destination)
    return {"status": "promoted", "source": str(source.relative_to(PROJECT_ROOT)), "destination": str(destination.relative_to(PROJECT_ROOT)), "note": INGEST_REMINDER}
```

- [ ] **Step 4: Verify core tests pass**

```bash
uv run pytest tests/test_slack_ingest.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add institutional_memory/slack_ingest.py tests/test_slack_ingest.py
git commit -m "feat: add Slack ingestion core helpers"
```

---

### Task 5: One-Shot Slack Sync And Promote CLI

**Files:**
- Modify: `institutional_memory/slack_ingest.py`
- Modify: `institutional_memory/cli.py`
- Test: `tests/test_slack_ingest.py`
- Test: `tests/test_cli_json.py`

- [ ] **Step 1: Add failing sync tests with fake Slack client**

Add to `tests/test_slack_ingest.py`:

```python
class FakeSlackClient:
    def conversations_history(self, channel, limit):
        return {
            "messages": [
                {"channel": channel, "ts": "1710000000.000000", "user": "U123", "text": "Need precedent"},
                {"channel": channel, "ts": "1710000002.000000", "bot_id": "B123", "text": "ignore bot"},
            ]
        }

    def conversations_replies(self, channel, ts):
        return {"messages": [{"channel": channel, "ts": ts, "user": "U123", "text": "Need precedent"}]}

    def chat_getPermalink(self, channel, message_ts):
        return {"permalink": f"https://example.slack.com/archives/{channel}/p{message_ts.replace('.', '')}"}


def test_sync_slack_history_writes_inbox_files(tmp_path, monkeypatch):
    monkeypatch.setattr(slack_ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(slack_ingest, "INBOX_PATH", tmp_path / "inbox")
    monkeypatch.setattr(slack_ingest, "CORPUS_PATH", tmp_path / "corpus")
    monkeypatch.setattr(slack_ingest, "load_processed_records", lambda: [])

    result = slack_ingest.sync_slack_history(mode="inbox", channel="C123", limit=20, client=FakeSlackClient(), sleep_seconds=0)

    assert result["status"] == "ok"
    assert result["written"] == ["inbox/slack/C123_1710000000.000000.md"]
    assert (tmp_path / "inbox/slack/C123_1710000000.000000.md").exists()


def test_sync_slack_history_corpus_includes_ingest_reminder(tmp_path, monkeypatch):
    monkeypatch.setattr(slack_ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(slack_ingest, "INBOX_PATH", tmp_path / "inbox")
    monkeypatch.setattr(slack_ingest, "CORPUS_PATH", tmp_path / "corpus")

    result = slack_ingest.sync_slack_history(mode="corpus", channel="C123", limit=20, client=FakeSlackClient(), sleep_seconds=0)

    assert result["status"] == "ok"
    assert result["written"] == ["corpus/slack/C123_1710000000.000000.md"]
    assert "ingest_corpus.py --force" in result["note"]


def test_sync_slack_history_loads_processed_registry_once(tmp_path, monkeypatch):
    calls = 0

    def fake_processed_records():
        nonlocal calls
        calls += 1
        return []

    monkeypatch.setattr(slack_ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(slack_ingest, "INBOX_PATH", tmp_path / "inbox")
    monkeypatch.setattr(slack_ingest, "CORPUS_PATH", tmp_path / "corpus")
    monkeypatch.setattr(slack_ingest, "load_processed_records", fake_processed_records)

    slack_ingest.sync_slack_history(mode="inbox", channel="C123", limit=20, client=FakeSlackClient(), sleep_seconds=0)

    assert calls == 1


class PartialFailureSlackClient(FakeSlackClient):
    def conversations_history(self, channel, limit):
        return {
            "messages": [
                {"channel": channel, "ts": "1710000000.000000", "user": "U123", "text": "bad thread"},
                {"channel": channel, "ts": "1710000001.000000", "user": "U456", "text": "good thread"},
            ]
        }

    def conversations_replies(self, channel, ts):
        if ts == "1710000000.000000":
            raise RuntimeError("thread not available")
        return {"messages": [{"channel": channel, "ts": ts, "user": "U456", "text": "good thread"}]}


def test_sync_slack_history_keeps_going_after_one_thread_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(slack_ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(slack_ingest, "INBOX_PATH", tmp_path / "inbox")
    monkeypatch.setattr(slack_ingest, "CORPUS_PATH", tmp_path / "corpus")
    monkeypatch.setattr(slack_ingest, "load_processed_records", lambda: [])

    result = slack_ingest.sync_slack_history(
        mode="inbox",
        channel="C123",
        limit=20,
        client=PartialFailureSlackClient(),
        sleep_seconds=0,
    )

    assert result["written"] == ["inbox/slack/C123_1710000001.000000.md"]
    assert result["errors"] == [{"ts": "1710000000.000000", "error": "thread not available"}]
```

- [ ] **Step 2: Add failing CLI tests**

Add to `tests/test_cli_json.py`:

```python
def test_sync_slack_cli_emits_json(monkeypatch, capsys):
    from institutional_memory import cli

    monkeypatch.setattr(
        "institutional_memory.slack_ingest.sync_slack_history",
        lambda **kwargs: {"status": "ok", "written": ["inbox/slack/C123_1710000000.000000.md"]},
    )

    args = cli.build_parser().parse_args(["sync-slack", "--mode", "inbox", "--channel", "C123", "--limit", "20"])
    assert args.func(args) == 0
    assert "inbox/slack/C123_1710000000.000000.md" in capsys.readouterr().out


def test_promote_slack_thread_cli_emits_json(monkeypatch, capsys):
    from institutional_memory import cli

    monkeypatch.setattr(
        "institutional_memory.slack_ingest.promote_slack_thread",
        lambda path, force=False: {"status": "promoted", "source": path, "destination": "corpus/slack/file.md"},
    )

    args = cli.build_parser().parse_args(["promote-slack-thread", "--path", "inbox/slack/file.md"])
    assert args.func(args) == 0
    assert "corpus/slack/file.md" in capsys.readouterr().out


def test_slack_operator_commands_are_visible_in_help():
    result = subprocess.run(["./bin/imem", "--help"], check=True, capture_output=True, text=True)

    assert "sync-slack" in result.stdout
    assert "promote-slack-thread" in result.stdout


def test_promote_slack_thread_subprocess_blocks_traversal_with_json_error():
    payload = run_imem("promote-slack-thread", "--path", "../.env")

    assert "error" in payload
```

- [ ] **Step 3: Run failing tests**

```bash
uv run pytest tests/test_slack_ingest.py tests/test_cli_json.py::test_sync_slack_cli_emits_json tests/test_cli_json.py::test_promote_slack_thread_cli_emits_json tests/test_cli_json.py::test_slack_operator_commands_are_visible_in_help tests/test_cli_json.py::test_promote_slack_thread_subprocess_blocks_traversal_with_json_error -q
```

Expected: fail until sync function and CLI commands exist.

- [ ] **Step 4: Implement sync function**

Add to `institutional_memory/slack_ingest.py`:

```python
def _client(client: WebClient | None = None) -> WebClient:
    if client is not None:
        return client
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN missing")
    return WebClient(token=SLACK_BOT_TOKEN)


def _permalink(web_client: WebClient, channel: str, ts: str) -> str | None:
    try:
        return web_client.chat_getPermalink(channel=channel, message_ts=ts).get("permalink")
    except SlackApiError:
        return None


def sync_slack_history(
    *,
    mode: Mode,
    channel: str,
    limit: int,
    client: WebClient | None = None,
    force: bool = False,
    sleep_seconds: float = 1.2,
) -> dict[str, Any]:
    web_client = _client(client)
    response = web_client.conversations_history(channel=channel, limit=limit)
    processed = processed_paths()
    written: list[str] = []
    errors: list[dict[str, str]] = []
    skipped = 0
    for message in response.get("messages", []):
        event = {**message, "channel": channel}
        if should_ignore_event(event):
            skipped += 1
            continue
        root_ts = thread_ts(event)
        try:
            replies = web_client.conversations_replies(channel=channel, ts=root_ts).get("messages", [event])
        except Exception as exc:
            errors.append({"ts": root_ts, "error": str(exc)})
            continue
        path = write_thread_file(
            mode,
            event,
            replies,
            _permalink(web_client, channel, root_ts),
            force=force,
            processed=processed,
        )
        written.append(str(path.relative_to(PROJECT_ROOT)))
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    result: dict[str, Any] = {
        "status": "ok",
        "mode": mode,
        "channel": channel,
        "written": sorted(set(written)),
        "skipped": skipped,
        "errors": errors,
    }
    if mode == "corpus":
        result["note"] = INGEST_REMINDER
    return result
```

`sleep_seconds` is intentional rate-limit protection. The CLI default of `1.2`
keeps large imports from making `conversations_replies` and `chat_getPermalink`
calls in a tight loop; tests pass `sleep_seconds=0`.

- [ ] **Step 5: Implement CLI commands**

In `institutional_memory/cli.py`, add:

```python
def cmd_sync_slack(args: argparse.Namespace) -> int:
    from institutional_memory.slack_ingest import sync_slack_history

    try:
        result = sync_slack_history(
            mode=args.mode,
            channel=args.channel,
            limit=args.limit,
            force=args.force,
            sleep_seconds=args.sleep_seconds,
        )
    except Exception as exc:
        return _emit_error(f"sync slack failed: {exc}", "slack_sync_failed", channel=args.channel, mode=args.mode)
    log_event("slack_synced", **result)
    emit(result)
    return 0


def cmd_promote_slack_thread(args: argparse.Namespace) -> int:
    from institutional_memory.slack_ingest import promote_slack_thread

    try:
        result = promote_slack_thread(args.path, force=args.force)
    except Exception as exc:
        return _emit_error(f"promote slack thread failed: {exc}", "slack_promote_failed", path=args.path)
    log_event("slack_thread_promoted", **result)
    emit(result)
    return 0
```

Update the `visible_commands` string so operator commands are visible in
`./bin/imem --help`:

```python
    visible_commands = (
        "hello,list-new-drafts,read-draft,mark-processed,reset-demo,search-memory,"
        "send-slack,sync-slack,promote-slack-thread"
    )
```

Add parsers:

```python
    sync = sub.add_parser("sync-slack", help="Import Slack history into inbox or corpus")
    sync.add_argument("--mode", choices=["inbox", "corpus"], required=True)
    sync.add_argument("--channel", required=True)
    sync.add_argument("--limit", type=int, default=20)
    sync.add_argument("--sleep-seconds", type=float, default=1.2)
    sync.add_argument("--force", action="store_true")
    sync.set_defaults(func=cmd_sync_slack)

    promote = sub.add_parser("promote-slack-thread", help="Copy a Slack inbox artifact into corpus")
    promote.add_argument("--path", required=True)
    promote.add_argument("--force", action="store_true")
    promote.set_defaults(func=cmd_promote_slack_thread)
```

- [ ] **Step 6: Verify tests pass**

```bash
uv run pytest tests/test_slack_ingest.py tests/test_cli_json.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add institutional_memory/slack_ingest.py institutional_memory/cli.py tests/test_slack_ingest.py tests/test_cli_json.py
git commit -m "feat: add Slack sync operator commands"
```

---

### Task 6: Socket Mode Listener Outside OpenClaw

**Files:**
- Create: `scripts/slack_listener.py`
- Modify: `institutional_memory/slack_ingest.py`
- Test: `tests/test_slack_ingest.py`

- [ ] **Step 1: Write failing listener handler test**

Add to `tests/test_slack_ingest.py`:

```python
def test_handle_socket_event_writes_inbox_thread(tmp_path, monkeypatch):
    monkeypatch.setattr(slack_ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(slack_ingest, "INBOX_PATH", tmp_path / "inbox")
    monkeypatch.setattr(slack_ingest, "CORPUS_PATH", tmp_path / "corpus")
    monkeypatch.setattr(slack_ingest, "load_processed_records", lambda: [])

    event = {"type": "message", "channel": "C123", "ts": "1710000000.000000", "user": "U123", "text": "Need precedent"}
    result = slack_ingest.handle_message_event(event, client=FakeSlackClient())

    assert result["status"] == "written"
    assert result["path"] == "inbox/slack/C123_1710000000.000000.md"
```

- [ ] **Step 2: Run failing test**

```bash
uv run pytest tests/test_slack_ingest.py::test_handle_socket_event_writes_inbox_thread -q
```

Expected: fail until `handle_message_event` exists.

- [ ] **Step 3: Implement event handler**

Add to `institutional_memory/slack_ingest.py`:

```python
def handle_message_event(event: dict[str, Any], client: WebClient | None = None, force: bool = False) -> dict[str, Any]:
    if event.get("type") != "message":
        return {"status": "ignored", "reason": "not_message"}
    if should_ignore_event(event):
        return {"status": "ignored", "reason": "bot_or_subtype"}
    web_client = _client(client)
    channel = str(event["channel"])
    root_ts = thread_ts(event)
    replies = web_client.conversations_replies(channel=channel, ts=root_ts).get("messages", [event])
    path = write_thread_file("inbox", event, replies, _permalink(web_client, channel, root_ts), force=force)
    return {"status": "written", "path": str(path.relative_to(PROJECT_ROOT))}
```

- [ ] **Step 4: Create listener script**

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

- [ ] **Step 5: Verify tests pass**

```bash
uv run pytest tests/test_slack_ingest.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add institutional_memory/slack_ingest.py scripts/slack_listener.py tests/test_slack_ingest.py
git commit -m "feat: add Slack Socket Mode listener"
```

---

### Task 7: Optional DGX Check For Slack Ingestion

**Files:**
- Modify: `scripts/dgx_check.py`
- Test: `tests/test_dgx_check.py`

- [ ] **Step 1: Write failing check test**

Add to `tests/test_dgx_check.py`:

```python
def test_slack_ingestion_blockers_require_app_token(monkeypatch):
    import scripts.dgx_check as dgx_check

    monkeypatch.delenv("SLACK_APP_TOKEN", raising=False)

    assert dgx_check.slack_ingestion_blockers() == ["SLACK_APP_TOKEN missing"]
```

- [ ] **Step 2: Run failing test**

```bash
uv run pytest tests/test_dgx_check.py::test_slack_ingestion_blockers_require_app_token -q
```

Expected: fail until helper exists.

- [ ] **Step 3: Implement optional check**

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

In `main()`, add parser flag:

```python
    parser.add_argument("--check-slack-ingestion", action="store_true")
```

After `blockers.extend(slack_secret_blockers())`, add:

```python
    if args.check_slack_ingestion:
        blockers.extend(slack_ingestion_blockers())
```

- [ ] **Step 4: Verify check tests pass**

```bash
uv run pytest tests/test_dgx_check.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/dgx_check.py tests/test_dgx_check.py
git commit -m "feat: add optional Slack ingestion readiness check"
```

---

### Task 8: README Handoff

**Files:**
- Modify: `README.md`
- Test: `tests/test_readme_handoff.py`

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

- [ ] **Step 2: Run failing test**

```bash
uv run pytest tests/test_readme_handoff.py::test_readme_documents_slack_ingestion -q
```

Expected: fail until docs are added.

- [ ] **Step 3: Update README**

Add a `## Slack Ingestion` section after `## Slack Behavior`:

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

- [ ] **Step 4: Verify README tests pass**

```bash
uv run pytest tests/test_readme_handoff.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_readme_handoff.py
git commit -m "docs: document Slack ingestion handoff"
```

---

### Task 9: Final Local Verification

**Files:**
- No new source files unless verification reveals a bug.

- [ ] **Step 1: Run full tests**

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run focused command smoke test**

Do not run a live `sync-slack` smoke test on a machine whose `.env` has a real
`SLACK_BOT_TOKEN`; that would call Slack. Parser and JSON behavior are covered
by the subprocess tests in `tests/test_cli_json.py`.

```bash
./bin/imem promote-slack-thread --path ../.env
```

Expected: JSON error, no copy outside project, exit code 0 under the existing CLI error convention.

- [ ] **Step 3: Run normal DGX check without Slack ingestion**

```bash
uv run python scripts/dgx_check.py --skip-model-smoke --skip-backup-video
```

Expected: Slack ingestion token is not required unless `--check-slack-ingestion` is passed.

- [ ] **Step 4: Run optional DGX check**

```bash
uv run python scripts/dgx_check.py --skip-model-smoke --skip-backup-video --check-slack-ingestion
```

Expected on machines without `SLACK_APP_TOKEN`: blocker includes `SLACK_APP_TOKEN missing`.

- [ ] **Step 5: Commit fixes if needed**

If any verification bug required edits:

```bash
git add <changed-files>
git commit -m "fix: stabilize Slack ingestion verification"
```

If no edits were required, do not create an empty commit.

---

### Task 10: ASUS Manual Verification

**Files:**
- No source changes expected.

- [ ] **Step 1: Deploy or pull on ASUS**

```bash
cd ~/memory-claw
git pull origin main
export PATH=$HOME/.local/bin:$PATH
uv sync
```

Expected: checkout has Slack ingestion files.

- [ ] **Step 2: Configure ASUS `.env`**

```bash
nano .env
```

Required:

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

In a tmux pane or shell on ASUS:

```bash
uv run python scripts/slack_listener.py
```

Expected stdout:

```json
{"status": "listening"}
```

- [ ] **Step 5: Send one Slack test message**

In the configured Slack channel, send:

```text
Do we have old NHS liability cap precedent?
```

Expected: a file appears under `~/memory-claw/inbox/slack/`.

- [ ] **Step 6: Confirm OpenClaw sees it**

```bash
./bin/imem list-new-drafts
```

Expected: JSON array includes `inbox/slack/<channel>_<thread_ts>.md`.

- [ ] **Step 7: Process with OpenClaw**

Ask OpenClaw:

```text
Check the inbox now and process one new draft.
```

Expected: OpenClaw searches corpus and posts only a memory-backed answer if relevant memory exists.

- [ ] **Step 8: Promote one useful thread**

```bash
./bin/imem promote-slack-thread --path inbox/slack/<channel>_<thread_ts>.md
uv run python scripts/ingest_corpus.py --force
```

Expected: copied file exists in `corpus/slack/` and is searchable after ingest.

---

## Plan Self-Review

- Spec coverage: covers live listener outside OpenClaw, manual sync to inbox/corpus, manual promote, no auto-promote, recursive inbox discovery, source attribution regex, optional Slack ingestion readiness, docs, and ASUS verification.
- Placeholder scan: no unfinished-work markers remain.
- Type consistency: commands use `sync-slack`, `promote-slack-thread`, and `scripts/slack_listener.py`; paths use `inbox/slack/*.md` and `corpus/slack/*.md`; helper names are consistent across tasks.
- Review fixes covered: explicit `PROJECT_ROOT` import, HTML-unescaped previews, one processed-registry read per sync, visible operator commands, subprocess CLI smoke coverage, Slack-only promotion, `web_client` naming, no `thread_ts` parameter shadowing, per-thread sync errors, rate-limit sleep, Slack `.gitkeep` files, and top-level `Event` import.
