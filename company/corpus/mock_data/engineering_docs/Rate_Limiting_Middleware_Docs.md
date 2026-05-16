# ENGINEERING DOCS
## Rate Limiting Middleware — @rateLimit

**Author:** Marcus Chen, Infrastructure Lead  
**Date:** 2023-09-01  
**Status:** MANDATORY — All new API endpoints  
**Outcome:** Zero repeat outages since adoption. Used on 14 endpoints.  
**Related Incident:** API Outage 2023-08-14 ($94K ARR lost)  

---

### Background

Built after the August 2023 outage. An unthrottled `/export` endpoint took down the entire API for 6 hours and cost us 3 enterprise customers. This middleware makes rate limiting a 2-line addition so there's no excuse to skip it.

---

### Usage

```python
from middleware.rate_limit import rate_limit

@app.route("/api/v1/export")
@rate_limit(requests_per_minute=60, per="user")
def export_data():
    ...
```

That's it. Two lines. No excuse not to use it.

---

### Configuration Options

```python
@rate_limit(
    requests_per_minute=60,   # default: 60
    per="user",               # "user" | "ip" | "org"
    burst=10,                 # allow short bursts above limit
    on_exceeded="429",        # return 429 with Retry-After header
)
```

---

### Why This Is Mandatory

From the August 2023 postmortem:

> "One customer's script ran at 340 req/min for 40 minutes. The connection pool exhausted. Every customer lost API access for 6 hours."

Any endpoint that touches the database can be abused the same way. The `per="org"` option means a single customer's bad behaviour cannot affect other customers.

---

### Endpoints Currently Rate Limited

| Endpoint | Limit | Per | Added |
|----------|-------|-----|-------|
| /export | 30 rpm | user | 2023-08-14 (emergency) |
| /bulk-import | 10 rpm | org | 2023-09-03 |
| /reports/generate | 20 rpm | user | 2023-09-08 |
| /webhooks/replay | 5 rpm | org | 2023-10-01 |

---

### Pre-Ship Checklist (required for all new endpoints)

Before any new API endpoint merges to main:

- [ ] `@rate_limit` applied if endpoint touches DB
- [ ] Pagination enforced if response can be large (max 1000 rows default)
- [ ] Query timeout set (default: 10s)
- [ ] k6 load test run at 10x expected peak
- [ ] Marcus Chen or Priya Patel infrastructure review if endpoint does: aggregations, exports, background job triggers, third-party API calls

This checklist exists because we didn't have it in August 2023 and it cost us $94,000.
