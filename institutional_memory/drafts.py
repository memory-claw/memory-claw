"""Inbox draft discovery and reading."""

from __future__ import annotations

from institutional_memory.config import INBOX_PATH, PROJECT_ROOT
from institutional_memory.documents import load_document_text
from institutional_memory.paths import safe_inbox_path
from institutional_memory.state import load_processed_records


def list_new_drafts() -> list[str]:
    if not INBOX_PATH.exists():
        return []
    processed = {record.get("path") for record in load_processed_records()}
    drafts: list[str] = []
    for path in sorted(INBOX_PATH.iterdir()):
        if path.name == ".gitkeep" or path.suffix.lower() not in {".txt", ".md", ".pdf"}:
            continue
        rel = str(path.resolve().relative_to(PROJECT_ROOT))
        if rel not in processed:
            drafts.append(rel)
    return drafts


def read_draft(path: str) -> dict[str, str]:
    safe_path = safe_inbox_path(path)
    return {"path": str(safe_path.relative_to(PROJECT_ROOT)), "text": load_document_text(safe_path)}
