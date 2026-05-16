# ENGINEERING POLICY
## Staging Environment — Mandatory Config and Integration Testing

**Author:** Marcus Chen / Priya Patel  
**Date:** 2022-09-26  
**Status:** MANDATORY — All configuration changes, integrations, and releases  
**Related Incident:** SendGrid config outage Sept 2022 — 11h email failure, 3 trial churns  

---

### Background

In September 2022, a credential rotation applied directly to production silently broke all email delivery for 11 hours. There was no staging environment to test the new credentials against. 47 welcome emails failed. 3 free trials churned.

"We'll add staging when we have more resources" was the plan from 2021. This incident ended that conversation. Staging was built immediately after.

---

### What Staging Is For

Staging is not for looking nice. It is for catching things before production does.

Every config change, every integration update, every credential rotation goes through staging first. If it works in staging, it can go to production. If it breaks in staging — good, that's what staging is for.

---

### Rules

#### Rule 1 — Staging Mirrors Production

Staging uses:
- The same application code as the most recent production deploy
- Equivalent infrastructure (same instance types, same DB engine version)
- Separate credentials with the same permission scopes as production
- Sandboxed third-party integrations (SendGrid sandbox mode, Stripe test mode, etc.)

If staging diverges significantly from production, we lose confidence in staging test results.

#### Rule 2 — All Config Changes Tested in Staging First

Any change to:
- API keys or credentials
- Environment variables
- Infrastructure configuration
- Third-party integration settings
- Feature flags

...must be applied to staging first and verified before production.

Verification means: the specific thing the config change affects actually works. For a SendGrid key rotation: send a test email in staging. Confirm delivery. Then rotate production.

#### Rule 3 — Email, Payment, and Auth Integrations Have Checklists

For SendGrid key rotation:
- [ ] New key generated with: Mail Send, Template Engine permissions
- [ ] Key applied to staging
- [ ] Test email sent and received
- [ ] Then apply to production
- [ ] Send test email in production within 5 minutes of rotation

Same principle applies to Stripe, Auth0, and any other critical integration.

#### Rule 4 — Failure Alerts for Critical Paths

Email delivery failure rate >2%: PagerDuty alert.  
Payment processing error rate >1%: PagerDuty alert.  
Auth error rate >5%: PagerDuty alert.

Silent failures are the most dangerous failures. If something is breaking quietly, we need to know.

---

### The "We'll Add It Later" Trap

> "We had no staging environment because we kept saying we'd add it when we had more resources. This incident cost us more than building staging would have."

"Later" means "after something breaks." Build the safety net before you need it.
