# ENGINEERING POLICY
## Code Review — No Exceptions

**Author:** Priya Patel  
**Date:** 2024-02-02  
**Status:** MANDATORY — All changes to main  
**Related Incident:** Direct push to main, auth outage Feb 2024 — 2h3m 100% auth failure  

---

### Background

On 2024-02-01, Alex pushed a "quick fix" directly to main without a PR or review. The three-line change introduced a logic error in JWT validation. Every API call returned 401 for 2 hours 3 minutes.

This policy removes the possibility of a repeat.

---

### Rules

#### Rule 1 — No Direct Pushes to Main. Ever.
All changes to main go through a pull request. There are no exceptions for:

- "Small" or "obvious" changes
- "Urgent" hotfixes
- Config changes
- One-liners
- Documentation

If it changes a file in the repository, it goes through a PR.

#### Rule 2 — Minimum One Approval Required
All PRs require at least one approval from a different engineer before merge. You cannot approve your own PR.

For changes touching: auth, billing, payments, database migrations, security — minimum two approvals required, one of which must be Marcus or Priya.

#### Rule 3 — Branch Protection Applies to Everyone
Main branch protection is enforced for all users, including repository admins. Admin access does not grant the ability to bypass branch protection.

Admin access (repository level) is held only by Priya Patel and Marcus Chen. It is for infrastructure management, not for bypassing review.

#### Rule 4 — Hotfixes Still Need Review
For genuine production emergencies, the process is:
1. Create a branch (`hotfix/description`)
2. Make the fix
3. Open a PR — even a 30-second review is better than no review
4. Get one approval (Marcus or Priya for auth/critical paths)
5. Merge

The 2024 incident took 2h3m to resolve. A 10-minute hotfix PR review would have caught the off-by-one error before it reached production.

#### Rule 5 — Review Checklist for Sensitive Code
When reviewing PRs that touch auth, validation, or security:

- [ ] Does the logic match the intent described in the PR description?
- [ ] Is there an off-by-one possibility in any comparisons?
- [ ] What happens at boundary conditions (midnight, expiry edge cases)?
- [ ] Has the author tested the specific edge case they claim to be fixing?

---

### The Quick Fix Trap

> "It was three lines. I was confident. I was wrong."  
> — Alex Rivera, February 2024

Confidence in a change is not a substitute for a second pair of eyes. The changes most likely to skip review are small and urgent — which are also the changes most likely to have subtle bugs that are invisible to their author.

The PR process takes 10 minutes. The auth outage took 2 hours 3 minutes and affected every user on the platform.
