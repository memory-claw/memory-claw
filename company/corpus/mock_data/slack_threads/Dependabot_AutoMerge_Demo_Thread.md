# SLACK THREAD EXPORT
## Channel: #engineering
## Date: 2025-02-06

---

**Alex Rivera** [10:22 AM]
hey, should we turn on dependabot auto-merge? getting a bit of a backlog of dependency PRs and it would be nice to just have it handle the minor updates automatically

**Jake Morrison** [10:25 AM]
yeah sounds like a good idea, less manual overhead

**Alex Rivera** [10:26 AM]
cool i'll enable it for patch and minor version bumps

---

*[AGENT INTERVENTION — 10:26 AM]*

---

**🔎 Memory** [10:26 AM]

> **Dependabot auto-merge caused a P1 in May 2023.**
>
> `date-fns` auto-updated from v2.29.3 to v3.0.0 at 3am via Dependabot auto-merge. v3 had breaking API changes — three functions we used changed signatures. The dashboard date filtering returned empty results for all users for **3 hours 47 minutes.** The failure was silent — empty arrays, no errors, no alerts. Users found it before monitoring did.
>
> The dependency management policy (May 2023) explicitly disables Dependabot auto-merge for this reason. Dependency updates require human changelog review and CI passing before merge. "Minor version bump" doesn't guarantee no breaking changes — date-fns called v2→v3 a major bump but Dependabot classified it as an auto-mergeable update under the `^` caret range.
>
> The backlog of Dependabot PRs is on Marcus's Monday review list. If it's getting long, ping Marcus to batch-review them — that's faster than dealing with a silent production breakage.
>
> 📎 `Unpinned_Dependency_Prod_Break_2023.md` · `Dependency_Management_Policy.md`

---

**Alex Rivera** [10:28 AM]
oh yeah i forgot about the date-fns thing. that was a horrible one to debug

**Marcus Chen** [10:29 AM]
yeah let's not do that again. i'll go through the backlog this afternoon, there's only like 8 PRs

**Jake Morrison** [10:30 AM]
perfect. manual review it is
