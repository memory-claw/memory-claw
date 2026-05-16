# memory-claw

Institutional Memory Engine demo for OpenClaw + local Ollama.

Spec: `2026-05-15-institutional-memory-engine.md`.

## Local Mac Status

This Mac has the tool layer implemented and tested. It is not the final live
demo machine. Final readiness still requires ASUS/DGX-only proof:

- `SLACK_BOT_TOKEN` and `SLACK_CHANNEL` in `.env`
- `nemotron-3-super:120b` responding within timeout
- OpenClaw audit events tagged `driver=openclaw`
- non-empty backup video under `demo_artifacts/`

## ASUS Run

After pulling this branch on ASUS:

```bash
uv sync
cp -n .env.example .env
uv run python scripts/live_handoff.py
```

Set real `SLACK_BOT_TOKEN` and `SLACK_CHANNEL` in `.env`, then follow the
printed sequence exactly. It covers model pulls, Slack secrets, OpenClaw setup,
RFP success case, silent case, heartbeat proof, backup video, and final gate.

Final gate:

```bash
uv run python scripts/final_gate.py
```

Do not call the goal complete until that command passes on ASUS.

## Push Deploy

Use SSH key auth over Tailscale. Do not store the ASUS login password in this
repo or in a workflow. Push deploy is defined in
`.github/workflows/deploy-asus.yml`.

GitHub secrets required:

```bash
ASUS_SSH_KEY          # private deploy key that can SSH to asus@100.68.221.47
TS_OAUTH_CLIENT_ID    # Tailscale OAuth client id
TS_OAUTH_SECRET       # Tailscale OAuth secret
```

One-time ASUS SSH key setup from this Mac:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/asus_deploy
ssh-copy-id -i ~/.ssh/asus_deploy.pub asus@100.68.221.47
tailscale ping 100.68.221.47
ASUS_SSH_KEY=~/.ssh/asus_deploy scripts/deploy_asus.sh
```

Each push to `codex/institutional-memory-engine` runs `scripts/deploy_asus.sh`
from GitHub Actions over Tailscale. The script fetches that branch on ASUS and
checks it out over the old `main` checkout. It also updates the OpenClaw
workspace with `SOUL.md`, `HEARTBEAT.md`, and the institutional-memory skill.
Override `ASUS_USER_HOST`, `ASUS_TAILSCALE_IP`, `ASUS_REPO`, `ASUS_BRANCH`,
`ASUS_SSH_KEY`, or `OPENCLAW_WORKSPACE` for manual runs if the ASUS checkout or
OpenClaw workspace differs from `~/memory-claw` and `~/.openclaw/workspace`.

test