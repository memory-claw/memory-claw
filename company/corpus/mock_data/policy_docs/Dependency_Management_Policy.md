# ENGINEERING POLICY
## Dependency Management — Pinning and Update Process

**Author:** Marcus Chen  
**Date:** 2023-05-24  
**Status:** MANDATORY — All repositories  
**Related Incident:** Unpinned date-fns auto-update, May 2023 — 3h47m P1, silent data breakage  

---

### Background

On 2023-05-22, `date-fns` auto-updated from v2.29.3 to v3.0.0 overnight via Dependabot auto-merge. v3 contained breaking API changes. Dashboard date filtering returned empty results for all users for 3h47m. No error fired — the failure was silent.

The fix was pinning the version. This policy ensures we don't let auto-updates reach production without a human review.

---

### Rules

#### Rule 1 — Pin All Versions
All dependencies in `package.json` and `requirements.txt` must use exact version pinning:

```json
// WRONG
"date-fns": "^2.29.3"
"axios": "~1.4.0"

// RIGHT
"date-fns": "2.29.3"
"axios": "1.4.0"
```

For Python:
```
# WRONG
requests>=2.28.0

# RIGHT
requests==2.28.2
```

No carets. No tildes. No ranges.

#### Rule 2 — Dependabot Auto-Merge Disabled
Dependabot is configured to open PRs for dependency updates. It is not configured to auto-merge them.

Dependency update PRs require:
- Human review of the changelog for breaking changes
- CI passing (all tests green)
- Marcus or Alex approval before merge

Do not re-enable auto-merge without Priya's explicit approval.

#### Rule 3 — Weekly Dependency Review
Marcus reviews open Dependabot PRs every Monday. Security updates are prioritised. Major version bumps require a changelog review and are tested on staging before merging.

#### Rule 4 — Silent Failures Must Be Logged
Any function that could return an empty result due to an error condition must log a warning. "No data" and "error producing data" must be distinguishable in the logs.

The May 2023 incident was invisible to monitoring for 5+ hours because empty arrays are valid return values. Silent failures are bugs waiting to be found at the worst time.

#### Rule 5 — Unit Tests for Data Transformation
Any function that filters, transforms, or aggregates data must have unit tests covering:
- The happy path
- Empty input
- Invalid input (what does the function return?)
- Edge cases specific to the domain (date ranges, null values, etc.)

The date filtering code had no tests. That's why the v3 breakage wasn't caught before users found it.

---

### The date-fns Lesson

> "The package updated at 3am. It broke silently. Users found it at 9am. We found the cause at 10:30am. It was a one-line fix. The 3h47m was entirely spent figuring out what had changed."

Pinned versions mean you update on your schedule, not npm's.
