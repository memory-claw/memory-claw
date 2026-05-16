from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMEM_PATH = PROJECT_ROOT / "bin" / "imem"

STEPS = [
    "1. uv sync",
    "2. cp -n .env.example .env, then edit .env and set real SLACK_BOT_TOKEN plus SLACK_CHANNEL",
    "3. ollama pull qwen3-embedding:8b",
    "4. ollama pull nemotron-3-super:120b",
    "5. uv run python scripts/dgx_check.py --skip-model-smoke --skip-backup-video",
    "6. ./bin/imem reset-demo --clear-audit --clear-chroma",
    "7. uv run python scripts/ingest_corpus.py --force",
    "8. uv run python scripts/cosine_sanity.py",
    "9. Configure OpenClaw native Ollama provider with model ollama/nemotron-3-super:120b and baseUrl http://127.0.0.1:11434",
    f"10. Allowlist only this absolute wrapper path: {IMEM_PATH}",
    "11. Ask OpenClaw: Check the inbox now and process one new draft.",
    "12. Verify Slack receives the RFP message and audit_log.jsonl has ordered RFP proof: draft_read path=company/inbox/new_rfp_draft.txt, memory_searched count > 0 source=company/corpus/2023_rfp_postmortem.txt, slack_sent status=sent source_attributions includes company/corpus/2023_rfp_postmortem.txt, processed path=company/inbox/new_rfp_draft.txt status=sent.",
    "13. ./bin/imem reset-demo",
    "14. uv run python scripts/demo_case.py silent (writes company/inbox/000_silent_clinical_trial_protocol.txt)",
    "15. Ask OpenClaw: Check the inbox now and process one new draft.",
    "16. Verify no Slack message posts and audit_log.jsonl has draft_read path=company/inbox/000_silent_clinical_trial_protocol.txt, driver=openclaw, memory_searched count: 0, no slack_sent before processed, and processed path=company/inbox/000_silent_clinical_trial_protocol.txt status=skipped_no_relevant_memory.",
    "17. ./bin/imem reset-demo, then uv run python scripts/demo_case.py rfp, then wait for heartbeat to send the RFP Slack message.",
    "18. Record a non-empty .mp4 or .mov backup video under demo_artifacts/ showing OpenClaw, audit tail, inbox file drop, and Slack message.",
    "19. Run uv run python scripts/final_gate.py without skip flags.",
]


def main() -> int:
    print("\n".join(STEPS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
