# INCIDENT REPORT
## P1 — Production Broken by Auto-Updated npm Dependency

**Author:** Marcus Chen  
**Date:** 2023-05-22  
**Severity:** P1  
**Duration:** 3 hours 47 minutes  
**Root Cause:** `date-fns` npm package auto-updated from v2.29 to v3.0 overnight. v3.0 contains breaking API changes. No version was pinned in package.json.  
**Outcome:** Dashboard date filtering completely broken for all users. 3h47m to identify cause and roll back.  

---

### What Happened

On the morning of 2023-05-22, the support queue filled with reports that date filtering on the analytics dashboard was returning no results. All date range queries were silently returning empty arrays.

Marcus investigated and found that the `date-fns` package had auto-updated from v2.29.3 to v3.0.0 overnight as part of a Dependabot auto-merge. The v3.0 release contained multiple breaking API changes — functions that were named exports in v2 became named differently in v3, and several argument orders changed.

The dashboard's date filtering logic relied on three functions from `date-fns` that had breaking changes in v3. Because the version was specified as `"date-fns": "^2.29.3"` in package.json, the caret allowed Dependabot to auto-update to any v2.x or v3.x release.

This was not caught because:
1. The Dependabot auto-merge was configured with no test gate
2. The date filtering code had no unit tests
3. The breakage was silent — it returned empty arrays, not errors, so no error monitoring fired

---

### Timeline

| Time | Event |
|------|-------|
| 03:14 | Dependabot auto-merges date-fns v3.0.0 update |
| 03:19 | Deployment completes |
| 08:47 | First support ticket — "date filter not working" |
| 09:12 | Marcus begins investigation |
| 10:31 | Root cause identified — date-fns v3 breaking change |
| 11:03 | date-fns pinned to v2.29.3, deployed |
| 12:03 | Dashboard date filtering restored |

---

### Why It Was Silent

`date-fns` v3 changed the `isWithinInterval` function to throw on invalid intervals rather than returning false. In our case, the interval construction was failing silently due to a separate argument order change, producing an invalid interval, which caused `isWithinInterval` to return false for all rows — producing empty results with no exception thrown and no error logged.

No alert fired. Users experienced "no data" rather than "error."

---

### People Involved

- **Marcus Chen** — Identified and resolved. Also the person who configured Dependabot auto-merge.
- **Alex Rivera** — Wrote the original date filtering code. No unit tests were written for it.
- **Jake Morrison** — Received the support escalations.

---

### What Changes

1. All dependencies in package.json pinned to exact versions (no `^` or `~`)
2. Dependabot auto-merge disabled — PRs require human review before merge
3. Unit tests required for any utility function touching data transformation
4. Silent failures (empty array returns on filter operations) now logged as warnings

See `Dependency_Management_Policy.md`.
