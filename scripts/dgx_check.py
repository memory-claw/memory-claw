from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import subprocess
from pathlib import Path
from collections.abc import Callable

import ollama

from institutional_memory.config import (
    DEMO_ARTIFACTS_PATH,
    LLM_MODEL,
    OLLAMA_BASE_URL,
    PROJECT_ROOT,
    SLACK_BOT_TOKEN,
    SLACK_CHANNEL,
)

EXAMPLE_SLACK_TOKEN = "xoxb-your-token-here"


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


def default_model_probe() -> str:
    response = ollama.Client(host=OLLAMA_BASE_URL).chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": "Reply with READY."}],
        options={"num_predict": 8},
    )
    return response["message"]["content"]


def _model_smoke_worker(probe: Callable[[], str], queue: mp.Queue) -> None:
    try:
        queue.put({"ok": True, "content": probe()})
    except Exception as exc:
        queue.put({"ok": False, "error": str(exc)})


def model_smoke(
    probe: Callable[[], str] = default_model_probe,
    timeout_seconds: float = 90,
) -> tuple[bool, str]:
    queue: mp.Queue = mp.Queue()
    process = mp.Process(target=_model_smoke_worker, args=(probe, queue))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        return False, f"model smoke timed out after {timeout_seconds:g}s"
    result = queue.get() if not queue.empty() else {"ok": False, "error": "model smoke returned no result"}
    if not result["ok"]:
        return False, f"model smoke failed: {result['error']}"
    if "READY" not in result["content"].upper():
        return False, "model smoke did not return READY"
    return True, "model smoke returned READY"


def backup_video_blockers(path: Path = DEMO_ARTIFACTS_PATH) -> list[str]:
    videos = sorted(list(path.glob("*.mov")) + list(path.glob("*.mp4")))
    if not videos:
        return ["backup video missing under demo_artifacts/"]
    if any(video.stat().st_size > 0 for video in videos):
        return []
    empty = ", ".join(video.name for video in videos)
    return [f"backup video is empty: {empty}"]


def slack_secret_blockers(token: str | None = None, channel: str | None = None) -> list[str]:
    token = token if token is not None else os.getenv("SLACK_BOT_TOKEN")
    channel = channel if channel is not None else os.getenv("SLACK_CHANNEL")
    blockers: list[str] = []
    if not token:
        blockers.append("SLACK_BOT_TOKEN missing")
    elif token == EXAMPLE_SLACK_TOKEN:
        blockers.append("SLACK_BOT_TOKEN is still the .env.example placeholder")
    if not channel:
        blockers.append("SLACK_CHANNEL missing")
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description="DGX/ASUS readiness check")
    parser.add_argument("--skip-model-smoke", action="store_true")
    parser.add_argument("--skip-backup-video", action="store_true")
    args = parser.parse_args()
    blockers: list[str] = []

    code, output = run("uv", "run", "pytest", "-q", timeout=180)
    if code != 0:
        blockers.append(f"pytest failed: {output[-1000:]}")

    blockers.extend(slack_secret_blockers())

    if not args.skip_model_smoke:
        ok, message = model_smoke()
        if not ok:
            blockers.append(message)

    if not args.skip_backup_video:
        blockers.extend(backup_video_blockers())

    print(json.dumps({"ok": not blockers, "blockers": blockers}, ensure_ascii=False))
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
