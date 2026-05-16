# SECURITY POLICY
## Secrets Management — Mandatory

**Author:** Marcus Chen / Priya Patel  
**Date:** 2023-03-18  
**Status:** MANDATORY — All repositories, all engineers  
**Related Incident:** GitHub credential leak March 2023 — $3,200 net cost, production DB connection string exposed  

---

### The Rule (One Sentence)

Credentials, API keys, passwords, and connection strings never touch version control. Ever. Not even private repos.

---

### What Happened

On 2023-03-17, a .env file with live AWS keys, a Stripe secret, and a production Postgres connection string was pushed to a public GitHub repo. Bots detected it in 47 seconds. $12,400 in crypto mining charges were incurred in 4 minutes. We got lucky: the billing alerts caught it, and the attackers chose mining over data exfiltration.

We cannot rely on luck again.

---

### Mandatory Controls (All Engineers)

#### 1. Pre-commit Hook — git-secrets
`git-secrets` is installed and configured on all repos. It blocks commits containing patterns matching AWS keys, Stripe keys, and generic API key formats.

**Setup (run once per machine):**
```bash
brew install git-secrets        # macOS
git secrets --install           # installs hooks into current repo
git secrets --register-aws      # adds AWS pattern detection
```

If you're onboarding and haven't run this: do it now before writing any code.

#### 2. .gitignore Standards
All repos include a standard `.gitignore` that covers:
```
.env
.env.*
*.env
.env.local
.env.production
*.pem
*.key
credentials.json
```
Do not remove these entries. Do not create exceptions.

#### 3. Local Development Credentials
Developers do not have production credentials locally. Full stop.

- **Local dev:** Use `.env.example` with dummy values. Real credentials in 1Password.
- **Staging:** Use AWS IAM roles with minimal permissions. Credentials injected via CI.
- **Production:** Credentials managed in AWS Secrets Manager. Never in code, never in environment files outside the deployment pipeline.

#### 4. GitHub Advanced Security
Secret scanning is enabled on all repositories. If a secret is detected in a push:
- GitHub blocks the push automatically
- Marcus is notified immediately
- The affected credential must be rotated before the push is retried

Do not disable or bypass secret scanning alerts.

#### 5. Credential Rotation Schedule
- AWS access keys: rotate every 90 days
- Third-party API keys: rotate every 180 days, or immediately on any personnel change
- Database passwords: rotate on any suspected exposure, or every 6 months

---

### If You Think You've Leaked a Credential

**Do not wait. Do not investigate first. Rotate immediately, then investigate.**

1. Message Marcus in Slack right now
2. Rotate the affected credential in the relevant service
3. Check AWS CloudTrail / service logs for unauthorised access
4. Marcus and Priya decide on customer notification

Time is the variable that determines severity. The March 2023 incident was contained in 4 minutes. Anything longer and we'd be notifying customers of a data breach.
