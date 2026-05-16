from __future__ import annotations

import json
import subprocess
from pathlib import Path

from institutional_memory.config import AUDIT_LOG, PROJECT_ROOT


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


def audit_blockers() -> list[str]:
    if not AUDIT_LOG.exists():
        return ["audit_log.jsonl missing"]
    events = [json.loads(line) for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    required = {"draft_listed", "draft_read", "memory_searched", "slack_sent", "processed"}
    seen = {event.get("type") for event in events}
    blockers = [f"missing audit event: {event}" for event in sorted(required - seen)]
    for event in events:
        if event.get("type") in required and event.get("driver") != "openclaw":
            blockers.append(f"non-openclaw proof for {event.get('type')}: {event.get('driver')}")
        if event.get("type") == "memory_searched":
            query = str(event.get("query", ""))
            words = query.split()
            if not (2 <= len(words) <= 6):
                blockers.append(f"query not focused 2-6 words: {query}")
    return blockers


def main() -> int:
    checks = [
        run(["uv", "run", "pytest", "-q"]),
        run(["uv", "run", "python", "scripts/nemoclaw_scaffold_check.py"]),
        run(["uv", "run", "python", "scripts/dgx_check.py"]),
    ]
    blockers = [check for check in checks if not check["ok"]]
    blockers.extend({"command": ["audit"], "ok": False, "error": item} for item in audit_blockers())
    print(json.dumps({"ok": not blockers, "blockers": blockers}, ensure_ascii=False, indent=2))
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
