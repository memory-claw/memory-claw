from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

import ollama

from institutional_memory.config import (
    DEMO_ARTIFACTS_PATH,
    LLM_MODEL,
    OLLAMA_BASE_URL,
    PROJECT_ROOT,
    SLACK_BOT_TOKEN,
    SLACK_CHANNEL,
)


def run(*command: str, timeout: int = 120) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s: {' '.join(command)}"
    return result.returncode, result.stdout + result.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description="DGX/ASUS readiness check")
    parser.add_argument("--skip-model-smoke", action="store_true")
    parser.add_argument("--skip-backup-video", action="store_true")
    args = parser.parse_args()
    blockers: list[str] = []

    code, output = run("uv", "run", "pytest", "-q", timeout=180)
    if code != 0:
        blockers.append(f"pytest failed: {output[-1000:]}")

    if not SLACK_BOT_TOKEN:
        blockers.append("SLACK_BOT_TOKEN missing")
    if not SLACK_CHANNEL:
        blockers.append("SLACK_CHANNEL missing")

    if not args.skip_model_smoke:
        try:
            response = ollama.Client(host=OLLAMA_BASE_URL).chat(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": "Reply with READY."}],
                options={"num_predict": 8},
            )
            if "READY" not in response["message"]["content"].upper():
                blockers.append("model smoke did not return READY")
        except Exception as exc:
            blockers.append(f"model smoke failed: {exc}")

    if not args.skip_backup_video:
        videos = list(DEMO_ARTIFACTS_PATH.glob("*.mov")) + list(DEMO_ARTIFACTS_PATH.glob("*.mp4"))
        if not videos:
            blockers.append("backup video missing under demo_artifacts/")

    print(json.dumps({"ok": not blockers, "blockers": blockers}, ensure_ascii=False))
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
