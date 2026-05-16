# SLACK THREAD EXPORT
## Channel: #releases
## Date: 2025-02-19

---

**Alex Rivera** [3:02 PM]
new checkout flow is ready to ship. been on staging for a week, looking good

**Jake Morrison** [3:05 PM]
nice! does it have a feature flag?

**Alex Rivera** [3:06 PM]
i was just going to ship it to everyone, it's been tested pretty thoroughly

**Jake Morrison** [3:07 PM]
it touches the checkout flow though so i'd want a flag on it

**Alex Rivera** [3:08 PM]
it's just UI changes, no logic changes. should be fine right?

---

*[AGENT INTERVENTION — 3:08 PM]*

---

**🔎 Memory** [3:08 PM]

> **The billing UI in March 2024 was also "just UI changes."**
>
> Alex shipped the redesigned billing UI directly to 100% of users — no feature flag, no canary. It contained a proration calculation bug that only affected annual plan users (34% of the base). Error rate hit 34% within 11 minutes. Rolling back took 2h12m because the billing changes were bundled with unrelated frontend code. 8 support tickets. 2 refunds.
>
> The feature flag policy (March 2024) requires a flag for any change touching billing, payments, checkout, or authentication — and mandates a 5% canary stage for at least 24 hours before wider rollout.
>
> "It's been tested" doesn't cover edge cases in production data that staging doesn't have. The proration bug only appeared on annual plans with specific billing cycle timing — it didn't show up in testing either.
>
> 📎 `Billing_UI_NoFlag_Incident_2024.md` · `Feature_Flag_Policy.md`

---

**Jake Morrison** [3:10 PM]
yeah what it said. checkout = flag. always.

**Alex Rivera** [3:11 PM]
ok fair point. i'll add the launchdarkly flag now. 5% canary first?

**Jake Morrison** [3:12 PM]
yes. 5% for 24 hours, watch the error rates, then expand if clean

**Alex Rivera** [3:13 PM]
on it. will have the flagged version ready in 30 mins
