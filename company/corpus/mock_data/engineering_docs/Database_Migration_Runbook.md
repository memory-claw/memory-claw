# ENGINEERING RUNBOOK
## Database Migration — Mandatory Procedure

**Author:** Marcus Chen  
**Date:** 2022-07-10  
**Status:** MANDATORY — All production database migrations  
**Related Incident:** DB Migration Failure July 2022 — 3h40m data loss, $47K ARR churned  

---

### The Rule

Never run a migration on production without completing this checklist in order. No exceptions for "small" migrations. The July 2022 migration was adding one table and one constraint. It caused 3h40m of data loss.

---

### Pre-Migration Checklist (Complete Before Running Anything)

```
BEFORE EVERY PRODUCTION MIGRATION:

[ ] 1. Manual RDS snapshot taken and confirmed complete
        → Do not rely on automated snapshots
        → Confirm in AWS console: snapshot status = "available"
        → Note the snapshot ID: _______________

[ ] 2. Rollback script written and tested on staging
        → The rollback must reverse every step of the migration
        → Run the migration on staging, then run the rollback, confirm clean state
        → If you can't write a rollback: do not run the migration in this form

[ ] 3. Migration tested on a production-data clone
        → Staging data is often cleaner than production
        → Run the migration against a recent production snapshot in a separate RDS instance
        → Confirm it completes without errors on real data

[ ] 4. Low-traffic window confirmed
        → Check analytics: run migrations between 02:00–04:00 UTC
        → Never run during business hours unless emergency

[ ] 5. Marcus or Priya aware and available
        → Post in #infra: "Running migration [name] at [time]. Rollback ready. Snapshot ID: [id]"
        → Someone with DB access must be available for the full migration window

[ ] 6. Estimated runtime confirmed
        → For tables > 1M rows: run EXPLAIN ANALYZE on the migration SQL first
        → If estimated runtime > 5 minutes: plan for a zero-downtime migration strategy (not a blocking ALTER)
```

---

### During the Migration

Run with output logging:
```bash
psql $DATABASE_URL -f migration.sql 2>&1 | tee migration_$(date +%Y%m%d_%H%M%S).log
```

If any step fails: **stop immediately. Do not proceed. Run the rollback.**

---

### If the Migration Fails

1. Run the rollback script immediately
2. Message Marcus in Slack
3. Do NOT attempt to manually fix the database state without Marcus present
4. If rollback also fails: restore from the snapshot taken in step 1

---

### Why The Automated Snapshot Is Not Enough

The July 2022 incident: the automated snapshot ran at 18:20. The migration started at 18:20. The snapshot predated the migration by seconds. When we restored, we lost everything written since the snapshot — which was everything written during the outage window.

A manual snapshot taken immediately before the migration is the only guarantee you have a clean restore point.

---

### Post-Migration

- [ ] Verify application is functioning on affected tables
- [ ] Check error rates in Datadog for 30 minutes post-migration
- [ ] Post in #infra: "Migration [name] complete. No issues." or escalate immediately
- [ ] Delete the production-clone RDS instance used for testing (cost policy)
