# SLACK THREAD EXPORT
## Channel: #engineering
## Date: 2025-02-04

---

**Jake Morrison** [3:15 PM]
hey marcus, i want to run some evals on the new embedding model. can i spin up a couple of GPU instances on AWS for like a few days?

**Marcus Chen** [3:18 PM]
yeah should be fine. which instance type?

**Jake Morrison** [3:19 PM]
was thinking p3.8xlarge x2, just for the weekend. i'll tear them down monday

**Marcus Chen** [3:21 PM]
cool go for it

**Jake Morrison** [3:22 PM]
sweet, spinning them up now

---

*[AGENT INTERVENTION — 3:22 PM]*

---

**🔎 Memory** [3:22 PM]

> **Quick flag — p3.8xlarge has come up before.**
>
> In October 2022, Jake spun up 3x p3.8xlarge for an ML experiment over a weekend. The experiment got deprioritised on Monday. The instances ran for 18 days. Nobody noticed. The AWS bill that month was **$34,400 — $31,200 above forecast.**
>
> At the time we had 4.5 months of runway.
>
> The cloud cost policy (introduced after this) requires:
> - A message in `#infra` before spinning up any instance > `t3.large`
> - Auto-shutdown configured (max 72 hours)
> - Your name tagged as owner with `auto-delete: true`
>
> Not flagging this to block it — just so the Monday teardown actually happens this time.
>
> 📎 `AWS_Bill_GPU_Instances_2022.md` · `Cloud_Cost_Policy.md`

---

**Jake Morrison** [3:23 PM]
oh god I completely forgot that was me lol

**Marcus Chen** [3:24 PM]
haha. set auto-shutdown to sunday night, i'll add the #infra post

**Jake Morrison** [3:25 PM]
yeah doing it now. tagging with auto-delete: true and setting a monday 9am termination alarm

**Marcus Chen** [3:26 PM]
perfect. carry on 👍
