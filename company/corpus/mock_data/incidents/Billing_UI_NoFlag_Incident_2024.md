# INCIDENT REPORT
## P1 — New Billing UI Shipped to 100% of Users, 34% Error Rate

**Author:** Jake Morrison, Product  
**Date:** 2024-03-04  
**Severity:** P1  
**Duration:** 2 hours 12 minutes before rollback completed  
**Affected:** 34% of users encountered billing errors during window  
**Root Cause:** New billing UI shipped directly to 100% of users with no feature flag. Edge case in proration calculation broke for annual plan users.  
**Outcome:** 34% billing error rate for 2h12m. 8 customers contacted support. 2 requested refunds. No churns.  

---

### What Happened

On 2024-03-04, Alex Rivera shipped a redesigned billing management UI. The new UI included a rewritten proration calculation for plan upgrades and downgrades.

The new calculation worked correctly for monthly plan users. It contained a bug for annual plan users who upgraded mid-cycle — it calculated the prorated credit based on calendar days remaining rather than billing-period days remaining, producing incorrect (higher) charges.

Annual plan users represent 34% of the user base.

The feature shipped directly to all users with no feature flag. There was no gradual rollout. There was no canary group.

Support tickets began appearing within 11 minutes of deploy. The error was identified at 37 minutes. Rolling back required a full revert deploy, which took 2 hours 12 minutes because the billing UI changes were bundled with unrelated frontend changes in the same deployment.

---

### Why No Feature Flag

Alex was not aware that feature flags were expected for billing-related changes. The team had discussed using feature flags in a planning meeting but no formal policy existed at the time.

Jake had approved the PR and the deployment plan. Neither Jake nor Alex considered the rollout risk for a billing change.

---

### Timeline

| Time | Event |
|------|-------|
| 14:00 | Alex deploys new billing UI to 100% of users |
| 14:11 | First support ticket: "I was charged the wrong amount" |
| 14:37 | Bug identified — annual plan proration calculation |
| 14:45 | Decision to rollback |
| 14:50 | Revert begins — complicated by bundled deployment |
| 16:12 | Rollback complete. Original billing UI restored. |
| 16:15 | Affected users identified and emailed |

---

### People Involved

- **Alex Rivera** — Shipped the billing UI. No feature flag.
- **Jake Morrison** — Approved PR and deploy. Did not flag rollout risk.
- **Priya Patel** — Incident lead. Customer comms.
- **Sarah Kim** — Handled the 2 refund requests.

---

### What Changes

Jake introduced a mandatory feature flag policy for any user-facing change. See `Feature_Flag_Policy.md`.

> "We shipped a billing change to 100% of users because we didn't have a policy saying we shouldn't. Now we do."  
> — Jake Morrison
