"""Local web dashboard for memory-claw — uses institutional_memory modules."""

from __future__ import annotations

import html
import json
import re
import shutil
import socket
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from institutional_memory.config import (
    AUDIT_LOG,
    CHROMA_COLLECTION,
    CHROMA_PATH,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COMPANY_CORPUS_PATH,
    COMPANY_INBOX_PATH,
    EMBEDDING_MODEL,
    LLM_MODEL,
    OLLAMA_BASE_URL,
    PROJECT_ROOT,
    RELEVANCE_THRESHOLD,
    RUNTIME_PATH,
    SLACK_BOT_TOKEN,
    SLACK_CHANNEL,
    SLACK_WEBHOOK_URL,
    TOP_K,
)
from institutional_memory.drafts import list_new_drafts, read_draft
from institutional_memory.ingest import (
    _fingerprint,
    _load_ingested,
    get_chroma_collection,
    ingest_folder,
)
from institutional_memory.state import load_processed_records

STATIC_DIR = Path(__file__).resolve().parent / "static"
SLACK_MESSAGE_PATH = RUNTIME_PATH / "slack_message.txt"
DOC_SUFFIXES = {".txt", ".md", ".pdf"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    yield


app = FastAPI(title="memory-claw dashboard", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_audit_lines() -> list[str]:
    if not AUDIT_LOG.is_file():
        return []
    try:
        return AUDIT_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _parse_audit_objects(lines: list[str] | None = None) -> list[dict[str, Any]]:
    lines = _read_audit_lines() if lines is None else lines
    out: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"raw": line, "ts": None, "type": "raw"})
    return out


def _format_ts_hhmm(ts: Any) -> str | None:
    if not ts:
        return None
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except (TypeError, ValueError, OSError):
        return None


def _format_ts_iso(ts: Any) -> str | None:
    if not ts:
        return None
    return str(ts)


def _iter_inbox_paths() -> list[Path]:
    if not COMPANY_INBOX_PATH.exists():
        return []
    paths: list[Path] = []
    for path in COMPANY_INBOX_PATH.rglob("*"):
        if not path.is_file():
            continue
        if path.name == ".gitkeep" or path.suffix.lower() not in DOC_SUFFIXES:
            continue
        paths.append(path)
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return paths


def _rel_inbox_path(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT))


def _processed_map() -> dict[str, dict[str, Any]]:
    return {
        str(record["path"]): record
        for record in load_processed_records()
        if record.get("path")
    }


def _count_corpus_docs() -> int:
    if not COMPANY_CORPUS_PATH.is_dir():
        return 0
    return sum(
        1
        for path in COMPANY_CORPUS_PATH.rglob("*")
        if path.is_file() and path.suffix.lower() in DOC_SUFFIXES
    )


def _list_corpus_paths() -> list[Path]:
    if not COMPANY_CORPUS_PATH.is_dir():
        return []
    return [
        path
        for path in COMPANY_CORPUS_PATH.rglob("*")
        if path.is_file() and path.suffix.lower() in DOC_SUFFIXES
    ]


def _audit_timeline_by_draft() -> dict[str, dict[str, Any]]:
    """Correlate audit events to inbox drafts via draft_read boundaries."""
    by_draft: dict[str, dict[str, Any]] = {}
    current: str | None = None
    for entry in _parse_audit_objects():
        event_type = str(entry.get("type") or "")
        if event_type == "draft_read" and entry.get("path"):
            current = str(entry["path"])
            by_draft.setdefault(
                current,
                {"draft_read_ts": entry.get("ts"), "events": []},
            )
        if current is None:
            continue
        slot = by_draft.setdefault(current, {"events": []})
        slot.setdefault("events", []).append(entry)
        if event_type == "memory_searched":
            slot["source"] = entry.get("source")
            slot["top_score"] = entry.get("top_score")
            slot["search_count"] = entry.get("count")
        elif event_type == "slack_sent":
            slot["slack_sent"] = entry
            slot["channel"] = entry.get("channel")
            attributions = entry.get("source_attributions")
            if isinstance(attributions, list) and attributions:
                slot["source"] = slot.get("source") or attributions[0]
        elif event_type == "processed":
            slot["processed"] = entry
            slot["status"] = entry.get("status")
            slot["reason"] = entry.get("reason")
            slot["top_score"] = slot.get("top_score") or entry.get("top_score")
            slot["source"] = slot.get("source") or entry.get("source")
    return by_draft


def _slack_message_text() -> str | None:
    if SLACK_MESSAGE_PATH.is_file():
        text = _read_text(SLACK_MESSAGE_PATH).strip()
        if text:
            return text
    return None


def _title_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title
    return fallback.replace("_", " ").replace("-", " ")


def _draft_status(rel_path: str, record: dict[str, Any] | None, audit: dict[str, Any]) -> str:
    if record is None:
        return "new"
    status = record.get("status")
    if status == "sent":
        return "sent"
    if status == "skipped_no_relevant_memory":
        return "skipped"
    audit_status = audit.get("status")
    if audit.get("slack_sent") or audit_status == "sent":
        return "sent"
    if audit_status == "skipped_no_relevant_memory":
        return "skipped"
    if status in {"search_failed", "slack_failed", "read_failed", "tool_error"}:
        return "processing"
    if audit.get("events"):
        return "processing"
    return "processing"


def _build_summary(
    status: str,
    *,
    source: str | None,
    score: float | None,
    channel: str | None,
    reason: str | None,
) -> str:
    if status == "new":
        return "Awaiting processing"
    if status == "skipped":
        detail = f" ({reason})" if reason else ""
        return f"No relevant memory found — message suppressed{detail}"
    if status == "processing":
        return "Processing in progress — awaiting final status"
    if status == "sent":
        src_name = Path(source).name if source else "corpus match"
        score_part = f" (score {score:.2f})" if score is not None else ""
        ch = channel or SLACK_CHANNEL
        return f"Matched {src_name}{score_part} — Slack message sent to {ch}"
    return "Awaiting processing"


def _humanize_mtime(mtime: float) -> str:
    import time

    delta = max(0, int(time.time() - mtime))
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{delta // 60}m ago"
    return f"{delta // 3600}h ago"


def _md_to_html(text: str) -> str:
    parts: list[str] = []
    in_pre = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_pre = not in_pre
            if in_pre:
                parts.append("<pre>")
            else:
                parts.append("</pre>")
            continue
        if in_pre:
            parts.append(html.escape(line))
            continue
        if line.startswith("# "):
            parts.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            parts.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            parts.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif not line.strip():
            parts.append("<br>")
        else:
            escaped = html.escape(line)
            escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
            parts.append(f"<p>{escaped}</p>")
    return "\n".join(parts)


def _ollama_ok() -> bool:
    base = OLLAMA_BASE_URL.rstrip("/")
    try:
        req = Request(f"{base}/api/tags", method="GET")
        with urlopen(req, timeout=2) as resp:
            return 200 <= resp.status < 300
    except (URLError, OSError, TimeoutError, ValueError):
        return False


def _chroma_ok() -> bool:
    try:
        get_chroma_collection().count()
        return True
    except Exception:
        return False


def _vector_chunks() -> int:
    try:
        return int(get_chroma_collection().count())
    except Exception:
        return 0


def _slack_sent_count() -> int:
    return sum(1 for e in _parse_audit_objects() if e.get("type") == "slack_sent")


def _listener_skip_stats(minutes: int = 60) -> dict[str, int]:
    cutoff = datetime.now(timezone.utc).timestamp() - (minutes * 60)
    counts: dict[str, int] = {}
    for event in _parse_audit_objects():
        if event.get("type") != "listener_skip":
            continue
        ts = event.get("ts")
        if ts:
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if dt.timestamp() < cutoff:
                    continue
            except (TypeError, ValueError):
                pass
        reason = str(event.get("reason") or "unknown")
        counts[reason] = counts.get(reason, 0) + 1
    return counts


def _infer_tag(rel_path: str) -> str:
    lower = rel_path.lower()
    if "policy" in lower:
        return "policy"
    if "postmortem" in lower or "incident" in lower:
        return "postmortem"
    if "contract" in lower or "clause" in lower:
        return "contract"
    if "slack" in lower:
        return "slack"
    if "rfp" in lower or "bid" in lower:
        return "rfp"
    return "doc"


def _chroma_chunks_for_source(rel: str) -> int | None:
    try:
        collection = get_chroma_collection()
        result = collection.get(where={"source": rel}, include=[])
        ids = result.get("ids") or []
        if ids:
            return len(ids)
    except Exception:
        pass
    return None


def _audit_message_text(entry: dict[str, Any]) -> str | None:
    for key in ("message", "text"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if entry.get("type") == "slack_sent":
        return _slack_message_text()
    return None


def _enrich_audit_entry(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("type") == "raw" and raw.get("raw"):
        return {
            "ts": None,
            "event": "raw",
            "message_preview": str(raw["raw"])[:80],
            "source": None,
            "draft": None,
            "full_message": None,
            "error": None,
            "ingest_detail": None,
        }

    event = str(raw.get("type") or "event")
    message = _audit_message_text(raw)
    preview = message[:80] if message and event == "slack_sent" else None
    full_message = message if event == "slack_sent" else None

    draft = None
    if raw.get("path"):
        draft = Path(str(raw["path"])).name

    error = None
    if event.endswith("_failed") or raw.get("status", "").endswith("failed") or raw.get("error"):
        error = str(raw.get("error") or raw.get("reason") or raw.get("status") or event)

    ingest_detail = None
    if event in {"demo_reset"} and raw.get("clear_chroma"):
        ingest_detail = "chroma cleared"
    elif "ingest" in event or event == "slack_synced":
        files = raw.get("files") or raw.get("imported") or raw.get("count")
        chunks = raw.get("chunks")
        if files is not None or chunks is not None:
            ingest_detail = f"+{files or 0} docs, {chunks or 0} chunks"

    display_event = event
    if event == "processed" and raw.get("status") == "skipped_no_relevant_memory":
        display_event = "skipped"

    source = raw.get("source")
    attributions = raw.get("source_attributions")
    if not source and isinstance(attributions, list) and attributions:
        source = attributions[0]

    return {
        "ts": _format_ts_hhmm(raw.get("ts")),
        "event": display_event,
        "message_preview": preview,
        "source": source,
        "draft": draft,
        "full_message": full_message,
        "error": error,
        "ingest_detail": ingest_detail,
        "status": raw.get("status"),
    }


def _inbox_item(rel_path: str, path: Path) -> dict[str, Any]:
    processed = _processed_map()
    audit_by_draft = _audit_timeline_by_draft()
    record = processed.get(rel_path)
    audit = audit_by_draft.get(rel_path, {})
    status = _draft_status(rel_path, record, audit)

    try:
        draft = read_draft(rel_path)
        text = draft.get("text", "")
    except Exception:
        draft = {"path": rel_path, "text": _read_text(path)}
        text = draft["text"]

    source = (
        (record or {}).get("source")
        or audit.get("source")
        or None
    )
    score = (record or {}).get("top_score")
    if score is None:
        score = audit.get("top_score")
    if score is not None:
        score = float(score)

    channel = audit.get("channel") or (audit.get("slack_sent") or {}).get("channel")
    if status == "sent" and not channel:
        channel = SLACK_CHANNEL

    title = _title_from_text(text, path.stem)
    reason = (record or {}).get("reason") or audit.get("reason")
    summary = _build_summary(
        status,
        source=source,
        score=score,
        channel=channel,
        reason=reason,
    )

    slack_message = _slack_message_text() if status == "sent" else None
    processed_at = (record or {}).get("processed_at") or (audit.get("processed") or {}).get(
        "processed_at"
    )

    log_lines: list[str] = []
    for ev in audit.get("events", []):
        ts = _format_ts_hhmm(ev.get("ts")) or "—"
        log_lines.append(f"[{ts}] {ev.get('type')} {json.dumps({k: v for k, v in ev.items() if k not in {'ts', 'type'}}, ensure_ascii=False)}")
    if slack_message and status == "sent":
        log_lines.append("\n--- .runtime/slack_message.txt ---\n")
        log_lines.append(slack_message)

    return {
        "path": rel_path,
        "name": path.name,
        "title": title,
        "summary": summary,
        "status": status,
        "matched_source": source,
        "score": score,
        "slack_channel": channel,
        "processed_content": "\n".join(log_lines) if log_lines else None,
        "mtime_ago": _humanize_mtime(path.stat().st_mtime),
        "processed_at": processed_at,
        "slack_message": slack_message,
        "skip_reason": reason if status == "skipped" else None,
    }


@app.get("/api/status")
def api_status() -> dict[str, Any]:
    return {
        "ollama_ok": _ollama_ok(),
        "slack_ok": bool(SLACK_BOT_TOKEN),
        "slack_webhook_ok": bool(SLACK_WEBHOOK_URL),
        "openclaw_ok": shutil.which("openclaw") is not None,
        "chroma_ok": _chroma_ok(),
        "machine": socket.gethostname(),
        "relevance_threshold": RELEVANCE_THRESHOLD,
        "chroma_path": str(CHROMA_PATH.relative_to(PROJECT_ROOT)),
        "chroma_collection": CHROMA_COLLECTION,
    }


@app.get("/api/stats")
def api_stats() -> dict[str, Any]:
    new_set = set(list_new_drafts())
    all_paths = [_rel_inbox_path(p) for p in _iter_inbox_paths()]
    skip_stats = _listener_skip_stats()
    return {
        "corpus_docs": _count_corpus_docs(),
        "inbox_total": len(all_paths),
        "inbox_unprocessed": len(new_set),
        "vector_chunks": _vector_chunks(),
        "slack_sent": _slack_sent_count(),
        "listener_skip_below_threshold": skip_stats.get("below_threshold", 0),
        "listener_skip_not_in_allowlist": skip_stats.get("not_in_allowlist", 0),
        "listener_skip_total": sum(skip_stats.values()),
    }


@app.get("/api/inbox")
def api_inbox() -> list[dict[str, Any]]:
    return [_inbox_item(_rel_inbox_path(path), path) for path in _iter_inbox_paths()]


def _inbox_detail_dict(path: str) -> dict[str, Any]:
    draft = read_draft(path)
    inbox_path = PROJECT_ROOT / draft["path"]
    if not inbox_path.is_file():
        raise HTTPException(status_code=404, detail="Draft file not found")
    item = _inbox_item(draft["path"], inbox_path)
    text = draft.get("text", "")
    return {
        **item,
        "body_markdown": text,
        "body_html": _md_to_html(text),
        "slack_channel_id": draft.get("slack_channel_id"),
        "slack_thread_ts": draft.get("slack_thread_ts"),
        "slack_permalink": draft.get("slack_permalink"),
    }


@app.get("/api/inbox/detail")
def api_inbox_detail(path: str = Query(..., description="Inbox path relative to repo root")) -> dict[str, Any]:
    try:
        return _inbox_detail_dict(path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/inbox/full")
def api_inbox_full() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for inbox_path in _iter_inbox_paths():
        rel = _rel_inbox_path(inbox_path)
        try:
            items.append(_inbox_detail_dict(rel))
        except HTTPException:
            continue
        except Exception:
            continue
    return items


@app.get("/inbox")
def inbox_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "inbox.html")


@app.get("/api/corpus")
def api_corpus() -> list[dict[str, Any]]:
    files = _list_corpus_paths()
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    items: list[dict[str, Any]] = []
    for path in files[:50]:
        rel = str(path.relative_to(COMPANY_CORPUS_PATH))
        full_rel = str(path.relative_to(PROJECT_ROOT))
        chunks = _chroma_chunks_for_source(full_rel)
        if chunks is None:
            try:
                size = path.stat().st_size
            except OSError:
                size = 800
            chunks = max(1, size // 800)
        items.append({"name": rel, "tag": _infer_tag(rel), "chunks": chunks})
    return items


@app.get("/api/audit")
def api_audit() -> list[dict[str, Any]]:
    lines = _read_audit_lines()
    tail = lines[-40:] if lines else []
    return [_enrich_audit_entry(obj) for obj in _parse_audit_objects(tail)]


@app.get("/api/model")
def api_model() -> dict[str, Any]:
    return {
        "inference_model": LLM_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "ollama_url": OLLAMA_BASE_URL,
        "relevance_threshold": RELEVANCE_THRESHOLD,
        "top_k": TOP_K,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "vector_db": f"chromadb ({CHROMA_PATH.name}/{CHROMA_COLLECTION})",
        "driver": "openclaw",
    }


def _page_css() -> str:
    return """
    :root {
      --teal: #1D9E75; --teal-light: #E1F5EE; --teal-dark: #0F6E56;
      --bg: #f8f7f4; --panel: #fff; --border: #e8e6e0;
      --text: #1a1a1a; --muted: #9b9b9b; --red: #c0392b; --green: #0F6E56;
      --font: ui-monospace, Menlo, Monaco, Consolas, monospace;
    }
    body { font-family: var(--font); background: var(--bg); color: var(--text); font-size: 13px; line-height: 1.5; margin: 0; }
    .wrap { max-width: 800px; margin: 0 auto; padding: 24px; }
    .back { color: var(--teal); text-decoration: none; font-size: 12px; }
    .back:hover { text-decoration: underline; }
    h1 { font-size: 20px; margin: 16px 0 8px; }
    .section {
      background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
      padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .section h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 8px; }
    .step { padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 12px; }
    .step:last-child { border-bottom: none; }
    .banner { padding: 16px; border-radius: 8px; font-weight: 700; font-size: 16px; margin: 16px 0; }
    .banner.pass { background: var(--teal-light); color: var(--green); border: 1px solid #b8e6d8; }
    .banner.fail { background: #fdeaea; color: var(--red); border: 1px solid #f0c0c0; }
    .blocker { font-size: 12px; padding: 8px; background: #fdeaea; border-radius: 6px; margin: 6px 0; }
    pre.raw { background: #f3f2ef; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 11px; }
    """


def _page_shell(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(title)} — memory-claw</title>
<style>{_page_css()}</style>
</head><body>
<div class="wrap">
<a class="back" href="/">← back to dashboard</a>
<h1>{html.escape(title)}</h1>
{body}
</div></body></html>"""


def _run_script(relative_script: str, timeout: int = 300) -> tuple[int, str, str]:
    result = subprocess.run(
        ["uv", "run", "python", relative_script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


@app.get("/checklist", response_class=HTMLResponse)
def checklist_page() -> str:
    code, stdout, stderr = _run_script("scripts/live_handoff.py", timeout=60)
    steps = [line.strip() for line in stdout.splitlines() if line.strip()]
    sections: list[str] = []
    for step in steps:
        sections.append(f'<div class="step">{html.escape(step)}</div>')
    if stderr.strip():
        sections.append(f'<div class="section"><h2>stderr</h2><pre class="raw">{html.escape(stderr)}</pre></div>')
    if not sections:
        sections.append('<p class="step">No output from live_handoff.py</p>')
    body = f'<p style="color:var(--muted);font-size:12px;margin-bottom:16px">Exit code: {code}</p>'
    body += '<div class="section"><h2>Live handoff steps</h2>' + "".join(sections) + "</div>"
    return _page_shell("checklist", body)


@app.get("/final-gate", response_class=HTMLResponse)
def final_gate_page() -> str:
    code, stdout, stderr = _run_script("scripts/final_gate.py", timeout=300)
    passed = code == 0
    banner = (
        '<div class="banner pass">PASS — final gate cleared</div>'
        if passed
        else '<div class="banner fail">FAIL — final gate blocked</div>'
    )
    body = banner
    try:
        data = json.loads(stdout)
        if not data.get("ok") and data.get("blockers"):
            for blocker in data["blockers"]:
                if isinstance(blocker, dict):
                    text = blocker.get("error") or json.dumps(blocker, ensure_ascii=False)
                else:
                    text = str(blocker)
                body += f'<div class="blocker">{html.escape(text)}</div>'
        elif data.get("ok"):
            body += '<p style="font-size:12px;color:var(--muted)">All checks passed.</p>'
    except json.JSONDecodeError:
        if stdout.strip():
            body += f'<pre class="raw">{html.escape(stdout)}</pre>'
    if stderr.strip():
        body += f'<div class="section"><h2>stderr</h2><pre class="raw">{html.escape(stderr)}</pre></div>'
    return _page_shell("final gate", body)


@app.post("/api/run/ingest")
def api_run_ingest() -> dict[str, Any]:
    registry_before = dict(_load_ingested())
    eligible = _list_corpus_paths()
    skipped = 0
    for path in eligible:
        rel = str(path.resolve().relative_to(PROJECT_ROOT))
        if registry_before.get(rel) == _fingerprint(path):
            skipped += 1

    result = ingest_folder(COMPANY_CORPUS_PATH, force=False)
    registry_after = _load_ingested()
    files_added = [
        rel
        for rel, fp in registry_after.items()
        if registry_before.get(rel) != fp
    ]

    return {
        "added": len(files_added),
        "skipped": skipped,
        "files_added": files_added,
        "chunks": result.get("chunks", 0),
        "files": result.get("files", 0),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run(
        "dashboard.app:app",
        host="0.0.0.0",
        port=7842,
        reload=False,
    )


if __name__ == "__main__":
    main()
