# ENGINEERING POLICY
## Third-Party Dependency Risk Policy

**Author:** Priya Patel, CTO  
**Date:** 2023-11-15  
**Status:** MANDATORY — All new third-party integrations  
**Related Incident:** Mapbox pricing crisis Nov 2023 — $100K annualised margin impact  

---

### Background

In November 2023, our primary mapping vendor raised prices 12x with 30 days notice. We had built our entire mapping layer on a single vendor with no fallback. Every session of the mapping feature would have cost us $0.21 more than we charged for it. We had to do an emergency 6-week migration.

This policy prevents vendor lock-in from becoming a business crisis.

---

### Rules

#### Rule 1 — No Single-Vendor Core Features
Any feature that is customer-facing and used by more than 20% of active users must not depend on a single third-party vendor with no fallback.

"We'll add a fallback later" is not acceptable for core features. Add it before shipping or don't use that vendor.

#### Rule 2 — Cost Ceiling Modelling Before Integration
Before integrating any paid third-party API, Marcus must model:
- Current cost per unit at current usage
- Cost at 10x usage
- Cost at 100x usage
- What happens if the vendor raises prices 5x

If the 5x scenario makes the feature unprofitable, either negotiate a pricing lock, find an alternative, or don't build the feature on that vendor.

#### Rule 3 — Contractual Pricing Lock (Where Possible)
For any vendor where we spend or expect to spend >$500/month, attempt to negotiate:
- Fixed pricing for minimum 12 months
- 90-day notice period for price changes (not 30 days)
- Volume discount commitments

If the vendor won't negotiate, document the risk explicitly and get Priya sign-off.

#### Rule 4 — Abstraction Layer Required
Any third-party API integration for a core feature must sit behind an abstraction layer — a service class or interface that could be pointed at a different vendor without rewriting the calling code.

This doesn't have to be overengineered. It just has to mean "swap vendor = change config, not rewrite."

#### Rule 5 — Annual Vendor Review
Marcus runs an annual review of all active third-party dependencies in Q1. Output: a list of vendors, current monthly cost, pricing lock status, and assessed switching cost.

---

### The Mapbox Lesson

> "We built a load-bearing feature on a vendor's free tier pricing and assumed it would last forever. It lasted 18 months."

If someone says "let's just use [vendor], we can abstract it later" — ask when. If there's no concrete plan, the abstraction never happens. Do it now.
