# INCIDENT REPORT
## Cloud Cost Incident — Unmonitored GPU Instances, $31,200 AWS Bill

**Author:** Marcus Chen, Infrastructure Lead  
**Date:** 2022-11-07  
**Severity:** P1 — Financial  
**Outcome:** Unplanned $31,200 AWS spend in 18 days. 2 months runway impacted.  
**Root Cause:** GPU instances spun up for ML experiment, never torn down, no billing alerts configured  
**Status:** Resolved — instances terminated, billing alerts now mandatory  

---

### What Happened

On 2022-10-19, Jake Morrison spun up 3x `p3.8xlarge` GPU instances on AWS to prototype an ML-based search ranking feature. The experiment ran over a weekend, produced inconclusive results, and was deprioritised. The instances were not terminated.

The instances ran for 18 days at a combined cost of $57.60/hour.

On 2022-11-07, the AWS bill arrived. The previous month's bill was $3,200. This month's bill was $34,400. The delta was $31,200.

At the time, the company had 4.5 months of runway. This incident consumed approximately 2 weeks of runway in 18 days.

---

### Why Nobody Noticed

- No AWS billing alerts were configured at any threshold
- No tagging policy meant the GPU spend was not obviously attributable to the experiment
- Jake assumed the instances had been terminated. Marcus assumed Jake had terminated them. Nobody checked.
- The AWS console was checked infrequently — no cost dashboard in the team's daily tooling

---

### Timeline

| Date | Event |
|------|-------|
| 2022-10-19 | Jake spins up 3x p3.8xlarge for ML experiment |
| 2022-10-21 | Experiment deprioritised. Instances not terminated. |
| 2022-11-07 | AWS invoice arrives. $34,400. Marcus escalates immediately. |
| 2022-11-07 | Instances terminated (18 days late) |
| 2022-11-08 | Priya informs board of unplanned spend |
| 2022-11-10 | AWS billing alerts configured. Cost policy written. |

---

### People Involved

- **Jake Morrison** — Spun up instances. Did not terminate. Did not inform Marcus.
- **Marcus Chen** — Infrastructure lead. No billing alerts configured. Did not follow up on instance status.
- **Priya Patel** — CTO. Escalated to board. Owns cost policy going forward.

---

### Financial Impact

- Unexpected AWS spend: $31,200
- Runway consumed: ~2 weeks
- AWS credits requested: $8,000 approved (one-time goodwill)
- Net cost: $23,200

---

### Immediate Changes

Priya Patel introduced mandatory cloud cost controls. See `Cloud_Cost_Policy.md`.

> "We were 4.5 months from zero. We burned 2 weeks of runway on an experiment nobody remembered was running. No alert fired because we never set one."  
> — Priya Patel
