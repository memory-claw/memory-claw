# POSTMORTEM
## /export Endpoint Outage — August 2023

**Author:** Priya Patel, CTO  
**Date:** 2023-08-18  
**Incident:** P0 API Outage, 2023-08-14  
**ARR Lost:** $94,000  
**Root Cause:** New endpoint shipped to production with no rate limiting, no load testing, no infrastructure review  

---

### Summary

We shipped a feature, it took down our entire API for 6 hours, and we lost three enterprise customers. The feature itself worked fine. The problem was we had no gate preventing a data-heavy endpoint from going to production without an infrastructure review.

This was not Alex's fault. Alex built what was specced. Nobody told Alex that endpoints doing full table scans need rate limiting. The failure was a process failure, not a people failure.

---

### Why It Really Happened

We had a fast-shipping culture with no infrastructure review step. PRs got reviewed for code correctness, not for production safety. The question "what happens if someone hammers this endpoint?" was never asked.

We also had no bulkhead isolation — one endpoint's database load could exhaust the connection pool for all endpoints. This is a systemic architecture issue separate from the rate limiting gap.

---

### What Changes Immediately

**Marcus Chen is introducing a mandatory pre-ship checklist for any new API endpoint:**

1. Does this endpoint hit the database? → Rate limiting required.
2. Does it return potentially large datasets? → Pagination required, max page size enforced.
3. Has it been load tested? → Minimum: k6 test at 10x expected peak load.
4. Infrastructure review required for any endpoint that: performs aggregations, exports data, triggers background jobs, or interacts with third-party APIs.

This checklist lives in `Endpoint_PreShip_Checklist.md`. It is a required step before any endpoint PR is merged, starting immediately.

**Marcus is also building a reusable `@rateLimit` middleware** so rate limiting takes 2 lines of code, not a reason to skip it.

---

### The Bigger Lesson

> "We lost $94K because adding rate limiting felt like extra work. The middleware Marcus built takes 2 lines. We will never ship an endpoint without it again."  
> — Priya Patel, CTO

Every time someone says "we can add rate limiting after launch" — this is the outcome. It will not be a quick fix after launch. It will be a 6-hour outage and three churned enterprise customers.

---

### Follow-Up Owners

- Marcus Chen → `@rateLimit` middleware + load testing docs. Complete by 2023-09-01. ✅
- Priya Patel → Architecture review: connection pool isolation. Q4 2023.
- Jake Morrison → Update PR template to include infrastructure checklist link.
