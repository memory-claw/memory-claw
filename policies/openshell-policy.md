# OpenShell Policy Scaffold

Final OpenClaw demo posture should allow only the repository wrapper command:

```text
/Users/ashwinmurthy/memory-claw/bin/imem
```

Do not allowlist `python3`, `uv`, `bash`, or arbitrary shell commands. The wrapper changes to the repository root and calls the packaged `imem` console command.

Optional NemoClaw proof must run in the real sandbox on the ASUS/DGX. Local unsandboxed probes that return `unsafe_access_succeeded` do not prove the bonus track.
