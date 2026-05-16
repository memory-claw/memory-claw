---
name: institutional-memory
description: Institutional memory agent tools.
---

# Institutional Memory Tools

Use only these commands from OpenClaw:

```bash
./bin/imem list-new-drafts
./bin/imem read-draft --path <path>
./bin/imem search-memory --query "<query>"
./bin/imem send-slack --message-file .runtime/slack_message.txt
./bin/imem send-slack --message-file .runtime/slack_message.txt --channel <slack_channel_id> --thread-ts <slack_thread_ts>
./bin/imem mark-processed --path <path> --status <status> --reason "<reason>" [--query "<query>"] [--top-score <score>] [--source "<source>"]
```

All commands return JSON. Process one draft per turn. Use the threaded `send-slack` form only when `read-draft` returns both Slack routing fields.
