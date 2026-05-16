# ENGINEERING CHECKLIST
## API Endpoint Pre-Ship Checklist

**Author:** Marcus Chen  
**Date:** 2023-09-01  
**Status:** MANDATORY — Required in every API endpoint PR  
**Related:** Rate_Limiting_Middleware_Docs.md, API_Outage_Export_Endpoint_2023.md  

---

### Why This Exists

On 2023-08-14, the `/export` endpoint shipped to production without rate limiting, pagination, or load testing. A single customer's script exhausted the database connection pool and took down the entire API for 6 hours. We lost $94,000 ARR.

This checklist is the gate that prevents that from happening again.

---

### Checklist (Required Before Merge)

Copy this into your PR description. All boxes must be checked.

```
## Infrastructure Checklist

### Rate Limiting
- [ ] Does this endpoint touch the database?
      If YES → @rate_limit decorator applied (see middleware/rate_limit.py)
- [ ] Is `per="org"` set for any endpoint that could affect other customers if abused?

### Pagination
- [ ] Can this endpoint return large datasets?
      If YES → max page size enforced (default: 1000 rows)
- [ ] Is offset/cursor pagination implemented?

### Timeouts
- [ ] Database query timeout set? (default: 10s)
- [ ] External API calls have timeout + retry logic?

### Load Testing
- [ ] k6 load test run at 10x expected peak concurrent load?
- [ ] No connection pool exhaustion observed under load?

### Infrastructure Review (Required if ANY of these apply)
- [ ] Endpoint performs aggregations or full table scans
- [ ] Endpoint exports or bulk-transfers data
- [ ] Endpoint triggers background jobs or queues
- [ ] Endpoint calls third-party APIs
→ If any box above is checked: ping @marcus or @priya before merging
```

---

### The One Rule

If you're about to write "we can add rate limiting after launch" — don't. Look at what happened in August 2023. It takes 2 lines. There is no valid reason to ship without it.

```python
@app.route("/api/v1/your-new-endpoint")
@rate_limit(requests_per_minute=60, per="org")   # ← 2 lines
def your_endpoint():
    ...
```

That's it.
