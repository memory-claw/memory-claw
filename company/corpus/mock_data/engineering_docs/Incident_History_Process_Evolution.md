# ENGINEERING DOCUMENT
## Incident History & Process Evolution — 2022–2024

**Author:** Marcus Chen  
**Date:** 2024-12-01  
**Purpose:** Complete record of production incidents, their root causes, and the process changes introduced. Used for onboarding, audits, and institutional memory.  

---

### Overview

This document is the single source of truth for every significant incident we've had and what changed as a result. It is updated after each major incident.

The pattern across almost every incident is the same: we moved fast, skipped a step that felt like overhead, and the cost of skipping it far exceeded the cost of the step.

---

## 2022

### July 2022 — Database Migration Data Loss
**What:** Schema migration ran without a manual snapshot or rollback script. Migration failed midway. Restore from automated snapshot (taken seconds before migration started). 3h40m of production writes permanently lost.  
**Cost:** 6 customers churned. $47,000 ARR.  
**Process change:** Database migration runbook — manual snapshot required, rollback script required, tested on prod clone, low-traffic window mandatory.  
**Doc:** `Database_Migration_Failure_2022.md`

### September 2022 — Email Outage (No Staging)
**What:** SendGrid API key rotated directly in production without staging test. New key missing Mail Send permission. All transactional emails silently failed for 11 hours.  
**Cost:** 3 free trial churns. 12 support tickets.  
**Process change:** Staging environment created. All config changes tested in staging first. Email delivery monitoring added.  
**Doc:** `No_Staging_Email_Outage_2022.md`

### October 2022 — AWS GPU Bill
**What:** Jake spun up GPU instances for an ML experiment. Instances ran for 18 days unmonitored. No billing alerts.  
**Cost:** $31,200 unplanned AWS spend. ~2 weeks of runway.  
**Process change:** Mandatory billing alerts. Resource tagging policy. #infra posting required for large instances. Auto-shutdown for experiment instances.  
**Doc:** `AWS_Bill_GPU_Instances_2022.md`

### December 2022 — Microservices Architecture Decision Reversed
**What:** Microservices architecture built for 12 customers. Velocity collapsed. Migrated back to monolith over 3 months.  
**Cost:** ~6 months engineering time (~$90,000). Features not shipped during period.  
**Process change:** "Build for where you are, not where you hope to be." No complex architectural patterns without a demonstrated scale problem.  
**Doc:** `Microservices_Premature_Architecture_2022.md`

---

## 2023

### March 2023 — GitHub Credentials Leak
**What:** .env file pushed to public repo. Bots detected in 47 seconds. $12,400 in crypto mining. Production DB connection string exposed.  
**Cost:** $3,200 net (AWS credited $9,200). Production DB exposure window: 4 minutes.  
**Process change:** git-secrets pre-commit hook. All .env files in .gitignore. Developers no longer have production credentials locally. GitHub Advanced Security enabled.  
**Doc:** `GitHub_Credentials_Leak_2023.md`

### May 2023 — Unpinned Dependency Auto-Updated, Silent Data Breakage
**What:** date-fns auto-updated via Dependabot auto-merge. v3 had breaking API changes. Dashboard date filtering returned empty results silently for 3h47m.  
**Cost:** 3h47m P1. Missed by monitoring because empty arrays ≠ errors.  
**Process change:** All versions pinned exactly. Dependabot auto-merge disabled. Unit tests required for data transformation functions. Silent failures logged as errors.  
**Doc:** `Unpinned_Dependency_Prod_Break_2023.md`

### August 2023 — API Outage, /export Endpoint
**What:** /export endpoint shipped without rate limiting. Customer script at 340 req/min exhausted Postgres connection pool. Entire API down 6 hours.  
**Cost:** 3 enterprise customers churned. $94,000 ARR.  
**Process change:** @rateLimit middleware (2 lines, mandatory on DB-touching endpoints). Pre-ship checklist. Load testing requirement.  
**Doc:** `API_Outage_Export_Endpoint_2023.md`

### September 2023 — Helix Enterprise Deal
**What:** $220K enterprise deal scoped without engineering input as "6 weeks." Took 7 months. Alex burned out and resigned. Customer churned anyway.  
**Cost:** -$130,000 net on a $220,000 deal. One engineer resigned.  
**Process change:** Mandatory engineering scope review before any enterprise deal over $50K signs. Change order clause in all enterprise contracts.  
**Doc:** `Helix_Enterprise_Deal_Postmortem_2024.md`

### September 2023 — H1 2023 Layoffs (Hiring Ahead of Revenue)
**What:** Hired 5 people in anticipation of Series A. Series A delayed. 2 engineers laid off 4–6 months after joining.  
**Cost:** Team trust significantly damaged. One original engineer updated LinkedIn and was visibly disengaged for 8 weeks.  
**Process change:** Hiring only on received funding or ARR that supports the hire at 18 months runway.  
**Doc:** `Hiring_Ahead_Of_Revenue_Retro_2023.md`

### November 2023 — Mapbox Pricing Crisis
**What:** Mapbox raised prices 12x with 30 days notice. Mapping feature built directly on Mapbox SDK with no abstraction layer or fallback. Emergency 6-week migration.  
**Cost:** Emergency migration: ~$28,000 engineering time. Would have lost $100,800/year if not migrated.  
**Process change:** Abstraction layer required for all core third-party integrations. Cost ceiling modelling before any paid API integration.  
**Doc:** `Mapbox_Pricing_Crisis_2023.md`

---

## 2024

### February 2024 — Direct Push to Main, Auth Outage
**What:** Alex pushed a "3-line quick fix" directly to main without PR or review. Off-by-one in JWT validation. 100% of API requests returned 401 for 2h3m.  
**Cost:** 100% of users broken for 2h3m.  
**Process change:** Branch protection enforced for all users including admins. Admin bypass removed. No exceptions to PR + review requirement.  
**Doc:** `Direct_Push_Main_Auth_Outage_2024.md`

### March 2024 — Billing UI No Feature Flag
**What:** Billing UI shipped to 100% of users without feature flag. Annual plan proration bug. 34% error rate. 2h12m rollback complicated by bundled deployment.  
**Cost:** 8 support tickets. 2 refunds.  
**Process change:** LaunchDarkly mandatory for billing, auth, checkout, and any change touching >20% of UI. 5% canary minimum for sensitive changes.  
**Doc:** `Billing_UI_NoFlag_Incident_2024.md`

### May 2024 — GDPR Data Retention Violation
**What:** Former user (deleted 2021) submitted SAR. Found their data in 4 locations: events table, RDS backups, Redshift, third-party analytics. No legal basis for 3-year retention.  
**Cost:** ICO formal warning. £34,000 legal fees.  
**Process change:** Full deletion cascade across all data stores within 30 days of account deletion. Backup retention capped at 90 days. New tables must document retention policy before shipping.  
**Doc:** `GDPR_Data_Retention_Violation_2024.md`

### July 2024 — Orion Financial Churn
**What:** Enterprise customer ($96K ARR) opened 3 high-priority tickets. Two went 72+ hours without substantive response. No SLA, no alerts, no escalation path.  
**Cost:** $96,000 ARR. $136,000 including replacement cost.  
**Process change:** Enterprise support SLA — 8-hour first response for P2, 2-hour for P1. Automated escalation alerts. Monthly account health reviews.  
**Doc:** `Orion_Financial_Churn_Analysis_2024.md`

---

### The Pattern

Every incident in this list has the same shape:

1. Someone skipped a step (review, test, snapshot, SLA, flag, policy)
2. The step felt like overhead
3. The cost of skipping exceeded the cost of the step by 10x–100x

The rate limiting middleware takes 2 minutes. The pre-ship checklist takes 5 minutes. The staging test takes 20 minutes. The code review takes 10 minutes.

The outages, churns, fines, and layoffs they prevented took months and cost hundreds of thousands.

Every policy in this company exists because of an entry in this document.
