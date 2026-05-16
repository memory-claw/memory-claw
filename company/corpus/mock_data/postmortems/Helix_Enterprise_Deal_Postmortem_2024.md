# POSTMORTEM
## Helix Enterprise Deal — Underscoped, Overdelivered, Still Churned

**Author:** Priya Patel, CTO  
**Date:** 2024-01-08  
**Project:** Helix Capital — Enterprise Onboarding  
**Deal Value:** $220,000 ARR  
**Estimated Delivery:** 6 weeks  
**Actual Delivery:** 7 months  
**Outcome:** Customer churned at renewal. Two engineers burned out. One resigned.  

---

### Summary

Sarah Kim closed a $220,000 ARR enterprise deal with Helix Capital in May 2023. The deal was scoped as "6 weeks of onboarding and custom integrations." Nobody from engineering was involved in scoping. The actual work took 7 months. At peak, Marcus and Alex were spending 60–70% of their time on Helix work while still expected to maintain product velocity. Alex resigned in November 2023, citing burnout. Helix churned in January 2024, citing "ongoing reliability concerns."

We lost the customer, lost an engineer, and delivered 7 months of work that generated $220,000 — a cost far exceeding revenue when engineering time is valued accurately.

---

### How the Deal Was Scoped

Sarah Kim closed the deal based on:
- A 30-minute demo call
- A requirements doc written by the Helix product team (not engineering)
- Sarah's estimate of "6 weeks" based on previous smaller deals

Engineering was not consulted before the deal closed. The contract was signed before Marcus or Alex had seen the technical requirements.

When Marcus reviewed the requirements doc post-signing, he flagged that the custom SSO integration, data pipeline, and white-labelling requirements were a minimum 5-month project, not 6 weeks. At that point the contract was already signed.

---

### Timeline

| Date | Event |
|------|-------|
| 2023-05-03 | Sarah closes Helix deal. $220K ARR. "6-week onboarding." |
| 2023-05-08 | Marcus reviews requirements. Flags 5-month minimum estimate. |
| 2023-05-09 | Priya: "We're committed. We'll have to make it work." |
| 2023-07-01 | Marcus and Alex at 70% Helix time. Product velocity stalls. |
| 2023-09-01 | Helix scope expands again. No change order process. |
| 2023-11-15 | Alex resigns. Burnout cited. |
| 2023-12-01 | Helix integration finally complete. 7 months in. |
| 2024-01-08 | Helix churns at renewal. "Reliability concerns." |

---

### Root Cause

Engineering was excluded from pre-sales scoping. A 30-minute demo and a customer-written requirements doc is not a technical scope. "6 weeks" was a sales estimate, not an engineering estimate.

Once the contract was signed, there was no change order process — scope expanded three times with no commercial adjustment.

---

### What Changes Now

**Jake Morrison is introducing a mandatory pre-close technical review for any enterprise deal over $50K:**

1. Engineering lead (Marcus or Priya) must review requirements before contract is signed
2. Written engineering estimate required — not a sales estimate
3. Any deal including custom integrations, data pipelines, SSO, or white-labelling is automatically flagged for technical review
4. Scope change clause required in all enterprise contracts: changes require a signed change order before work begins

See `Enterprise_Deal_Process.md`.

---

### The Real Cost of Helix

Revenue: $220,000  
Engineering time (Marcus + Alex, 7 months, 65% allocation): ~$310,000 in fully-loaded cost  
Alex's replacement hiring: ~$40,000  
Net: **-$130,000**

We lost money on a $220,000 deal.

---

### Lesson

> "Sales closes the deal. Engineering pays for it. If engineering hasn't scoped it, the number on the contract is fiction."  
> — Priya Patel

If a deal is about to close and engineering hasn't seen the technical requirements — stop. That is the Helix conversation.
