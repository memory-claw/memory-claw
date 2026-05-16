# INCIDENT REPORT
## P0 — Database Migration Failure, 3 Hours 40 Minutes of Data Loss

**Author:** Marcus Chen, Infrastructure Lead  
**Date:** 2022-07-08  
**Severity:** P0 — Data loss  
**Duration:** 3 hours 40 minutes of production writes lost  
**Affected:** All customers writing data between 18:20 and 22:00 UTC  
**Root Cause:** Schema migration run on production without backup. Migration failed midway. Rollback impossible. Restored from last snapshot.  
**Outcome:** 3h40m of customer data permanently lost. 6 customers churned. $47,000 ARR lost.  

---

### What Happened

At 18:20 UTC on 2022-07-08, Marcus ran a schema migration on the production Postgres database to add a new `user_segments` table and add a foreign key constraint to the `events` table.

The migration failed at step 3 of 5 when the foreign key constraint violated existing rows in the `events` table that contained null user IDs (a legacy data quality issue). The database was left in a partially migrated state — the new table existed but the constraint had failed, leaving the schema inconsistent.

Attempting to roll back the migration also failed — the rollback script had not been written or tested.

At this point, the production database was in an inconsistent state. The application began throwing errors for any write that touched the `events` table. This affected approximately 60% of user actions.

The decision was made to restore from the most recent RDS snapshot. The last snapshot was taken at 18:20 UTC — coincidentally exactly when the migration started, as the automated snapshot had just completed.

The restore took 1h45m. By the time the database was restored and the application was reconnected, the time was 22:00 UTC.

All writes between 18:20 and 22:00 UTC — 3 hours 40 minutes — were permanently lost.

---

### Why There Was No Backup

Marcus had intended to take a manual snapshot before running the migration but did not do so, assuming the automated snapshot schedule meant one had recently been taken. The automated snapshot had run at 18:20 — but because the migration also started at 18:20, the snapshot predated the migration by seconds and was used as the restore point.

There was no pre-migration snapshot. The automated snapshot is not a substitute.

---

### Timeline

| Time (UTC) | Event |
|------------|-------|
| 18:20 | Automated RDS snapshot completes |
| 18:20 | Marcus begins running migration |
| 18:23 | Migration fails at step 3. DB in inconsistent state. |
| 18:31 | Application errors detected. Marcus paged. |
| 18:40 | Rollback attempted. Fails — no rollback script. |
| 18:55 | Decision to restore from snapshot. |
| 19:00 | RDS restore begins. |
| 20:45 | Restore complete. Application reconnected. Testing. |
| 22:00 | Full service restored. |
| 22:01 | 3h40m of data confirmed unrecoverable. |

---

### Customer Impact

6 customers who were actively using the product during the outage window contacted support. Three of them had been entering data that was lost. All six churned within 30 days. ARR impact: $47,000.

---

### People Involved

- **Marcus Chen** — Ran the migration without a backup. No rollback script prepared.
- **Priya Patel** — Incident lead. Customer comms.
- **Jake Morrison** — Not involved in incident but introduced the post-incident migration checklist.

---

### What Changes

Marcus introduced a mandatory migration runbook. See `Database_Migration_Runbook.md`.

> "I ran a migration on production without a backup because I assumed the automated snapshot covered me. It didn't. We lost 3h40m of customer data permanently. I will never run a migration without a manual snapshot again."  
> — Marcus Chen
