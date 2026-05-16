# CUSTOMER POLICY
## Enterprise Support SLA — Response Time Requirements

**Author:** Sarah Kim / Priya Patel  
**Date:** 2024-07-20  
**Status:** MANDATORY — All enterprise customers (>$30K ARR)  
**Related Incident:** Orion Financial churn July 2024 — $96,000 ARR lost due to 72+ hour support response times  

---

### Background

Orion Financial ($96,000 ARR) churned in July 2024. Three of their high-priority support tickets received first responses after 72+ hours. Two of those tickets related to compliance reporting failures in a financial services context. We had no SLAs and no alert system to notice tickets going stale.

This policy defines response time requirements and ensures they are met.

---

### SLA Tiers

#### Enterprise (>$30K ARR)

| Priority | First Response | Substantive Update | Resolution Target |
|----------|---------------|-------------------|-------------------|
| Critical (P1) | 2 hours | 4 hours | 24 hours |
| High (P2) | 8 hours | 24 hours | 72 hours |
| Normal (P3) | 24 hours | 72 hours | 7 days |

**Critical (P1):** Product completely unusable, data loss, security incident, compliance-blocking issue.  
**High (P2):** Major feature broken, significant workflow impact, billing/payment issue.  
**Normal (P3):** Minor bugs, feature requests, how-to questions.

#### Standard (<$30K ARR)

| Priority | First Response | Resolution Target |
|----------|---------------|-------------------|
| High | 24 hours | 5 days |
| Normal | 48 hours | 10 days |

---

### Escalation Process

**P1 tickets from enterprise customers:** Page Marcus Chen immediately via PagerDuty. Sarah Kim notified. Priya Patel notified if not resolved within 4 hours.

**P2 tickets approaching SLA breach (>6 hours without response):** Automated Slack alert to #support-escalations. Sarah Kim responsible for ensuring response.

**Any enterprise ticket without activity for 48 hours:** Automated alert to Sarah Kim and Priya Patel.

---

### Enterprise Account Health

Sarah Kim reviews the top 10 accounts by ARR monthly:
- Open ticket count and age
- Time since last meaningful interaction
- Product usage trend (up/down)
- Any recent support escalations

An account going quiet is often a churn signal, not a health signal. Orion had no support tickets for 6 weeks before the churn conversation — they had stopped expecting help.

---

### The Orion Lesson

> "Orion sent us 6 tickets and we never noticed that 3 of them went silent for 72+ hours. We didn't have the systems to notice."

$96,000 ARR. 14 months of tenure. Lost to slow support response times that we didn't know were happening.

The systems now exist to notice. Use them.
