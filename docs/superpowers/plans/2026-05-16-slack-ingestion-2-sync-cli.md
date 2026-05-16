# Slack Ingestion Sync And CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Slack ingestion core module and one-shot operator CLI commands for manual Slack import and manual Slack-thread promotion.

**Architecture:** This branch builds on the foundation branch. It owns `institutional_memory/slack_ingest.py` and the Slack operator command surface in `institutional_memory/cli.py`. It must not add the long-running listener script or README handoff; those belong to branch 3.

**Tech Stack:** Python 3.12+, `slack-sdk` WebClient, argparse, markdown files, pytest.

---

## Branch

- Branch: `codex/slack-ingestion-sync-cli`
- Base: `codex/slack-ingestion-foundation` after it is pushed or merged.
- Merge second.
- Owned files: `institutional_memory/slack_ingest.py`, `institutional_memory/cli.py`, `tests/test_slack_ingest.py`, `tests/test_cli_json.py`.
- Do not edit `scripts/slack_listener.py`, `scripts/dgx_check.py`, or `README.md`.

---

### Task 1: Slack Ingestion Core Helpers

- [ ] **Step 1: Create failing tests**

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


def test_render_thread_markdown_contains_metadata_and_unescaped_messages():
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
    return f"{event['channel']}_{thread_ts(event)}.md"


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
```

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/test_slack_ingest.py -q
git add institutional_memory/slack_ingest.py tests/test_slack_ingest.py
git commit -m "feat: add Slack ingestion core helpers"
```

---

### Task 2: Manual Sync And Promotion Logic

- [ ] **Step 1: Add failing sync and promote tests**

Append to `tests/test_slack_ingest.py`:

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


def test_sync_slack_history_corpus_includes_ingest_reminder(tmp_path, monkeypatch):
    monkeypatch.setattr(slack_ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(slack_ingest, "INBOX_PATH", tmp_path / "inbox")
    monkeypatch.setattr(slack_ingest, "CORPUS_PATH", tmp_path / "corpus")

    result = slack_ingest.sync_slack_history(mode="corpus", channel="C123", limit=20, client=FakeSlackClient(), sleep_seconds=0)

    assert result["written"] == ["corpus/slack/C123_1710000000.000000.md"]
    assert "ingest_corpus.py --force" in result["note"]


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

- [ ] **Step 2: Implement sync and promote functions**

Append to `institutional_memory/slack_ingest.py`:

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

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest tests/test_slack_ingest.py -q
git add institutional_memory/slack_ingest.py tests/test_slack_ingest.py
git commit -m "feat: add Slack history sync helpers"
```

---

### Task 3: Operator CLI Commands

- [ ] **Step 1: Add failing CLI tests**

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


def test_promote_slack_thread_subprocess_blocks_traversal_with_json_error():
    payload = run_imem("promote-slack-thread", "--path", "../.env")

    assert "error" in payload


def test_slack_operator_commands_are_visible_in_help():
    result = subprocess.run(["./bin/imem", "--help"], check=True, capture_output=True, text=True)

    assert "sync-slack" in result.stdout
    assert "promote-slack-thread" in result.stdout
```

- [ ] **Step 2: Implement CLI functions and parsers**

In `institutional_memory/cli.py`, add `cmd_sync_slack` and `cmd_promote_slack_thread`, update `visible_commands`, and add parsers:

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

```python
    visible_commands = (
        "hello,list-new-drafts,read-draft,mark-processed,reset-demo,search-memory,"
        "send-slack,sync-slack,promote-slack-thread"
    )
```

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

- [ ] **Step 3: Add `reset-demo --clear-slack-inbox`**

Add a parser argument and cleanup block in `cmd_reset_demo()`:

```python
    reset.add_argument("--clear-slack-inbox", action="store_true")
```

```python
    if args.clear_slack_inbox:
        slack_inbox = PROJECT_ROOT / "inbox" / "slack"
        if slack_inbox.exists():
            for child in slack_inbox.rglob("*"):
                if child.is_file() and child.name != ".gitkeep":
                    child.unlink(missing_ok=True)
```

Include `clear_slack_inbox` in the reset JSON output.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/test_slack_ingest.py tests/test_cli_json.py -q
git add institutional_memory/slack_ingest.py institutional_memory/cli.py tests/test_slack_ingest.py tests/test_cli_json.py
git commit -m "feat: add Slack sync operator commands"
```

---

### Task 4: Branch Verification

- [ ] **Step 1: Run focused tests**

```bash
uv run pytest tests/test_slack_ingest.py tests/test_cli_json.py tests/test_drafts.py tests/test_paths.py -q
```

Expected: pass after foundation branch is present.

- [ ] **Step 2: Push branch**

```bash
git push -u origin codex/slack-ingestion-sync-cli
```

Expected: branch pushed and ready to merge after foundation.
