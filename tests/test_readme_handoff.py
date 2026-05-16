from pathlib import Path


def test_readme_points_asus_operator_to_live_gate():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "ASUS" in readme
    assert "uv run python scripts/live_handoff.py" in readme
    assert "uv run python scripts/final_gate.py" in readme
    assert "SLACK_BOT_TOKEN" in readme
    assert "nemotron-3-super:120b" in readme
    assert "2026-05-15-institutional-memory-engine.md" in readme


def test_plan_names_current_repo_path():
    plan = Path("2026-05-15-institutional-memory-engine.md").read_text(encoding="utf-8")

    assert "/Users/ashwinmurthy/memory-claw" in plan
    assert "/Users/ashwinmurthy/larp-idea" not in plan
