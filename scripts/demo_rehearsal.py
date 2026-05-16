from __future__ import annotations

import argparse
import json
import subprocess
import sys

from institutional_memory.config import PROJECT_ROOT


def run_json(*args: str):
    result = subprocess.run(
        ["./bin/imem", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Mac-local demo rehearsal")
    parser.add_argument("--skip-ingest", action="store_true")
    args = parser.parse_args()

    run_json("reset-demo", "--clear-audit")
    if not args.skip_ingest:
        subprocess.run(
            ["uv", "run", "python", "scripts/ingest_corpus.py", "--force"],
            cwd=PROJECT_ROOT,
            check=True,
        )
    rfp = run_json("search-memory", "--query", "RFP liability indemnification clause")
    silent = run_json("search-memory", "--query", "clinical trial dermatology placebo")
    ok = isinstance(rfp, list) and rfp and rfp[0].get("source") == "company/corpus/2023_rfp_postmortem.txt" and silent == []
    print(json.dumps({"rfp": rfp[:1] if isinstance(rfp, list) else rfp, "silent": silent, "ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
