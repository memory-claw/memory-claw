"""Processed draft registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from institutional_memory.config import PROCESSED_REGISTRY


def load_processed() -> list[str]:
    if not Path(PROCESSED_REGISTRY).exists():
        return []
    return json.loads(Path(PROCESSED_REGISTRY).read_text(encoding="utf-8"))


def load_processed_records() -> list[dict[str, Any]]:
    processed = load_processed()
    records: list[dict[str, Any]] = []
    for item in processed:
        if isinstance(item, str):
            records.append({"path": item})
        elif isinstance(item, dict):
            records.append(item)
    return records


def mark_as_processed(path: str, **fields: Any) -> None:
    processed = load_processed()
    if not fields:
        if path not in {item if isinstance(item, str) else item.get("path") for item in processed}:
            processed.append(path)
        Path(PROCESSED_REGISTRY).write_text(
            json.dumps(processed, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return

    records = load_processed_records()
    existing = next((record for record in records if record.get("path") == path), None)
    if existing is None:
        records.append({"path": path, **fields})
    else:
        existing.update(fields)
    Path(PROCESSED_REGISTRY).write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def reset_processed() -> None:
    Path(PROCESSED_REGISTRY).write_text("[]", encoding="utf-8")
