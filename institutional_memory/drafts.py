"""Inbox draft discovery and reading."""

from __future__ import annotations

from pathlib import Path

from institutional_memory.config import COMPANY_INBOX_PATH, PROJECT_ROOT
from institutional_memory.documents import load_document_text
from institutional_memory.paths import safe_inbox_path
from institutional_memory.state import load_processed_records

SLACK_METADATA = {
    "channel": "slack_channel_id",
    "slack_channel_id": "slack_channel_id",
    "thread ts": "slack_thread_ts",
    "slack_thread_ts": "slack_thread_ts",
    "permalink": "slack_permalink",
    "slack_permalink": "slack_permalink",
}


def list_new_drafts() -> list[str]:
    processed = {record.get("path") for record in load_processed_records()}
    return sorted(_new_drafts_under(COMPANY_INBOX_PATH, processed))


def _new_drafts_under(root: Path, processed: set[str]) -> list[str]:
    if not root.exists():
        return []
    drafts: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == ".gitkeep" or path.suffix.lower() not in {".txt", ".md", ".pdf"}:
            continue
        rel = str(path.resolve().relative_to(PROJECT_ROOT))
        if rel not in processed:
            drafts.append(rel)
    return drafts


def _metadata_key(raw: str) -> str:
    key = raw.strip().strip("*").replace("_", " ").lower()
    return SLACK_METADATA.get(key, "")


def _slack_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in text.splitlines()[:40]:
        stripped = line.strip()
        if stripped.startswith("**") and ":**" in stripped:
            raw_key, value = stripped.split(":**", 1)
            key = _metadata_key(raw_key)
        elif ":" in stripped:
            raw_key, value = stripped.split(":", 1)
            key = _metadata_key(raw_key)
        else:
            continue
        value = value.strip()
        if key and value:
            metadata[key] = value
    return metadata


def read_draft(path: str) -> dict[str, str]:
    safe_path = safe_inbox_path(path)
    text = load_document_text(safe_path)
    return {
        "path": str(safe_path.relative_to(PROJECT_ROOT)),
        "text": text,
        **_slack_metadata(text),
    }
