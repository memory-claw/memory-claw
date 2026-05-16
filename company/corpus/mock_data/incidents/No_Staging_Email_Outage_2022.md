# INCIDENT REPORT
## P1 — Environment Config Change Broke Production Email Delivery

**Author:** Marcus Chen  
**Date:** 2022-09-12  
**Severity:** P1  
**Duration:** 11 hours (overnight — not detected until morning)  
**Root Cause:** SendGrid API key rotated in production without testing in staging first. New key was scoped incorrectly — missing the "Mail Send" permission. All transactional emails silently failed for 11 hours.  
**Outcome:** Welcome emails, password resets, and billing receipts not delivered for 11 hours. 3 churned free trials (no welcome email = assumed broken product). 12 support tickets.  

---

### What Happened

On 2022-09-11 at 21:30 UTC, Marcus rotated the SendGrid API key as part of a routine credential rotation. The new key was generated with a template that omitted the "Mail Send" permission — it had "Template Engine" and "Stats" permissions only.

The key was applied directly to production. There was no staging environment to test it against first.

SendGrid returned 403 errors for all email send attempts. These errors were caught by the application's email service and logged — but the log level was set to `warn`, not `error`, and no alert was configured for email delivery failures.

All transactional emails silently failed between 21:30 UTC and 08:15 UTC the following morning — 11 hours.

Failed emails included:
- 47 welcome emails (new signups)
- 23 password reset requests
- 8 billing receipts

The 47 users who signed up during this window received no welcome email, no onboarding prompts, and could not receive a password reset if they forgot their credentials. 3 of these users, contacted retroactively, stated they assumed the product was broken and did not return.

---

### Why There Was No Staging Environment

At the time, we had no staging environment. Configuration changes were applied directly to production. This was a conscious decision made in 2021 ("we'll add staging when we have more resources") that was never revisited.

---

### People Involved

- **Marcus Chen** — Rotated the credential. Applied directly to production.
- **Priya Patel** — Morning escalation. Notified affected users.
- **Jake Morrison** — Triaged support tickets.

---

### What Changed

1. Staging environment created within 2 weeks of this incident — mirrors production configuration.
2. All config changes tested in staging before production.
3. Email delivery monitoring added — failure rate >2% triggers PagerDuty alert.
4. Log level for email send failures changed from `warn` to `error`.
5. Permission checklist created for SendGrid key generation.

See `Staging_Environment_Policy.md`.

> "We had no staging environment because we kept saying we'd add it when we had more resources. This incident cost us more than building staging would have. We built staging immediately after."  
> — Priya Patel
