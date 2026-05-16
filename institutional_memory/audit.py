"""Append structured events to audit_log.jsonl."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from institutional_memory.config import AUDIT_LOG


def log_event(event_type: str, **fields: Any) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "driver": fields.pop("driver", os.getenv("IMEM_DRIVER", "openclaw")),
        **fields,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
