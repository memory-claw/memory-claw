# PROJECT POSTMORTEM
## DataVault Vendor Incident 2021 — Security Breach

**Author:** Rachel Moore, Compliance  
**Date:** 2021-11-22  
**Project:** CRM Data Infrastructure Upgrade  
**Vendor:** DataVault Systems Ltd  
**Outcome:** Security Breach — Unauthorised data access. £180,000 ICO fine. 6-month delay.  
**Risk Level:** Critical  
**Department:** IT / Compliance / Procurement  

---

### Summary

DataVault Systems Ltd was onboarded as a data infrastructure vendor in August 2021 following a fast-tracked procurement process. Standard vendor security assessments were skipped due to timeline pressure. In October 2021, DataVault suffered a breach affecting 14,000 customer records. We were held jointly liable as the data controller. The ICO issued a £180,000 fine and required mandatory security audits.

---

### What Happened

Emma Patel approved DataVault at procurement stage without a completed Cyber Essentials Plus check. The vendor had submitted an expired ISO 27001 certificate (lapsed 4 months prior). This was not caught during onboarding.

The breach occurred when DataVault's own infrastructure was compromised. Because we had not conducted penetration testing or verified their current security posture, we had no grounds to limit our liability.

---

### Timeline

| Date | Event |
|------|-------|
| 2021-08-03 | DataVault shortlisted |
| 2021-08-14 | Emma Patel approves onboarding — security checks marked as "to follow" |
| 2021-08-21 | DataVault begin work |
| 2021-10-09 | DataVault breach detected |
| 2021-10-11 | We notify ICO |
| 2021-11-01 | ICO issues £180,000 fine |
| 2021-11-22 | This postmortem |

---

### Root Cause

Fast-tracked onboarding with no security gate enforced. Expired ISO 27001 certificate accepted at face value. Cyber Essentials Plus check not completed before work began.

---

### Persons Involved

- **Emma Patel** — Procurement. Approved vendor without completed security checks.
- **Rachel Moore** — Compliance. Not consulted before onboarding.
- **James Liu** — Delivery Lead. Applied timeline pressure that drove the fast-track.

---

### Mandatory Process Change (Effective Immediately)

Rachel Moore has introduced the **Vendor Security Gate** — a mandatory 5-point checklist that must be completed before any data-handling vendor is approved:

1. Valid Cyber Essentials Plus certificate (not expired)
2. Current ISO 27001 or SOC 2 Type II certificate
3. Penetration test report (within 12 months)
4. Data Processing Agreement signed and reviewed by Legal
5. Rachel Moore compliance sign-off

**No data vendor may begin work without completing the Vendor Security Gate.**

---

### Financial Impact

- ICO Fine: £180,000
- Project delay: 6 months
- Emergency incident response: £45,000
- Reputational: Material. Two clients requested security audits of our practices.

---

### Key Lesson

> "We saved 3 weeks on onboarding and lost 6 months and £225,000. Speed is not a reason to skip a security check on a data vendor."  
> — Rachel Moore

If we are moving fast on a vendor and someone says "we'll do the security check later" — stop. That is exactly when the breach happens.
