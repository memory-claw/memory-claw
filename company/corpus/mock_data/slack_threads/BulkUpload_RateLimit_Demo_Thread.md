# SLACK THREAD EXPORT
## Channel: #engineering
## Date: 2025-01-21
## Note: PRIMARY DEMO THREAD — ARC 1

---

**Alex Rivera** [11:02 AM]
hey, just finished the /bulk-upload endpoint. ready to ship. PR is up

**Jake Morrison** [11:05 AM]
nice, been waiting on this. looks good from a product side, lgtm

**Alex Rivera** [11:07 AM]
cool. marcus you good to merge? it's pretty straightforward, just streams files into S3 then kicks off a processing job

**Marcus Chen** [11:09 AM]
looks clean. does it have rate limiting on it?

**Alex Rivera** [11:10 AM]
not yet, figured we could add it post-launch once we see how people use it. shouldn't be a big deal right?

**Jake Morrison** [11:11 AM]
yeah probably fine, it's behind auth so not like randos can hit it

**Alex Rivera** [11:12 AM]
exactly. let's just ship it and we can circle back on rate limiting next sprint

---

*[AGENT INTERVENTION — 11:12 AM]*

---

**🔎 Memory** [11:12 AM]

> **Heads up — we've been here before.**
>
> On 2023-08-14, Alex shipped the `/export` endpoint without rate limiting — also behind auth, also "low risk." A single customer's automated script hit it at 340 req/min. The Postgres connection pool exhausted in 22 minutes. The entire API went down for 6 hours.
>
> We lost Meridian Analytics, Stackform, and NovaBuild. **$94,000 ARR churned.**
>
> Marcus built `@rateLimit` middleware after that incident — it's literally 2 lines:
> ```python
> @rate_limit(requests_per_minute=60, per="org")
> ```
> It's in `middleware/rate_limit.py`. The pre-ship checklist also requires it for any endpoint that triggers background jobs.
>
> 📎 `API_Outage_Export_Endpoint_2023.md` · `Export_Endpoint_Outage_Postmortem_2023.md` · `Rate_Limiting_Middleware_Docs.md`

---

**Marcus Chen** [11:13 AM]
yeah what it said lol. add the decorator, takes 2 mins

**Alex Rivera** [11:14 AM]
oh damn I didn't realise that's what happened with the outage. adding it now

**Jake Morrison** [11:15 AM]
good catch. didn't connect those dots either

**Alex Rivera** [11:22 AM]
done, PR updated. @rate_limit(requests_per_minute=30, per="org") on the endpoint and added pagination cap. ready to merge

**Marcus Chen** [11:23 AM]
perfect. merging 👍
