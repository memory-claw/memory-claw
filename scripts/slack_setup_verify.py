#!/usr/bin/env python3
"""Run ASUS Slack setup verification (plan steps 7-8)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _token_status() -> list[str]:
    blockers: list[str] = []
    env_text = (ROOT / ".env").read_text(encoding="utf-8")
    for line in env_text.splitlines():
        if line.startswith("SLACK_APP_TOKEN="):
            value = line.split("=", 1)[1].strip()
            if not value or value == "xapp-your-token-here":
                blockers.append("SLACK_APP_TOKEN is placeholder — run: uv run python scripts/prompt_slack_tokens.py")
        if line.startswith("SLACK_BOT_TOKEN="):
            value = line.split("=", 1)[1].strip()
            if not value.startswith("xoxb-") or "your-token" in value or "REPLACE" in value:
                blockers.append("SLACK_BOT_TOKEN missing or placeholder")
    return blockers


def _run(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (result.stdout or "") + (result.stderr or "")
        return result.returncode, out.strip()
    except subprocess.TimeoutExpired as exc:
        chunks: list[str] = []
        for stream in (exc.stdout, exc.stderr):
            if not stream:
                continue
            chunks.append(stream.decode("utf-8", errors="replace") if isinstance(stream, bytes) else stream)
        out = "".join(chunks).strip()
        return 0 if out else -1, out


def main() -> int:
    blockers = _token_status()
    if blockers:
        print(json.dumps({"ok": False, "blockers": blockers}, indent=2))
        return 1

    uv = str(Path.home() / ".local/bin/uv")
    steps: list[dict[str, object]] = []

    code, out = _run([uv, "run", "python", "scripts/dgx_check.py", "--skip-backup-video", "--check-slack-ingestion"], timeout=180)
    steps.append({"step": "dgx_check_slack_ingestion", "ok": code == 0, "output": out[-500:]})
    if code != 0:
        print(json.dumps({"ok": False, "steps": steps}, indent=2))
        return 1

    code, out = _run(["./bin/imem", "send-slack", "--message", "Slack setup verify smoke test"], timeout=30)
    steps.append({"step": "send_slack", "ok": code == 0 and '"status": "sent"' in out, "output": out})

    code, out = _run([uv, "run", "python", "scripts/ingest_corpus.py", "--force"], timeout=300)
    steps.append({"step": "ingest_corpus", "ok": code == 0, "output": out})

    code, out = _run([uv, "run", "python", "scripts/slack_listener.py"], timeout=8)
    listening = '"status": "listening"' in out
    steps.append({"step": "slack_listener_connect", "ok": listening, "output": out[-800:]})

    ok = all(bool(step.get("ok")) for step in steps)
    print(json.dumps({"ok": ok, "steps": steps}, indent=2))
    if ok:
        print("\nListener connect OK. Start for real: tmux new -s slack && uv run python scripts/slack_listener.py")
        print("Golden test: @Bot in #institutional-memory with RFP / clause 7.4 question.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
