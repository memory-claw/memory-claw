# SLACK THREAD EXPORT
## Channel: #engineering
## Date: 2025-01-29

---

**Alex Rivera** [11:43 AM]
hey marcus, i've got a migration ready for the new analytics schema. planning to run it on prod this afternoon. it's pretty simple, just adding 3 columns to the events table

**Marcus Chen** [11:46 AM]
have you taken a manual snapshot?

**Alex Rivera** [11:47 AM]
i figured the automated snapshot from this morning would cover it, it ran like 2 hours ago

**Marcus Chen** [11:48 AM]
hmm

---

*[AGENT INTERVENTION — 11:48 AM]*

---

**🔎 Memory** [11:48 AM]

> **The automated snapshot is not enough — we learned this the hard way.**
>
> In July 2022, Marcus ran a migration assuming the automated snapshot covered him. The migration failed midway. The rollback script didn't exist. The restore point was the automated snapshot — which had run at exactly the same time as the migration started, so it predated it by seconds.
>
> We lost **3 hours 40 minutes of production writes.** 6 customers churned. **$47,000 ARR lost.**
>
> The migration runbook (July 2022) requires: (1) manual snapshot taken and confirmed before running anything, (2) rollback script written and tested on staging, (3) migration tested on a production-data clone, (4) run in a low-traffic window (02:00–04:00 UTC). "Pretty simple" migrations are how the July 2022 one started — it was adding one table and one constraint.
>
> 📎 `Database_Migration_Failure_2022.md` · `Database_Migration_Runbook.md`

---

**Marcus Chen** [11:50 AM]
yeah. take a manual snapshot. write the rollback script. test on staging. then we can talk about running it

**Alex Rivera** [11:51 AM]
ok fair. i'll do it properly. can probably run it tonight in the low traffic window

**Marcus Chen** [11:52 AM]
that's the move. ping me before you run it and i'll be around

**Alex Rivera** [11:53 AM]
will do. sending the rollback script to you to review first

**Marcus Chen** [11:54 AM]
👍 that's exactly right
