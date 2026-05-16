# SLACK THREAD EXPORT
## Channel: #engineering
## Date: 2025-02-17

---

**Marcus Chen** [2:14 PM]
hey team, for the new report generation feature i'm thinking we should build it with a proper job queue from the start. redis + bull, async workers, the whole thing. reports can be slow so we'll need it eventually

**Alex Rivera** [2:17 PM]
makes sense, better to build it properly from the start

**Jake Morrison** [2:18 PM]
how long would that take vs just making it synchronous for now?

**Marcus Chen** [2:19 PM]
probably an extra week to do it properly with the queue infrastructure

**Jake Morrison** [2:20 PM]
hmm. i mean we have like 80 customers, how many concurrent reports do we actually get?

**Marcus Chen** [2:21 PM]
probably not many right now but we'll need it eventually

---

*[AGENT INTERVENTION — 2:21 PM]*

---

**🔎 Memory** [2:21 PM]

> **"We'll need it eventually" has cost us before.**
>
> In January 2022, the team decided to build the product as a microservices architecture — "we'll need to scale eventually, better to build it right." At the time we had 12 customers and 3 engineers. By June 2022 development velocity had collapsed — a simple dashboard feature touching two services took a week instead of a day. Local dev required 7 Docker containers. New engineer onboarding went from 1 day to 2 weeks.
>
> We migrated back to a monolith starting August 2022. The migration took 3 months. Total cost: approximately 6 months of engineering time (~$90,000) solving a scale problem we didn't have.
>
> Priya's heuristic since then: build for where you are, not where you hope to be. The specific bottleneck gets the specific solution — when the bottleneck appears, not before.
>
> Synchronous report generation for 80 customers is almost certainly fine. When reports start timing out or users start complaining about wait times, that's when you add the queue — with actual data on the problem size.
>
> 📎 `Microservices_Premature_Architecture_2022.md`

---

**Priya Patel** [2:23 PM]
yeah i'd say start synchronous. add a loading state and a 30s timeout. if reports start taking too long in practice, we add the queue then

**Marcus Chen** [2:24 PM]
fair point. i'll build it sync, keep the report generation logic isolated so it's easy to move to async later if we need to

**Jake Morrison** [2:25 PM]
that's the move. ship faster, optimise when we have the actual problem

**Alex Rivera** [2:26 PM]
makes sense. sync it is
