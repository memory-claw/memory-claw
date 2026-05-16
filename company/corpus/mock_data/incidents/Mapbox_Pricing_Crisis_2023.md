# INCIDENT REPORT
## Vendor Pricing Crisis — Mapbox Price Increase, Unit Economics Broken

**Author:** Marcus Chen, Infrastructure Lead  
**Date:** 2023-11-02  
**Severity:** P1 — Business Critical  
**Outcome:** Core mapping feature costs 12x more to run overnight. Feature margin goes negative.  
**Root Cause:** Entire mapping layer built on single vendor API with no fallback. Vendor raised prices with 30 days notice.  
**Status:** Resolved — migrated to multi-vendor strategy over 6 weeks  

---

### What Happened

On 2023-11-01, Mapbox sent an email announcing a pricing restructure effective 2023-12-01. The new pricing was approximately 12x higher for our usage tier. Our map rendering feature cost $0.04 per user session under the old pricing. Under the new pricing it would cost $0.51 per session.

Our feature was priced at $0.30 per session equivalent in our plan tiers. At the new Mapbox rates, every use of the mapping feature would cost us $0.21 more than we collected for it.

At current usage (approximately 40,000 sessions/month), this represented a monthly loss of **$8,400 per month, or $100,800 annualised**, on a feature that had previously contributed positive margin.

We had 30 days to resolve it.

---

### Why We Were Exposed

When Marcus built the mapping feature in 2022, Mapbox was the obvious choice — great SDK, generous free tier, fast integration. The integration was built assuming Mapbox pricing would remain stable. No fallback vendor was evaluated. No cost ceiling was set. No contractual pricing lock was negotiated.

The entire mapping layer was tightly coupled to Mapbox's SDK — swapping vendors wasn't a configuration change, it required a partial rewrite.

Marcus flagged at the time that building on a single vendor for a core feature was a risk. It was deprioritised in favour of shipping speed.

---

### Timeline

| Date | Event |
|------|-------|
| 2022-04-11 | Mapping feature shipped. Built entirely on Mapbox. |
| 2023-11-01 | Mapbox pricing change email received. 30-day notice. |
| 2023-11-02 | Marcus calculates impact. Escalates to Priya. |
| 2023-11-03 | Emergency vendor evaluation begins. |
| 2023-11-14 | Decision: migrate to MapLibre (open source) + AWS Location as fallback. |
| 2023-12-08 | Migration complete. Zero customer-visible changes. |

---

### Financial Impact

- Monthly cost increase if not mitigated: $8,400
- Annualised: $100,800
- Migration engineering cost (Marcus + Alex, 4 weeks): ~$28,000
- Net saving vs staying on Mapbox: ~$73,000 in year one

---

### People Involved

- **Marcus Chen** — Built original integration. Led migration.
- **Priya Patel** — Escalated to board. Approved emergency migration budget.
- **Jake Morrison** — Deprioritised multi-vendor evaluation in 2022.

---

### What Changes

Priya introduced the Third-Party Dependency Policy. See `Third_Party_Dependency_Policy.md`.

> "We built a load-bearing feature on a vendor's free tier pricing and assumed it would last forever. It lasted 18 months."  
> — Marcus Chen
