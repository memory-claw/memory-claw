from __future__ import annotations

import json
import subprocess
from pathlib import Path

from institutional_memory.config import AUDIT_LOG, PROJECT_ROOT

GENERIC_QUERY_WORDS = {
    "draft",
    "new",
    "rfp",
    "memory",
    "context",
    "document",
    "file",
    "inbox",
    "search",
}


def run(command: list[str], timeout: int = 180) -> dict:
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "command": command,
            "ok": result.returncode == 0,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"command": command, "ok": False, "error": f"timeout after {timeout}s"}


def audit_blockers(audit_text: str | None = None) -> list[str]:
    if audit_text is None and not AUDIT_LOG.exists():
        return ["audit_log.jsonl missing"]
    if audit_text is None:
        audit_text = AUDIT_LOG.read_text(encoding="utf-8")
    events = []
    blockers = []
    for line_number, line in enumerate(audit_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            blockers.append(f"malformed audit line {line_number}")
            continue
        if not isinstance(event, dict):
            blockers.append(f"non-object audit line {line_number}")
            continue
        events.append(event)
    required = {"draft_listed", "draft_read", "memory_searched", "slack_sent", "processed"}
    seen = {event.get("type") for event in events}
    blockers.extend(f"missing audit event: {event}" for event in sorted(required - seen))
    processed_statuses = {
        event.get("status")
        for event in events
        if event.get("type") == "processed" and event.get("driver") == "openclaw"
    }
    if "sent" not in processed_statuses:
        blockers.append("missing success processed proof")
    if "skipped_no_relevant_memory" not in processed_statuses:
        blockers.append("missing silent-case processed proof")
    if not any(
        event.get("type") == "memory_searched"
        and event.get("driver") == "openclaw"
        and isinstance(event.get("count"), int)
        and event.get("count") > 0
        for event in events
    ):
        blockers.append("missing success positive-hit search proof")
    if not any(
        event.get("type") == "memory_searched"
        and event.get("driver") == "openclaw"
        and event.get("count") == 0
        for event in events
    ):
        blockers.append("missing silent zero-hit search proof")
    if not any(
        event.get("type") == "slack_sent"
        and event.get("driver") == "openclaw"
        and event.get("status") == "sent"
        for event in events
    ):
        blockers.append("missing sent Slack proof")
    for event in events:
        if event.get("type") in required and event.get("driver") != "openclaw":
            blockers.append(f"non-openclaw proof for {event.get('type')}: {event.get('driver')}")
        if event.get("type") == "memory_searched":
            query = str(event.get("query", ""))
            words = query.split()
            if not (2 <= len(words) <= 6):
                blockers.append(f"query not focused 2-6 words: {query}")
            normalized_words = {word.strip(".,:;!?()[]{}").lower() for word in words}
            if normalized_words and normalized_words <= GENERIC_QUERY_WORDS:
                blockers.append(f"generic search query: {query}")
            if len(words) >= 25 or len(query) >= 180:
                blockers.append(f"full-draft-style search query: {query[:120]}")
    return blockers


def main() -> int:
    audit_text = AUDIT_LOG.read_text(encoding="utf-8") if AUDIT_LOG.exists() else None
    checks = [
        run(["uv", "run", "pytest", "-q"]),
        run(["uv", "run", "python", "scripts/cosine_sanity.py"]),
        run(["uv", "run", "python", "scripts/nemoclaw_scaffold_check.py"]),
        run(["uv", "run", "python", "scripts/dgx_check.py"]),
    ]
    blockers = [check for check in checks if not check["ok"]]
    blockers.extend({"command": ["audit"], "ok": False, "error": item} for item in audit_blockers(audit_text))
    print(json.dumps({"ok": not blockers, "blockers": blockers}, ensure_ascii=False, indent=2))
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
