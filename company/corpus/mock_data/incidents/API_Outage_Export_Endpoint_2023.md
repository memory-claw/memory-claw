# INCIDENT REPORT
## P0 — API Outage: /export Endpoint, 6-Hour Downtime

**Author:** Marcus Chen, Infrastructure Lead  
**Date:** 2023-08-14  
**Severity:** P0 — Full API outage  
**Duration:** 6 hours 12 minutes  
**Affected:** All API customers  
**Root Cause:** Unthrottled /export endpoint overwhelmed database connection pool  
**Outcome:** 3 enterprise customers churned. $94,000 ARR lost.  
**Status:** Resolved — rate limiting retroactively applied  

---

### What Happened

At 02:14 UTC on 2023-08-14, a customer's automated script began hitting the `/export` endpoint in a tight loop — approximately 340 requests per minute sustained over 40 minutes. The endpoint performed a full table scan on each request. Within 22 minutes the Postgres connection pool was exhausted. The entire API went down. All customers were affected, not just the one running the script.

The `/export` endpoint had shipped 11 days earlier. It had no rate limiting, no pagination enforcement, and no query timeout.

---

### Timeline

| Time (UTC) | Event |
|------------|-------|
| 02:14 | Customer script begins hammering /export |
| 02:36 | Connection pool exhausted. API returns 500s across all endpoints. |
| 02:41 | PagerDuty fires. Marcus Chen paged. |
| 02:58 | Marcus identifies /export as root cause. Endpoint taken offline. |
| 03:10 | API restored for all other endpoints. |
| 08:26 | /export brought back online with emergency rate limiting patch. |

---

### Root Cause

The `/export` endpoint was shipped without:
- Per-user rate limiting
- Query pagination (full table scan on every call)
- Database query timeout
- Load testing against concurrent usage

The PR was reviewed by Jake Morrison (product) and approved. No infrastructure review was required at the time. The endpoint shipped the same day it was merged.

---

### Customer Impact

Three enterprise customers opened support tickets during the outage. Two escalated to account reviews.

By 2023-09-01, all three had churned:

| Customer | ARR | Reason Given |
|----------|-----|--------------|
| Meridian Analytics | $38,000 | "Reliability concerns" |
| Stackform Inc | $31,000 | "SLA breach" |
| NovaBuild | $25,000 | "Lost confidence in platform stability" |

Total ARR lost: **$94,000**

---

### What We Got Wrong

1. No rate limiting on a data-heavy endpoint that was trivially abusable
2. No infrastructure review required before shipping new API endpoints
3. No load testing gate before production
4. One customer's bad behaviour could take down the entire API (no isolation)

---

### Immediate Fix

Marcus applied emergency rate limiting at the nginx layer within 4 hours of the outage ending. Longer-term, Marcus built a reusable rate limiting middleware (`@rateLimit`) that is now available to all endpoint authors.

See: `Rate_Limiting_Middleware_Docs.md`

---

### People Involved

- **Marcus Chen** — Infrastructure Lead. On-call. Identified and resolved the outage.
- **Jake Morrison** — Product. Approved the PR. No awareness of infrastructure risk.
- **Priya Patel** — CTO. Notified at 03:00. Led customer comms.
- **Alex Rivera** — Built the /export endpoint. Unaware rate limiting was required.
