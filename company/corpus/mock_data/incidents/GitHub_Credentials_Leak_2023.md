# INCIDENT REPORT
## P0 Security — AWS Credentials Leaked to Public GitHub Repository

**Author:** Marcus Chen, Infrastructure Lead  
**Date:** 2023-03-17  
**Severity:** P0 — Security  
**Duration:** 4 minutes 11 seconds between push and credential rotation  
**Outcome:** $12,400 in unauthorised AWS charges (crypto mining). All credentials rotated. No customer data accessed.  
**Root Cause:** .env file committed and pushed to public repository  

---

### What Happened

At 14:32 UTC on 2023-03-17, Jake Morrison pushed a commit to the public `analytics-dashboard` repository. The commit included a `.env` file containing live AWS access keys, a Stripe secret key, and the production Postgres connection string.

Automated bots that continuously scan GitHub for exposed credentials detected the push within 47 seconds. By 14:36, four EC2 instances had been spun up in regions we do not operate in (ap-southeast-1, sa-east-1). The instances were running a cryptocurrency mining workload.

Marcus received a billing alert at 14:36 (threshold: $500 above baseline). He identified the cause, revoked all credentials, and terminated the instances. Total window: 4 minutes 11 seconds.

Despite the speed of response, $12,400 in EC2 charges were incurred before the instances were terminated. AWS credited $9,200 as a goodwill gesture. Net cost: $3,200.

The Stripe key was also rotated immediately. No unauthorised Stripe transactions were detected. The Postgres connection string was for the production database. There is no evidence of access, but this cannot be ruled out with certainty for the 4-minute window.

---

### Timeline

| Time (UTC) | Event |
|------------|-------|
| 14:32:07 | Jake pushes commit containing .env file to public repo |
| 14:32:54 | Automated credential scanner detects exposed keys (47 seconds) |
| 14:33:41 | First unauthorised EC2 instances launched (ap-southeast-1) |
| 14:36:18 | Marcus billing alert fires |
| 14:36:29 | Marcus identifies cause |
| 14:36:41 | AWS credentials revoked |
| 14:36:52 | Unauthorised instances begin terminating |
| 14:36:58 | Postgres password rotated |
| 14:37:01 | Stripe key rotated |
| 14:37:19 | All credentials confirmed rotated — incident contained |

---

### Root Cause

`.env` was not in `.gitignore` for the `analytics-dashboard` repo. Jake was working on a local setup and committed the file without noticing it contained live production credentials.

No pre-commit hooks were in place to detect secrets before push. No repository scanning was active.

---

### How It Could Have Been Much Worse

- The 4-minute window included a live Postgres connection string. If the attacker had prioritised data exfiltration over crypto mining, customer data could have been exposed.
- The billing alert that caught this was set up after the GPU bill incident in November 2022. If that policy hadn't been in place, this could have run for hours.

---

### People Involved

- **Jake Morrison** — Pushed the .env file. Not malicious — standard developer error.
- **Marcus Chen** — Detected and contained the incident.
- **Priya Patel** — Customer comms lead. Decided no customer notification required (no evidence of data access in the window, legal reviewed).

---

### Immediate Actions

1. All credentials rotated (complete, 14:37 UTC same day)
2. `.env` added to `.gitignore` across all repositories
3. `git-secrets` pre-commit hook installed across all repos
4. GitHub Advanced Security secret scanning enabled (was available, not activated)
5. AWS credential policy scoped down — developers no longer have production credentials locally

See `Secrets_Management_Policy.md`.
