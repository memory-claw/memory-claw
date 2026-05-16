"""Optional hook to nudge OpenClaw after the listener writes a new inbox file."""

from __future__ import annotations

import subprocess
from typing import Any

from institutional_memory.audit import log_event
from institutional_memory.config import OPENCLAW_WAKE_CMD


def maybe_wake_openclaw(ingest_result: dict[str, Any]) -> None:
    if ingest_result.get("status") != "written":
        return
    if not OPENCLAW_WAKE_CMD:
        return
    path = ingest_result.get("path")
    try:
        subprocess.Popen(
            OPENCLAW_WAKE_CMD,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        log_event("openclaw_wake", path=path, cmd=OPENCLAW_WAKE_CMD)
    except OSError as exc:
        log_event("openclaw_wake_failed", path=path, error=str(exc), cmd=OPENCLAW_WAKE_CMD)
