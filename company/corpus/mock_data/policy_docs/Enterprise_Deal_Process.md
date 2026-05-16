# PROCESS POLICY
## Enterprise Deal — Pre-Close Technical Review

**Author:** Jake Morrison, Product / Priya Patel, CTO  
**Date:** 2024-01-15  
**Status:** MANDATORY — All enterprise deals over $50,000 ARR  
**Outcome:** 3 enterprise deals closed correctly since adoption, all delivered on time  
**Related Incident:** Helix Capital — 7-month overrun, $130K net loss, 1 engineer resigned  

---

### Why This Exists

In May 2023, Sarah Kim closed a $220K enterprise deal based on a "6-week" estimate she made without consulting engineering. The deal took 7 months. One engineer burned out and resigned. The customer churned anyway.

This policy ensures engineering is part of the deal before it closes, not after.

---

### The Rules

#### Rule 1 — Technical Review Gate (Deals > $50K)
No enterprise deal above $50,000 ARR may be signed without a written engineering estimate from Marcus Chen or Priya Patel.

The estimate must cover:
- Realistic delivery timeline (not a sales estimate)
- Engineering resources required (who, how much of their time)
- Custom work scope: SSO, integrations, data pipelines, white-labelling, API work
- Risk flags: anything that extends the timeline if requirements change

#### Rule 2 — Requirements Review
Engineering must see the actual technical requirements before the estimate, not after the contract.

A customer-written requirements doc is a starting point, not a scope. Engineering reads it and produces their own estimate.

#### Rule 3 — Scope Change Clause
All enterprise contracts must include a scope change clause:

> "Any modification to the agreed scope of work requires a signed Change Order before work commences. Change Orders will be priced at [standard rate] and timelines adjusted accordingly."

Sarah Kim has a standard clause template. Use it.

#### Rule 4 — Red Flag Triggers (Automatic Technical Review)
Any deal including the following is automatically flagged for engineering review regardless of deal size:
- Custom SSO / identity provider integration
- Data pipeline or ETL work
- White-labelling or custom UI
- Third-party API integrations
- Custom reporting or analytics
- On-premise or VPC deployment

#### Rule 5 — Post-Signature Kickoff
Within 5 days of signing, a kickoff meeting with Sales + Engineering must occur. Engineering confirms scope, sets internal milestones, and flags any gaps between the contract and technical reality before work begins.

---

### The Helix Lesson

> "Engineering was excluded from pre-sales scoping. A 30-minute demo and a customer-written requirements doc is not a technical scope."  
> — Priya Patel, January 2024

If someone says "we can loop in engineering after we close" — that is the Helix conversation. Do not proceed without the technical review.
