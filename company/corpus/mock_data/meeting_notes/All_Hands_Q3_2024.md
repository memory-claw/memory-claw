# MEETING NOTES
## All-Hands — Q3 2024

**Date:** 2024-07-01  
**Facilitator:** Priya Patel  
**Attendees:** Full team  

---

### Company Update

Priya opened with ARR: $1.2M, up from $880K at start of year. MRR growth rate: 8% month-over-month for past 3 months. Runway: 19 months at current burn.

One notable callout: Orion Financial ($96K ARR) churned in June. Sarah walked through the root cause — support response times. The enterprise support SLA policy is now in place. Sarah committed to a monthly account health review for the top 10 accounts.

---

### Engineering Update — Marcus Chen

Marcus presented the quarter's incident summary:

**Zero P0s this quarter.** First quarter without a P0 since Q1 2022.

Marcus attributed this to three things:
1. The `@rateLimit` middleware is now on every endpoint that touches the database
2. Staging environment being used for all config changes before production
3. Alex joining the on-call rotation, reducing Marcus's single-point-of-failure risk

Outstanding risk items:
- Redshift cost is growing faster than usage — Marcus flagged as a Q4 review item
- Two Dependabot PRs pending review for major version bumps — reviewing next Monday

---

### Product Update — Jake Morrison

Q2 shipped: bulk CSV import (highest-requested enterprise feature), redesigned onboarding flow, new dashboard filters.

Q3 priorities: AI-assisted search (spec complete, starting build), mobile-responsive improvements, API v2.

Jake noted that feature flags are now standard on all releases. The March 2024 billing UI incident has not recurred.

---

### Sales Update — Sarah Kim

8 new enterprise logos in Q2. Average deal size: $68K ARR, up from $51K in Q1.

Enterprise deal process is working — all 8 Q2 deals had engineering scope reviews before signing. All 8 are tracking on time for delivery.

Notable: Vantara (closed Q1) is expanding — likely to double their ARR in Q4 renewal.

---

### Open Q&A

**Q (Alex): Can we talk about the on-call rotation?**  
Marcus confirmed the rotation is now alternating weekly between him and Alex. Priya noted that as the team grows, the goal is 4-person rotation by end of 2025.

**Q (Jake): The GDPR data retention thing — are we fully compliant now?**  
Marcus confirmed: user_deletion_job updated, backup retention capped at 90 days, annual GDPR review scheduled for Q1 2025. Rachel Moore (external consultant) has reviewed and signed off.

---

### Closing

Priya closed with the company's operating principle going into Q4: **build for where we are, not where we hope to be.** Decisions should be made on current data, not projections.

*Reference to the microservices retrospective and the hiring retrospective — both times we optimised for a future that didn't arrive on schedule.*
