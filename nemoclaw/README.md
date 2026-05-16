# NemoClaw Bonus Scaffold

NemoClaw bonus proof is optional and should only be attempted after the core OpenClaw demo passes twice.

Probe commands:

```bash
./bin/imem nemoclaw-probe denied-read
./bin/imem nemoclaw-probe denied-network
```

Inside the sandbox, both should return JSON with `{"status":"denied"}`. On an unsandboxed Mac they may return `unsafe_access_succeeded`; that is expected and does not satisfy the bonus proof.
