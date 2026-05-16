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
    assert "PATH=\\$HOME/.local/bin:\\$PATH" in script
    assert "git fetch origin" in script
    assert "git checkout -B" in script
    assert ".openclaw/workspace" in script
    assert "cp SOUL.md" in script
    assert "cp HEARTBEAT.md" in script
    assert "cp skills/institutional-memory/SKILL.md" in script
    assert "SLACK_BOT_TOKEN" in script
    assert "SLACK_CHANNEL" in script
    assert "cat > .env" in script
    assert "umask 077" in script
    assert "uv sync" in script
    assert "scripts/dgx_check.py --skip-model-smoke --skip-backup-video" in script
    assert "sshpass" not in script
    assert "password" not in script.lower()


def test_no_github_actions_auto_deploy_workflow():
    assert not Path(".github/workflows/deploy-asus.yml").exists()


def test_readme_documents_asus_push_deploy():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "ASUS webhook" in readme
    assert "scripts/deploy_asus.sh" in readme
    assert "ASUS_SSH_KEY" in readme
    assert "ASUS_BRANCH" in readme
    assert "OpenClaw workspace" in readme
    assert "tailscale ping 100.68.221.47" in readme
