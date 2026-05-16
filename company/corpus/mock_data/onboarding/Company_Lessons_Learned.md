# ONBOARDING DOCUMENT
## What We've Learned — Institutional Lessons for New Team Members

**Author:** Priya Patel  
**Date:** 2024-06-01  
**Audience:** All new hires, engineering and non-engineering  
**Purpose:** The institutional memory that doesn't show up in the codebase  

---

### Why This Document Exists

Every company has a set of lessons that were learned the hard way. At most companies, this knowledge lives in the heads of people who were there when it happened. When those people leave, the lesson leaves with them.

This document captures ours. It is not exhaustive — it covers the incidents that shaped how we operate today. If you join and later wonder why we have a particular policy or process that seems like overhead, the answer is almost certainly in here.

---

## Engineering Lessons

### 1. Rate limit everything that touches the database

In August 2023, an unthrottled `/export` endpoint took down our entire API for 6 hours. One customer's automated script ran at 340 requests per minute. The Postgres connection pool exhausted in 22 minutes. Three enterprise customers churned. $94,000 ARR lost.

Marcus built `@rateLimit` middleware after this. It's 2 lines of code. It's mandatory on any endpoint that hits the database. See `Rate_Limiting_Middleware_Docs.md`.

**If you ever hear "we can add rate limiting after launch":** that is the August 2023 conversation. Stop it.

---

### 2. Tag your AWS resources and always take a manual snapshot before migrations

In October 2022, Jake spun up GPU instances for a weekend ML experiment. They ran for 18 days unmonitored. The AWS bill was $34,400. We had 4.5 months of runway.

In July 2022, Marcus ran a database migration without a manual snapshot, assuming the automated snapshot covered it. The migration failed. The restore point was the automated snapshot — which had run seconds before the migration started. 3 hours 40 minutes of customer data was lost permanently. Six customers churned.

Both incidents produced policies. Read `Cloud_Cost_Policy.md` and `Database_Migration_Runbook.md` before touching infrastructure.

---

### 3. Ship new features with a feature flag

In March 2024, a billing UI change shipped to 100% of users with no feature flag. It had a bug affecting 34% of users (annual plan holders). Rollback took 2h12m because billing code was bundled with other frontend changes.

Feature flags exist in LaunchDarkly. Any user-facing feature, especially anything touching billing, auth, or checkout, ships behind a flag with a canary rollout. See `Feature_Flag_Policy.md`.

---

### 4. Never commit credentials to version control

In March 2023, a .env file with live AWS keys was pushed to a public GitHub repo. Bots detected it in 47 seconds. $12,400 in crypto mining charges were run up in 4 minutes. The production Postgres connection string was also exposed.

Run `git-secrets --install` on your machine before writing any code. Credentials go in 1Password. Never in .env files that could touch a repo. See `Secrets_Management_Policy.md`.

---

### 5. Don't build core features on a single vendor with no fallback

In April 2022, we built our mapping feature directly on the Mapbox SDK. In November 2023, Mapbox raised prices 12x with 30 days notice. Every mapping session went from $0.04 to $0.51 — our feature margin went negative.

Because there was no abstraction layer, migrating away required a partial rewrite. 4 weeks of engineering time.

Any third-party integration for a core feature needs an abstraction layer. Read `Third_Party_Dependency_Policy.md`.

---

## Business Lessons

### 6. Get engineering to scope enterprise deals before they close

In May 2023, Sarah closed a $220K enterprise deal — custom SSO, data pipeline, white-label — scoped as "6 weeks" without engineering input. The deal took 7 months. Alex burned out and resigned. The customer churned anyway. Net outcome: -$130K on a $220K deal.

Any enterprise deal over $50K requires an engineering estimate before the contract is signed. See `Enterprise_Deal_Process.md`.

---

### 7. Hire on revenue, not expectations

In H1 2023, we hired 5 people in anticipation of a Series A. The Series A didn't close on timeline. We laid off 2 engineers in September 2023, 4–6 months after they had joined.

The hiring policy requires received funding or ARR that supports the hire at 18 months runway. "We expect to close the Series A" is not a trigger. See `Hiring_Policy.md`.

---

### Final Note

These lessons exist because we made mistakes. The people who made them are good people who were moving fast and doing their best. The policies aren't blame — they're the institutional equivalent of writing down what we learned so the next person doesn't have to learn it the same way.

If you see a situation that looks like one of these, say something. That's the whole point.
