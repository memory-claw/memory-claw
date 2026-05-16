# INCIDENT REPORT
## P0 — Auth Broken, Direct Push to Main Without Review

**Author:** Priya Patel  
**Date:** 2024-02-01  
**Severity:** P0  
**Duration:** 2 hours 3 minutes  
**Root Cause:** Alex pushed a "one-line fix" directly to main, bypassing code review. The fix introduced a logic error in the JWT validation middleware. All API requests returned 401.  
**Outcome:** Complete authentication failure. 100% of API calls broken for 2h3m.  

---

### What Happened

At 16:44 UTC on 2024-02-01, Alex Rivera pushed a commit directly to the `main` branch, bypassing the pull request process. The commit message was "fix: token expiry edge case (quick fix)".

The change modified the JWT token validation middleware to handle a reported edge case where tokens issued close to midnight were being incorrectly rejected. The fix introduced an off-by-one error in the expiry comparison — specifically, it used `>=` where it should have used `>`, causing all tokens to be considered expired regardless of their actual expiry time.

Every authenticated API request began returning 401 Unauthorized. This affected 100% of users attempting to use the product.

Alex was not aware of the severity because the logic error was subtle and the change was three lines. There was no code review to catch it.

---

### Timeline

| Time (UTC) | Event |
|------------|-------|
| 16:44 | Alex pushes directly to main. Deployment triggers. |
| 16:49 | Deployment complete. Auth broken for all users. |
| 16:57 | First support ticket: "getting logged out constantly" |
| 17:03 | Marcus paged — PagerDuty 100% error rate on auth endpoints |
| 17:11 | Root cause identified |
| 17:15 | Revert commit pushed |
| 18:20 | Auth confirmed working for all users |
| 18:52 | Full incident resolved |

---

### Why It Was Possible to Push Directly to Main

Branch protection rules on the `main` branch required a pull request and one approval — but Alex had admin access to the repository and was able to bypass branch protection. Admin access had been granted to Alex for a specific infrastructure task 6 months prior and was never revoked.

Additionally, there was a cultural understanding that "small, urgent fixes" could bypass the PR process when the author was confident in the change.

---

### People Involved

- **Alex Rivera** — Pushed directly to main. Believed the fix was safe.
- **Marcus Chen** — On-call. Identified and reverted.
- **Priya Patel** — Incident lead. Authored this report.

---

### What Changes

1. Admin access revoked from all engineers not explicitly requiring it for ongoing infrastructure work. Admin = Priya and Marcus only.
2. Branch protection on `main` enforced for all users including admins — no bypassing via admin access.
3. "Quick fix" culture explicitly removed from engineering norms. There is no such thing as a safe direct push to main.
4. Required reviewers: at minimum one approval from a different engineer before merge to main.

See updated `Code_Review_Policy.md`.

> "It was three lines. I was confident. I was wrong. Two hours of downtime for a three-line change with no review."  
> — Alex Rivera
