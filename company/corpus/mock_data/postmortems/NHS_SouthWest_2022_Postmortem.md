# PROJECT POSTMORTEM
## NHS SouthWest Tender 2022 — Failure Analysis

**Author:** Rachel Moore, Compliance  
**Date:** 2022-10-18  
**Project:** NHS-SW-2022-DIG-047  
**Outcome:** Lost — Procurement Rejection  
**Financial Impact:** £4.2M contract lost. Estimated re-bid cost: £35,000.  
**Risk Level:** Critical  
**Department:** Legal / Sales / Compliance  

---

### Summary

We lost the NHS SouthWest Digital Infrastructure tender at procurement stage. The rejection was entirely avoidable. The root cause was a liability cap (Clause 7.3) set at 10% of annual contract value — £140,000 against a £4.2M contract. NHS England procurement standards (PPN 06/21) require full contract value indemnity for patient data suppliers. We were 9x below the threshold.

This was flagged internally by Sarah Chen (Legal) on 2022-09-08 — six days before submission — but was not actioned by the sales team.

---

### Timeline of Failure

| Date | Event |
|------|-------|
| 2022-08-22 | Bid team assembled. Tom Walker leads. Standard commercial template used. |
| 2022-09-08 | Sarah Chen raises liability cap concern in email. Not escalated. |
| 2022-09-14 | Tender submitted with 10% liability cap (Clause 7.3). |
| 2022-10-03 | NHS SW procurement panel rejects at Stage 2. Liability cited as sole reason. |
| 2022-10-05 | James Liu notifies leadership. |
| 2022-10-18 | This postmortem completed. |

---

### Root Cause Analysis

**Primary Cause:** Incorrect liability cap applied.  
10% annual cap used (standard commercial template).  
NHS PPN 06/21 requires 100% contract value minimum for data-handling suppliers.

**Secondary Cause:** Legal review findings were not treated as blockers.  
Sarah Chen's concern was logged in email but not escalated to a formal hold.

**Contributing Factor:** No NHS-specific bid checklist existed at time of submission.

---

### What We Got Wrong

1. Used a generic commercial liability template for a regulated NHS procurement.
2. Ignored a legal flag six days before submission.
3. No mandatory sign-off from Legal before submission of NHS bids.
4. Sales team was unaware that NHS Digital supplier standards differ significantly from standard commercial contracts.

---

### Recommendations

1. **Immediately:** Sarah Chen (Legal) to draft revised liability clause suitable for NHS procurement. Target: Q1 2023.
2. **Process:** No NHS bid to be submitted without explicit Legal sign-off on liability section.
3. **Template:** Create NHS-specific contract template with correct indemnity language baked in.
4. **Training:** Sales team to receive NHS procurement standards briefing before Q2 2023.
5. **Checklist:** Mandatory NHS bid compliance checklist to be created. Owner: Rachel Moore.

---

### Persons Involved

- **Tom Walker** — Sales Director. Led bid. Used standard template. Did not escalate Legal flag.  
- **Sarah Chen** — Legal Counsel. Flagged liability issue on 2022-09-08. Flag not actioned.  
- **Emma Patel** — Procurement (NHS side). Issued rejection notice.  
- **James Liu** — Delivery Lead. Raised postmortem request.  
- **Rachel Moore** — Compliance. Authored this document.

---

### Follow-Up Owner

Sarah Chen to present revised liability clause to leadership by **2023-02-01**.  
Rachel Moore to circulate NHS bid checklist by **2023-01-15**.

---

### Lessons Learned

> "A £4.2M loss caused by a single clause set 9x below minimum. This was not a pricing problem. It was not a technical problem. It was a template problem. We submitted the wrong document."  
> — Rachel Moore, Compliance

If we see a liability cap discussion on any NHS bid, we must check Clause 7.3 against PPN 06/21 before that conversation ends.
