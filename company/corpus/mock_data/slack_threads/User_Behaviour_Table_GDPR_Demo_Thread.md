# SLACK THREAD EXPORT
## Channel: #engineering
## Date: 2025-02-20

---

**Alex Rivera** [11:33 AM]
hey, i'm adding a new `user_behaviour` table to track detailed clickstream data for the new personalisation feature. going to store user_id, event_type, element_id, timestamp

**Jake Morrison** [11:36 AM]
nice, that'll give us good data for the ML model

**Alex Rivera** [11:37 AM]
yeah exactly. i'll just log everything and we can figure out what's useful later

---

*[AGENT INTERVENTION — 11:37 AM]*

---

**🔎 Memory** [11:37 AM]

> **New table storing user_id — needs a deletion plan before it ships.**
>
> In March 2024, a user who deleted their account in 2021 submitted a Subject Access Request. Marcus found their data in four locations — including the `events` analytics table, which stored user_id-linked data and was never included in the account deletion workflow. The user's data had been retained for 3 years post-deletion with no legal basis.
>
> The ICO opened a formal investigation. We received a formal warning and paid **£34,000 in legal fees.**
>
> The GDPR data retention policy (June 2024) requires that before any new table storing personal data ships, you document: what personal data is stored, the retention period, and how it's deleted when a user deletes their account. The `user_deletion_job` worker needs to be updated to include the new table before it goes to production.
>
> "We'll figure out what's useful later" also means you'll be retaining data you don't have a legal basis to keep.
>
> 📎 `GDPR_Data_Retention_Violation_2024.md` · `Data_Retention_GDPR_Policy.md`

---

**Alex Rivera** [11:39 AM]
oh damn. ok i didn't know about the SAR thing

**Marcus Chen** [11:40 AM]
yeah it was a nightmare. update the user_deletion_job to include user_behaviour before you ship. i'll send you the worker code

**Alex Rivera** [11:41 AM]
and what's the retention period for clickstream data?

**Priya Patel** [11:43 AM]
i'd say 12 months max. we don't need behaviour data older than that for personalisation. add a nightly cleanup job deleting rows older than 365 days

**Alex Rivera** [11:44 AM]
got it. documenting retention policy in the PR description and updating the deletion job. thanks for flagging
