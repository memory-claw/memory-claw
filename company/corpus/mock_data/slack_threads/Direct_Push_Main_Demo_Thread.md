# SLACK THREAD EXPORT
## Channel: #engineering
## Date: 2025-01-31

---

**Alex Rivera** [4:47 PM]
hey, found a small bug in the session timeout logic. super obvious fix, literally one line. can i just push it directly to main? don't want to wait for a PR review at this time of day

**Jake Morrison** [4:49 PM]
yeah seems fine for a one-liner, go for it

---

*[AGENT INTERVENTION — 4:49 PM]*

---

**🔎 Memory** [4:49 PM]

> **"One-liner, no review needed" caused a 2-hour auth outage in February 2024.**
>
> Alex pushed a 3-line "quick fix" to the JWT token expiry validation directly to main. It introduced an off-by-one error in the expiry comparison — `>=` instead of `>`. Every API request returned 401. 100% of users were broken for **2 hours 3 minutes.**
>
> The fix was three lines. Alex was confident it was correct. A reviewer would have caught the boundary condition in under a minute.
>
> Branch protection on main is enforced for all users including admins — admin access was revoked as a bypass route after that incident. The code review policy (Feb 2024) has no exceptions: auth, session, and validation changes require two approvals.
>
> Session timeout logic is auth-adjacent. PR please — Marcus or Priya needs to be one of the approvers.
>
> 📎 `Direct_Push_Main_Auth_Outage_2024.md` · `Code_Review_Policy.md`

---

**Alex Rivera** [4:51 PM]
yeah ok fair. opening a PR now

**Marcus Chen** [4:52 PM]
i'll review it now, won't take long

**Alex Rivera** [4:53 PM]
appreciate it. PR up: #341

**Marcus Chen** [5:01 PM]
reviewed — actually spotted a potential edge case in the null check. left a comment. good catch catching this, and good call on the PR

**Alex Rivera** [5:02 PM]
oh wow yeah that would've been bad. updating now
