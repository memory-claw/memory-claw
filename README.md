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
uv run python scripts/live_handoff.py
```

Follow that printed sequence exactly. It covers model pulls, Slack secrets,
OpenClaw setup, RFP success case, silent case, heartbeat proof, backup video,
and final gate.

Final gate:

```bash
uv run python scripts/final_gate.py
```

Do not call the goal complete until that command passes on ASUS.
