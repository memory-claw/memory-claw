# DRAFT — Vantara Capital Integration Proposal v0.1
## Internal working doc — do not share externally yet

**Owner:** Jake Morrison  
**Date:** 2025-01-30  
**Status:** DRAFT — pending engineering scoping  

---

### Overview

Vantara Capital has expressed interest in an enterprise plan at $180K ARR. This doc outlines the proposed integration scope for internal review before we finalise the contract.

---

### What They Want

Based on the sales call (Sarah Kim, 2025-01-28):

- **Custom SSO** — Vantara uses Okta. They need SAML-based SSO with their internal identity provider. Users should auto-provision on first login.
- **Data pipeline** — They want a nightly export of their usage data into their internal Redshift instance. Custom schema mapping required.
- **White-labelled dashboard** — Their compliance team wants the dashboard to appear under the Vantara brand. Custom domain, logo, colour scheme.

---

### Sarah's Estimate

Sarah told them 8 weeks for full onboarding. This was based on previous smaller deals and has not been reviewed by engineering.

---

### Open Questions

- Does Marcus have capacity to lead the SSO integration?
- What's the realistic timeline for all three workstreams in parallel?
- Do we have a standard SAML integration or does this need to be built?
- Redshift pipeline — custom or can we reuse the existing export infrastructure?

---

### Next Steps

- [ ] Engineering review before contract goes out
- [ ] Marcus to estimate SSO + pipeline work
- [ ] Confirm white-label timeline with Alex
- [ ] Sarah to hold contract until estimates are in
