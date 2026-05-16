from pathlib import Path


def test_deploy_script_uses_tailscale_and_ssh_key_without_password():
    script = Path("scripts/deploy_asus.sh").read_text(encoding="utf-8")

    assert "100.68.221.47" in script
    assert "tailscale ping" in script
    assert "tailscale status" in script
    assert "tailscale netcheck" in script
    assert "ssh -i" in script
    assert "BatchMode=yes" in script
    assert "StrictHostKeyChecking=accept-new" in script
    assert "ASUS_BRANCH" in script
    assert "git fetch origin" in script
    assert "git checkout -B" in script
    assert ".openclaw/workspace" in script
    assert "cp SOUL.md" in script
    assert "cp HEARTBEAT.md" in script
    assert "cp skills/institutional-memory/SKILL.md" in script
    assert "uv sync" in script
    assert "scripts/dgx_check.py --skip-model-smoke --skip-backup-video" in script
    assert "sshpass" not in script
    assert "password" not in script.lower()


def test_github_action_deploys_over_tailscale_without_password():
    workflow = Path(".github/workflows/deploy-asus.yml").read_text(encoding="utf-8")

    assert "tailscale/github-action@v4" in workflow
    assert "main" in workflow
    assert "codex/institutional-memory-engine" in workflow
    assert "100.68.221.47" in workflow
    assert "ASUS_SSH_KEY" in workflow
    assert "scripts/deploy_asus.sh" in workflow
    assert "sshpass" not in workflow
    assert "password" not in workflow.lower()


def test_readme_documents_asus_push_deploy():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert ".github/workflows/deploy-asus.yml" in readme
    assert "scripts/deploy_asus.sh" in readme
    assert "ASUS_SSH_KEY" in readme
    assert "ASUS_BRANCH" in readme
    assert "OpenClaw workspace" in readme
    assert "TS_OAUTH_CLIENT_ID" in readme
    assert "tailscale ping 100.68.221.47" in readme
