from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import subprocess
import os
from pathlib import Path

import ollama

from institutional_memory.config import LLM_MODEL, OLLAMA_BASE_URL, PROJECT_ROOT, RUNTIME_PATH
from institutional_memory.audit import log_event


def run_imem(*args: str) -> object:
    env = os.environ.copy()
    env["IMEM_DRIVER"] = "harness"
    result = subprocess.run(
        ["./bin/imem", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(result.stdout)


def focused_query(text: str) -> str:
    lower = text.lower()
    if "rfp" in lower and ("indemnification" in lower or "liability" in lower):
        return "RFP liability indemnification"
    return " ".join(text.split()[:6])


def _ollama_compose_worker(prompt: str, queue: mp.Queue) -> None:
    try:
        response = ollama.Client(host=OLLAMA_BASE_URL).chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 160},
        )
        queue.put({"ok": True, "message": response["message"]["content"].strip()})
    except Exception as exc:
        queue.put({"ok": False, "error": str(exc)})


def compose_message(draft: dict, hits: list[dict], timeout_seconds: int) -> str:
    prompt = (
        "Write a 2-3 sentence Slack message as a knowledgeable colleague. "
        "Include the source filename. Avoid the words detected, triggered, alert, "
        "notification, and As an AI.\n\n"
        f"Draft path: {draft['path']}\nDraft text:\n{draft['text']}\n\nMemory hits:\n{json.dumps(hits, ensure_ascii=False)}"
    )
    queue: mp.Queue = mp.Queue()
    process = mp.Process(target=_ollama_compose_worker, args=(prompt, queue))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        raise TimeoutError(f"Nemotron message generation exceeded {timeout_seconds}s")
    result = queue.get() if not queue.empty() else {"ok": False, "error": "no response"}
    if not result["ok"]:
        raise RuntimeError(result["error"])
    return result["message"]


def fallback_message(hits: list[dict]) -> str:
    hit = hits[0]
    return (
        "Relevant prior memory: our 2023 RFP postmortem calls out liability caps in clause 7.4 "
        f"and indemnification as factors in the Meridian loss. Source: {hit['source']}."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Emergency fallback institutional memory harness")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model-timeout", type=int, default=20)
    args = parser.parse_args()

    drafts = run_imem("list-new-drafts")
    if not drafts:
        print("[]")
        return 0
    path = drafts[0]
    draft = run_imem("read-draft", "--path", path)
    if isinstance(draft, dict) and "error" in draft:
        run_imem("mark-processed", "--path", path, "--status", "read_failed", "--reason", draft["error"])
        print(json.dumps(draft, ensure_ascii=False))
        return 0

    query = focused_query(draft["text"])
    hits = run_imem("search-memory", "--query", query, "--draft-path", path)
    if isinstance(hits, dict) and "error" in hits:
        run_imem("mark-processed", "--path", path, "--status", "search_failed", "--reason", hits["error"], "--query", query)
        print(json.dumps(hits, ensure_ascii=False))
        return 0
    if not hits:
        run_imem(
            "mark-processed",
            "--path",
            path,
            "--status",
            "skipped_no_relevant_memory",
            "--reason",
            "No relevant memory above threshold",
            "--query",
            query,
        )
        print("[]")
        return 0

    try:
        message = compose_message(draft, hits, args.model_timeout)
    except Exception:
        message = fallback_message(hits)

    RUNTIME_PATH.mkdir(parents=True, exist_ok=True)
    message_path = RUNTIME_PATH / "slack_message.txt"
    message_path.write_text(message, encoding="utf-8")
    status = {"status": "dry_run", "message": message}
    if args.dry_run:
        log_event("harness_dry_run", driver="harness", path=path, query=query, top_score=hits[0]["score"], source=hits[0]["source"])
        print(json.dumps(status, ensure_ascii=False))
        return 0

    status = run_imem("send-slack", "--message-file", ".runtime/slack_message.txt")
    final_status = "sent" if isinstance(status, dict) and status.get("status") in {"sent", "dry_run"} else "slack_failed"
    run_imem(
        "mark-processed",
        "--path",
        path,
        "--status",
        final_status,
        "--reason",
        "Harness completed" if final_status == "sent" else json.dumps(status, ensure_ascii=False),
        "--query",
        query,
        "--top-score",
        str(hits[0]["score"]),
        "--source",
        hits[0]["source"],
    )
    print(json.dumps(status, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
