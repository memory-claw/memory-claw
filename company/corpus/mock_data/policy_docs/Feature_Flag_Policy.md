# PRODUCT POLICY
## Feature Flag — Mandatory Rollout Policy

**Author:** Jake Morrison, Product  
**Date:** 2024-03-06  
**Status:** MANDATORY — All user-facing feature releases  
**Related Incident:** Billing UI incident March 2024 — 34% error rate, 2h12m to rollback  

---

### Background

On 2024-03-04, a billing UI change shipped to 100% of users with no feature flag. It contained a bug affecting annual plan users (34% of base). The error rate hit 34% within minutes. Rollback took 2h12m because billing changes were bundled with unrelated code.

Feature flags would have: caught the bug in a 5% canary, limited blast radius, allowed instant kill-switch rollback in seconds instead of hours.

---

### Rules

#### Rule 1 — Feature Flags Are Default

All new user-facing features ship behind a feature flag. "This is a small change" is not an exception. The billing UI change was considered small.

We use LaunchDarkly. If you don't have access, ask Jake.

#### Rule 2 — Mandatory Flag Categories

The following change types **always** require a feature flag, no exceptions:

- Any change to billing, payments, or subscription logic
- Any change to authentication or login flows  
- Any change to data export or deletion
- New features that change existing user workflows
- Any change touching > 20% of the UI surface area

#### Rule 3 — Rollout Stages

Default rollout stages for any flagged feature:

```
Stage 1: Internal team only (5 users) — 48 hours minimum
Stage 2: 5% of users — 24 hours, monitor error rates
Stage 3: 25% of users — 24 hours, monitor
Stage 4: 100% of users
```

For billing or auth changes: stages 1 and 2 are mandatory minimum before any wider rollout.

#### Rule 4 — Separate Deployments

Billing, auth, and payment changes must be deployed separately from unrelated frontend changes. Do not bundle them.

The March 2024 rollback took 2h12m because billing changes were tangled with unrelated CSS and component updates. A clean, isolated deployment means rollback is a flag toggle — seconds, not hours.

#### Rule 5 — Kill Switch Always Ready

Before any feature exits the flag, confirm the kill switch works — setting the flag to 0% must immediately revert the behaviour for all users without a deploy.

Test this on staging before production rollout begins.

---

### What a Flag Buys You

The March 2024 incident: 34% error rate, 2h12m to resolve, 8 support tickets, 2 refunds.

With a feature flag at 5% canary: error affects 1.7% of users. Detected within minutes. Flag turned off in 10 seconds. 0 support tickets.

The flag takes 20 minutes to set up. It saves hours of incident response and customer trust.
