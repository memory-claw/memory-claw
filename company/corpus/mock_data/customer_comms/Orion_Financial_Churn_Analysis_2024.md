# CUSTOMER CHURN ANALYSIS
## Orion Financial — $96,000 ARR Lost, Support Response Time Root Cause

**Author:** Sarah Kim, Growth  
**Date:** 2024-07-15  
**Customer:** Orion Financial  
**ARR Lost:** $96,000  
**Tenure:** 14 months  
**Stated Churn Reason:** "Support response times are not acceptable for a financial services environment."  
**Actual Root Cause:** Three critical support tickets went 72+ hours without a substantive response. No enterprise SLA existed.  

---

### What Happened

Orion Financial renewed their contract in May 2023 at $96,000 ARR. They were our second-largest customer.

Between February and June 2024, Orion opened six support tickets. Three of them — all marked "High" priority by Orion — received first substantive responses after 72 hours or more.

| Ticket | Priority | Time to first response | Time to resolution |
|--------|----------|----------------------|-------------------|
| ORN-041 | High | 18 hours | 4 days |
| ORN-052 | High | 76 hours | 6 days |
| ORN-067 | Normal | 6 hours | 1 day |
| ORN-071 | High | 84 hours | 8 days |
| ORN-088 | Normal | 4 hours | 2 days |
| ORN-094 | Normal | 8 hours | 3 days |

ORN-052 and ORN-071 both related to data export failures affecting Orion's compliance reporting. Both went more than 3 days before substantive engineering input. In a financial services context, compliance reporting failures have regulatory implications for the customer.

Sarah received no signal during this period that Orion was unhappy. The account had no assigned owner who was monitoring ticket SLAs. The CSM function (Sarah) and engineering (Marcus) operated in separate systems with no handoff for high-severity customer tickets.

In June 2024, Orion's Head of Operations emailed Priya directly, expressing frustration. Priya escalated internally. By that point, Orion had already begun evaluating alternatives. They declined to renew in July 2024.

---

### Why Support Was Slow

There were no SLAs. No defined response time targets. Marcus and Alex handled support tickets when they had capacity — between feature work, on-call incidents, and meetings. High-priority tickets from enterprise customers were not differentiated from general support.

There was also no alert or escalation path. A ticket could sit for days with no response and nobody would notice.

---

### What It Cost

$96,000 ARR.

Replacement sales cycle cost (to replace with equivalent ARR): approximately $40,000 in sales and marketing effort. Net impact: $136,000.

---

### What Changed

Sarah introduced a tiered support SLA framework and enterprise customer health monitoring. See `Enterprise_Support_SLA_Policy.md`.

> "Orion sent us 6 tickets and we never noticed that 3 of them went silent for 72+ hours. We didn't have the systems to notice. By the time Priya got the email, they were already gone."  
> — Sarah Kim
