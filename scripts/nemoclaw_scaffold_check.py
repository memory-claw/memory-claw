from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from institutional_memory.config import PROJECT_ROOT


REQUIRED = [
    "policies/openshell-policy.md",
    "nemoclaw/README.md",
    "institutional_memory/nemoclaw.py",
]


def main() -> int:
    missing = [path for path in REQUIRED if not (PROJECT_ROOT / path).exists()]
    probes = []
    for probe in ("denied-read", "denied-network"):
        result = subprocess.run(
            ["./bin/imem", "nemoclaw-probe", probe],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        probes.append(json.loads(result.stdout))
    ok = not missing and all(item.get("status") in {"denied", "unsafe_access_succeeded"} for item in probes)
    print(json.dumps({"ok": ok, "missing": missing, "probes": probes}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
