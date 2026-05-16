# COMPLIANCE POLICY
## Data Retention and Deletion — GDPR Compliance

**Author:** Rachel Moore (external consultant) / Priya Patel  
**Date:** 2024-06-01  
**Status:** MANDATORY — All data storage and deletion workflows  
**Related Incident:** GDPR SAR violation 2024 — ICO formal warning, £34,000 legal fees  

---

### Background

In March 2024, a user who deleted their account in 2021 submitted a Subject Access Request. We found their data in four places: the events table, RDS backups, Redshift, and a third-party analytics tool. We had no legal basis to retain data for a deleted user for 3 years. The ICO opened an investigation. We received a formal warning and paid £34,000 in legal fees.

This policy prevents recurrence.

---

### Data Retention Rules

#### Rule 1 — Deleted Users: Full Cascade Within 30 Days

When a user deletes their account, all personal data must be deleted or anonymised within 30 days from all storage locations:

| Location | Action | Responsible |
|----------|--------|-------------|
| `users` table | Delete row | Existing (done) |
| `events` table | Delete or anonymise rows where user_id matches | Marcus — implemented |
| `sessions` table | Delete rows | Marcus — implemented |
| Redshift data warehouse | Delete or anonymise | Marcus — implemented |
| Third-party analytics (Mixpanel, etc.) | Suppress/delete via API | Marcus — implemented |
| Email (Mailchimp/SendGrid) | Remove from all lists | Sarah Kim |

Deletion cascade is now automated via the `user_deletion_job` worker. It runs within 24 hours of account deletion.

#### Rule 2 — Backup Retention Capped at 90 Days

RDS automated backups are retained for a maximum of 90 days. Previously: indefinite.

This means a user deleted today will not appear in any backup after 90 days.

#### Rule 3 — Responding to Subject Access Requests (SARs)

SARs must be responded to within 30 days (UK GDPR requirement).

When a SAR is received by Sarah Kim or any team member:
1. Forward to Priya Patel within 24 hours
2. Marcus to identify all data locations within 5 days
3. Compile full data export or deletion confirmation
4. Legal review if there is any complexity
5. Respond to user within 30 days

Do not ignore or delay SARs. The ICO tracks response times.

#### Rule 4 — New Data Stores Require Retention Review

Before creating any new database, table, data warehouse schema, or third-party data integration, the following must be documented:
- What personal data (if any) is stored?
- What is the retention period?
- How is data deleted when a user deletes their account?
- How is data deleted after the retention period expires?

If you can't answer these before building: talk to Priya before building.

#### Rule 5 — Annual GDPR Review

Priya runs an annual GDPR compliance review in Q1. Output: a data map of all personal data locations, retention periods, and deletion mechanisms. Any gaps are remediation items.

---

### The SAR Lesson

> "Account deletion meant deleting a row in one table. We didn't think about where else the data lived. The answer was: everywhere."

When you add a new place data lives — a new table, a new warehouse, a new analytics tool — ask: "what happens to this data when a user deletes their account?" That question should have an answer before you ship.
