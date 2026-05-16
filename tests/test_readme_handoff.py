from pathlib import Path


def test_readme_points_asus_operator_to_live_gate():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "ASUS" in readme
    assert "uv run python scripts/live_handoff.py" in readme
    assert "uv run python scripts/final_gate.py" in readme
    assert "SLACK_BOT_TOKEN" in readme
    assert "nemotron-3-super:120b" in readme
    assert "2026-05-15-institutional-memory-engine.md" in readme


def test_readme_documents_asus_setup_and_rerun_flow():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "PATH=$HOME/.local/bin:$PATH" in readme
    assert "~/run_openclaw.sh" in readme
    assert "~/memory-claw/inbox/" in readme
    assert "corpus/mock_data/" in readme
    assert "inbox/000_nhs_northeast_liability_demo.md" in readme
    assert "./bin/imem reset-demo --clear-audit --clear-chroma" in readme
    assert "uv run python scripts/ingest_corpus.py --force" in readme
    assert "uv run python scripts/dgx_check.py --skip-backup-video" in readme
    assert "demo_artifacts/" in readme


def test_plan_names_current_repo_path():
    plan = Path("2026-05-15-institutional-memory-engine.md").read_text(encoding="utf-8")

    assert "/Users/ashwinmurthy/memory-claw" in plan
    assert "/Users/ashwinmurthy/larp-idea" not in plan
