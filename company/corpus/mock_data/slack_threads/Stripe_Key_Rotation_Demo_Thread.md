# SLACK THREAD EXPORT
## Channel: #engineering
## Date: 2025-02-11

---

**Marcus Chen** [3:44 PM]
doing the quarterly Stripe key rotation today. going to apply the new keys directly to prod, it's just a credential swap

**Alex Rivera** [3:46 PM]
seems fine, it's not a code change

---

*[AGENT INTERVENTION — 3:46 PM]*

---

**🔎 Memory** [3:46 PM]

> **The last time a credential was applied directly to production without staging testing, email broke for 11 hours.**
>
> In September 2022, Marcus rotated the SendGrid API key directly in production. The new key was missing the "Mail Send" permission — it only had "Template Engine" and "Stats." All transactional emails silently failed for 11 hours overnight. 47 welcome emails, 23 password reset requests, 8 billing receipts — all silently dropped. 3 free trial users never received their welcome email and didn't come back.
>
> The staging environment was built specifically because of this incident. The policy (September 2022) requires all credential and config changes to be applied to staging first, verified, then production. For Stripe key rotation specifically: apply to staging, trigger a test payment in Stripe test mode, confirm it processes, then rotate production.
>
> "It's just a credential swap" was also the thinking in September 2022.
>
> 📎 `No_Staging_Email_Outage_2022.md` · `Staging_Environment_Policy.md`

---

**Marcus Chen** [3:48 PM]
yeah ok. applying to staging first. 

**Marcus Chen** [3:56 PM]
staging good — test payment processed fine. rotating production now

**Alex Rivera** [3:58 PM]
👍 good process
