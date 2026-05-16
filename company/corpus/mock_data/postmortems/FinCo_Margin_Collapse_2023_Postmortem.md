# PROJECT POSTMORTEM
## FinCo Analytics Platform — Margin Collapse 2023

**Author:** Rachel Moore, Compliance / James Liu, Delivery Lead  
**Date:** 2023-07-14  
**Project:** FinCo Analytics Platform  
**Client:** FinCo Capital Ltd  
**Contract Value (Bid):** £1,100,000  
**Actual Cost to Deliver:** £1,740,000  
**Margin:** -£640,000 (negative)  
**Outcome:** Delivered successfully. Complete commercial failure. Margin collapse.  
**Risk Level:** Critical  
**Department:** Sales / Delivery  

---

### Summary

We won the FinCo Analytics Platform bid and delivered it on time. We also lost £640,000 doing so. The bid was underpriced by 58% of actual delivery cost. The pricing model did not account for: data migration complexity, third-party licensing fees, or the 3x scope expansion that occurred during discovery. No scope change process was in place.

Tom Walker submitted the bid without involving James Liu (Delivery) or Rachel Moore (Compliance) in the cost model.

---

### What Happened

Tom Walker produced a bid price of £1.1M based on a standard day-rate model. The model assumed:

- Clean, structured source data (actual: 14 legacy systems, partial data, inconsistent schemas)
- No third-party licensing beyond standard stack (actual: £180,000 in additional BI tooling required)
- Fixed scope through delivery (actual: scope expanded 3x during discovery phase)
- 4-person team for 9 months (actual: 7-person team for 13 months)

No delivery estimate was provided by James Liu's team. No risk contingency was included. No scope change clause was in the contract.

---

### Timeline

| Date | Event |
|------|-------|
| 2023-01-10 | Tom Walker submits bid. No delivery review. |
| 2023-01-28 | FinCo awards contract. |
| 2023-02-14 | Discovery begins. Scope issues identified immediately. |
| 2023-03-01 | James Liu escalates: "We will lose money on this." |
| 2023-03-04 | No mechanism to change contract price. Delivery continues. |
| 2023-07-01 | Project delivered. |
| 2023-07-14 | Financial review confirms -£640,000 margin. This postmortem. |

---

### Root Cause

Bid submitted without delivery input. No scope change process. No risk contingency. No pricing checklist.

**Person responsible:** Tom Walker (bid owner). Note: Tom followed standard practice at the time — the failure was systemic, not individual.

---

### Mandatory Process Change (Effective Immediately)

James Liu has introduced the **Delivery Pricing Sign-Off** requirement:

No bid over £250,000 may be submitted without:
1. Delivery team complexity estimate (James Liu or senior delivery lead)
2. Third-party licensing cost review
3. 15% risk contingency line item
4. Scope change clause in contract (Rachel Moore to draft standard language)
5. CFO approval on bids over £500,000

---

### Persons Involved

- **Tom Walker** — Sales Director. Submitted bid without delivery input.
- **James Liu** — Delivery Lead. Not consulted. Escalated when underpricing became clear.
- **Rachel Moore** — Compliance. Authored postmortem. Drafting scope change clause.

---

### Financial Impact

- Revenue: £1,100,000
- Cost to deliver: £1,740,000
- Net loss: **-£640,000**
- Equivalent: Company funded the project and paid FinCo £640,000 to take it.

---

### Lessons Learned

> "We won the deal and lost the company money. Winning a contract at the wrong price is worse than losing it."  
> — James Liu

If a bid is being prepared and delivery hasn't reviewed the complexity, that bid is not ready. The FinCo engagement proved that a working delivery does not save a bad price.
