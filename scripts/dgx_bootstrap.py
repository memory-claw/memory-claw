from __future__ import annotations

import argparse


COMMANDS = [
    "uv sync",
    "ollama pull qwen3-embedding:8b",
    "ollama pull nemotron-3-super:120b",
    "cp .env.example .env  # then set Slack secrets",
    "./bin/imem reset-demo --clear-audit --clear-chroma",
    "uv run python scripts/ingest_corpus.py --force",
    "uv run python scripts/dgx_check.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Print DGX/ASUS bootstrap sequence")
    parser.add_argument("--dry-run", action="store_true")
    parser.parse_args()
    for command in COMMANDS:
        print(command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
