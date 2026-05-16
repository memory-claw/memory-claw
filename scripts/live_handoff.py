from __future__ import annotations


STEPS = [
    "1. uv sync",
    "2. cp .env.example .env and set SLACK_BOT_TOKEN plus SLACK_CHANNEL",
    "3. ollama pull qwen3-embedding:8b",
    "4. ollama pull nemotron-3-super:120b",
    "5. uv run python scripts/dgx_check.py --skip-model-smoke --skip-backup-video",
    "6. ./bin/imem reset-demo --clear-audit --clear-chroma",
    "7. uv run python scripts/ingest_corpus.py --force",
    "8. uv run python scripts/cosine_sanity.py",
    "9. Configure OpenClaw native Ollama provider with model ollama/nemotron-3-super:120b and baseUrl http://127.0.0.1:11434",
    "10. Allowlist only the absolute bin/imem wrapper path",
    "11. Ask OpenClaw: Check the inbox now and process one new draft.",
    "12. Verify Slack, audit_log.jsonl, and silent-case skipped_no_relevant_memory.",
    "13. Record backup video under demo_artifacts/.",
    "14. Run uv run python scripts/final_gate.py without skip flags.",
]


def main() -> int:
    print("\n".join(STEPS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
