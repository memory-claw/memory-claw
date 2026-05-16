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
    "12. Verify Slack receives the RFP message and audit_log.jsonl has driver=openclaw, count > 0, source=corpus/2023_rfp_postmortem.txt, source_attributions includes corpus/2023_rfp_postmortem.txt, slack_sent status=sent, processed status=sent.",
    "13. ./bin/imem reset-demo",
    "14. uv run python scripts/demo_case.py silent (writes inbox/000_silent_clinical_trial_protocol.txt)",
    "15. Ask OpenClaw: Check the inbox now and process one new draft.",
    "16. Verify no Slack message posts and audit_log.jsonl has driver=openclaw, memory_searched count: 0, and processed status=skipped_no_relevant_memory.",
    "17. ./bin/imem reset-demo, then uv run python scripts/demo_case.py rfp, then wait for heartbeat to send the RFP Slack message.",
    "18. Record a non-empty .mp4 or .mov backup video under demo_artifacts/ showing OpenClaw, audit tail, inbox file drop, and Slack message.",
    "19. Run uv run python scripts/final_gate.py without skip flags.",
]


def main() -> int:
    print("\n".join(STEPS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
