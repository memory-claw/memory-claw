# ENGINEERING POLICY
## Cloud Cost Controls — Mandatory

**Author:** Priya Patel, CTO  
**Date:** 2022-11-10  
**Version:** 1.2 (updated 2024-01-15)  
**Status:** MANDATORY — All AWS / GCP / Azure spend  
**Outcome:** Zero surprise bills since adoption. Monthly spend predictable within 8%.  
**Related Incident:** AWS GPU Bill 2022 — $31,200 unplanned spend  

---

### Background

In October 2022, Jake Morrison spun up GPU instances for an ML experiment. The instances ran for 18 days unmonitored. The AWS bill was $31,200 above forecast. At the time we had 4.5 months of runway. We cannot repeat this.

---

### Rules (All Mandatory)

#### Rule 1 — Billing Alerts (Already Set — Do Not Remove)
AWS billing alerts are configured at: $500 / $2,000 / $5,000 / $10,000 monthly thresholds.
- Any alert above $2,000 pages Marcus Chen and Priya Patel immediately.
- Do not modify or disable these alerts. Ever.

#### Rule 2 — Resource Tagging
Every AWS resource must be tagged at creation:
```
team:        engineering | product | data
purpose:     production | experiment | dev
owner:       <your slack handle>
auto-delete: true | false
```
Untagged resources are automatically flagged by our cost anomaly detector weekly.

#### Rule 3 — GPU / Compute-Intensive Instances
Any instance type larger than `t3.large` requires:
- Slack message in `#infra` before spinning up: what it's for, expected duration, who's responsible for teardown
- Auto-shutdown configured (maximum 72 hours unless explicitly extended)
- Marcus Chen pinged for instances expected to run > 48 hours

#### Rule 4 — Experiment Instances
If you spin up infrastructure for an experiment:
- It is **your responsibility** to terminate it when done
- Post in `#infra` when terminated: "spun down [resource] [date]"
- If deprioritised without termination, that is a production incident

#### Rule 5 — Monthly Cost Review
Marcus Chen runs a monthly cost review in the first week of each month. All engineers are expected to know their team's approximate monthly AWS spend.

---

### Why This Exists

> "Jake thought Marcus terminated the instances. Marcus thought Jake did. $31,200 later, we wrote a policy."

If you're about to spin up a large instance and you're thinking "I'll sort the teardown later" — that is the 2022 conversation. Post in #infra first.
