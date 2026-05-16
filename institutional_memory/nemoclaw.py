"""Local scaffold probes for the optional NemoClaw/OpenShell bonus."""

from __future__ import annotations

import urllib.request
from pathlib import Path


def run_probe(probe: str) -> dict:
    if probe == "denied-read":
        try:
            Path("/etc/passwd").read_text(encoding="utf-8")
        except OSError as exc:
            return {"status": "denied", "probe": probe, "error": str(exc)}
        return {"status": "unsafe_access_succeeded", "probe": probe}
    if probe == "denied-network":
        try:
            urllib.request.urlopen("https://example.com", timeout=5).read(1)
        except Exception as exc:
            return {"status": "denied", "probe": probe, "error": str(exc)}
        return {"status": "unsafe_access_succeeded", "probe": probe}
    return {"status": "error", "error": f"unknown probe: {probe}"}
