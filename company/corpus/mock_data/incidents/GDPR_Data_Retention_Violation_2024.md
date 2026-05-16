# INCIDENT REPORT
## GDPR — Data Retention Policy Violation, ICO Formal Warning

**Author:** Rachel Moore (external compliance consultant, engaged post-incident)  
**Date:** 2024-05-14  
**Severity:** Regulatory  
**Outcome:** ICO formal warning issued. No fine (first offence, cooperative response). Mandatory remediation plan required within 60 days. Significant legal fees: £34,000.  
**Root Cause:** No data retention policy existed. Deleted user data retained indefinitely in backups and analytics tables. Former user submitted Subject Access Request, discovered data retained 3 years post-deletion.  

---

### What Happened

In March 2024, a former user (account deleted in January 2021) submitted a Subject Access Request under UK GDPR Article 15, requesting all data held about them.

Sarah Kim received the SAR and forwarded it to Marcus to pull the data. Marcus found data in four locations:

1. The main user table — empty (user was deleted)
2. The `events` analytics table — **full event history from 2019–2021 retained, user ID present**
3. RDS automated backups — **user data present in backups going back 36 months**
4. The data warehouse (Redshift) — **user data present, never deleted**

The user's personal data had been retained for 3 years after they explicitly deleted their account.

Under UK GDPR, data must be deleted when no longer necessary for its original purpose. Deleted users' data is no longer necessary. There was no legal basis for the 3-year retention.

The user filed a complaint with the ICO. The ICO opened a formal investigation. Following a cooperative response and remediation plan, the ICO issued a formal warning rather than a fine.

Legal fees to respond to the investigation: £34,000.

---

### Root Cause

There was no data retention policy. Account deletion was implemented to remove rows from the users table. It was never implemented to cascade to the events table, the data warehouse, or the backup rotation schedule.

Nobody had ever thought through what "user deletes their account" meant for all the places their data lived.

---

### Timeline

| Date | Event |
|------|-------|
| 2021-01-14 | User deletes account |
| 2021-01-14 | User row deleted from users table. Nothing else deleted. |
| 2024-03-02 | Former user submits SAR |
| 2024-03-07 | Marcus identifies data in 4 locations |
| 2024-03-15 | ICO complaint received |
| 2024-04-01 | ICO formal investigation opens |
| 2024-05-14 | ICO formal warning issued. 60-day remediation plan required. |

---

### People Involved

- **Marcus Chen** — Responded to SAR data request. Found data in 4 locations.
- **Sarah Kim** — Received SAR, escalated appropriately.
- **Priya Patel** — ICO response lead. Engaged external compliance consultant.

---

### What Changed

Full data deletion cascade implemented across all data stores. Automated backup retention capped at 90 days. Data retention policy written and published. Annual GDPR review introduced.

See `Data_Retention_GDPR_Policy.md`.

> "Account deletion meant deleting a row in one table. We didn't think about where else the data lived. The answer was: everywhere."  
> — Marcus Chen
