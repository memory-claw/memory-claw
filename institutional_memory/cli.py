"""Institutional Memory Engine CLI."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from institutional_memory.audit import log_event
from institutional_memory.config import (
    AUDIT_LOG,
    CHROMA_PATH,
    COMPANY_INBOX_PATH,
    PROJECT_ROOT,
    RUNTIME_PATH,
)
from institutional_memory.drafts import list_new_drafts, read_draft
from institutional_memory.paths import PathNotAllowedError, safe_inbox_path
from institutional_memory.state import mark_as_processed, reset_processed

PROCESSED_STATUSES = {
    "sent",
    "skipped_no_relevant_memory",
    "search_failed",
    "slack_failed",
    "read_failed",
    "tool_error",
}


def emit(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False))


def _emit_error(message: str, event_type: str = "tool_error", **fields: Any) -> int:
    log_event(event_type, error=message, **fields)
    emit({"error": message})
    return 0


def cmd_hello(_: argparse.Namespace) -> int:
    emit({"status": "ok", "message": "hello from Python"})
    return 0


def cmd_list_new_drafts(_: argparse.Namespace) -> int:
    try:
        drafts = list_new_drafts()
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return _emit_error(f"list failed: {exc}")
    log_event("draft_listed", count=len(drafts), drafts=drafts)
    emit(drafts)
    return 0


def cmd_read_draft(args: argparse.Namespace) -> int:
    try:
        payload = read_draft(args.path)
    except (PathNotAllowedError, FileNotFoundError, ValueError, RuntimeError) as exc:
        return _emit_error(f"read failed: {exc}", "draft_read", path=args.path)
    log_event("draft_read", path=payload["path"], characters=len(payload["text"]))
    emit(payload)
    return 0


def cmd_mark_processed(args: argparse.Namespace) -> int:
    if args.status not in PROCESSED_STATUSES:
        return _emit_error(f"invalid status: {args.status}", path=args.path)
    try:
        safe_path = safe_inbox_path(args.path)
        rel_path = str(safe_path.relative_to(PROJECT_ROOT))
    except (PathNotAllowedError, ValueError) as exc:
        return _emit_error(f"mark failed: {exc}", "processed", path=args.path)
    fields = {
        "status": args.status,
        "reason": args.reason,
        "query": args.query,
        "top_score": args.top_score,
        "source": args.source,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
    mark_as_processed(rel_path, **{k: v for k, v in fields.items() if v is not None})
    log_event("processed", path=rel_path, **fields)
    emit({"status": args.status, "path": rel_path})
    return 0


def cmd_reset_demo(args: argparse.Namespace) -> int:
    RUNTIME_PATH.mkdir(parents=True, exist_ok=True)
    for child in RUNTIME_PATH.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)
    reset_processed()
    if args.clear_chroma:
        shutil.rmtree(CHROMA_PATH, ignore_errors=True)
        (PROJECT_ROOT / "ingested_files.json").unlink(missing_ok=True)
    if args.clear_slack_inbox:
        slack_inbox = COMPANY_INBOX_PATH / "slack"
        if slack_inbox.exists():
            for child in slack_inbox.rglob("*"):
                if child.is_file() and child.name != ".gitkeep":
                    child.unlink(missing_ok=True)
    if args.clear_audit:
        AUDIT_LOG.unlink(missing_ok=True)
    else:
        log_event("demo_reset", clear_chroma=args.clear_chroma, clear_slack_inbox=args.clear_slack_inbox)
    emit({"status": "reset", "clear_audit": args.clear_audit, "clear_chroma": args.clear_chroma, "clear_slack_inbox": args.clear_slack_inbox})
    return 0


def cmd_search_memory(args: argparse.Namespace) -> int:
    from institutional_memory.search import search_memory

    try:
        draft_text = None
        if args.draft_path:
            draft_text = read_draft(args.draft_path)["text"]
        hits = search_memory(args.query, threshold=args.threshold, top_k=args.top_k, draft_text=draft_text)
    except Exception as exc:
        return _emit_error(f"search failed: {exc}", "memory_searched", query=args.query)
    top = hits[0] if hits else {}
    log_event(
        "memory_searched",
        query=args.query,
        count=len(hits),
        top_score=top.get("score"),
        source=top.get("source"),
    )
    emit(hits)
    return 0


def cmd_send_slack(args: argparse.Namespace) -> int:
    from institutional_memory.slack import send_slack_message

    result = send_slack_message(args.channel, args.message_file, args.message, thread_ts=args.thread_ts)
    log_event("slack_sent", **result)
    emit(result)
    return 0


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


def cmd_nemoclaw_probe(args: argparse.Namespace) -> int:
    from institutional_memory.nemoclaw import run_probe

    emit(run_probe(args.probe))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="imem", description="Institutional Memory Engine")
    visible_commands = (
        "hello,list-new-drafts,read-draft,mark-processed,reset-demo,search-memory,"
        "send-slack,sync-slack,promote-slack-thread"
    )
    sub = parser.add_subparsers(
        dest="command",
        required=True,
        metavar=f"{{{visible_commands}}}",
    )

    hello = sub.add_parser("hello", help="Smoke test")
    hello.set_defaults(func=cmd_hello)

    list_drafts = sub.add_parser("list-new-drafts", help="List unprocessed inbox drafts")
    list_drafts.set_defaults(func=cmd_list_new_drafts)

    read = sub.add_parser("read-draft", help="Read one inbox draft")
    read.add_argument("--path", required=True)
    read.set_defaults(func=cmd_read_draft)

    mark = sub.add_parser("mark-processed", help="Mark a draft as processed")
    mark.add_argument("--path", required=True)
    mark.add_argument("--status", required=True)
    mark.add_argument("--reason", required=True)
    mark.add_argument("--query")
    mark.add_argument("--top-score", type=float)
    mark.add_argument("--source")
    mark.set_defaults(func=cmd_mark_processed)

    reset = sub.add_parser("reset-demo", help="Reset runtime demo state")
    reset.add_argument("--clear-audit", action="store_true")
    reset.add_argument("--clear-chroma", action="store_true")
    reset.add_argument("--clear-slack-inbox", action="store_true")
    reset.set_defaults(func=cmd_reset_demo)

    search = sub.add_parser("search-memory", help="Search persistent institutional memory")
    search.add_argument("--query", required=True)
    search.add_argument("--draft-path", help=argparse.SUPPRESS)
    search.add_argument("--threshold", type=float)
    search.add_argument("--top-k", type=int)
    search.set_defaults(func=cmd_search_memory)

    slack = sub.add_parser("send-slack", help="Send a Slack message")
    slack.add_argument("--message-file")
    slack.add_argument("--message")
    slack.add_argument("--channel")
    slack.add_argument("--thread-ts")
    slack.set_defaults(func=cmd_send_slack)

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

    probe = sub.add_parser("nemoclaw-probe", help=argparse.SUPPRESS)
    probe.add_argument("probe", choices=["denied-read", "denied-network"])
    probe.set_defaults(func=cmd_nemoclaw_probe)
    sub._choices_actions = [
        action for action in sub._choices_actions if action.dest != "nemoclaw-probe"
    ]

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
