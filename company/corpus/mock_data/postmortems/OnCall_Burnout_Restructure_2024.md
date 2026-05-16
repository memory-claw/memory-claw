# POSTMORTEM
## On-Call Burnout — Marcus Chen Near-Resignation, January 2024

**Author:** Priya Patel  
**Date:** 2024-01-30  
**Type:** People / Process  
**Outcome:** Marcus disclosed he was close to resigning due to on-call load. On-call rotation restructured. Alex Rivera joined rotation. PagerDuty escalation policy added.  
**Risk:** Nearly lost founding infrastructure engineer.  

---

### What Happened

In a 1:1 on 2024-01-29, Marcus disclosed that he had been the sole on-call engineer for 14 months and was considering leaving. He had been paged an average of 2.3 times per week during that period, including 11 weekend incidents and 8 middle-of-the-night pages in the preceding 6 months.

Marcus said: "I don't mind being on-call. I mind being the only person who is ever on-call. I haven't had a weekend where I wasn't expecting to be paged in over a year."

Marcus is the only person with full production access, infrastructure context, and the institutional knowledge to debug most P0s. Losing him would have been an existential risk to the company's operational stability.

---

### Why It Got This Bad

There was no explicit decision to make Marcus the sole on-call engineer. It happened gradually:

- In 2022, Marcus set up PagerDuty and configured it to alert him. It was always intended to be temporary until others were trained.
- Jake and Alex both expressed willingness to join the rotation but training was always deprioritised in favour of feature work.
- Priya was aware Marcus was the sole on-call but did not treat it as an urgent problem until this 1:1.

---

### Changes Made

**Immediately:**
- Alex Rivera joined the on-call rotation with a 2-week shadow period (complete as of 2024-02-12)
- PagerDuty configured: primary alert to on-call engineer, escalation to Marcus after 10 minutes if no acknowledgement, escalation to Priya after 20 minutes
- On-call rotation: Marcus and Alex alternate weekly. No engineer is on-call for more than 2 consecutive weeks.

**Ongoing:**
- Runbooks written for all P0 and P1 incident types so any on-call engineer can handle them without needing Marcus's personal knowledge
- Quarterly rotation review to add additional engineers as team grows

---

### The Lesson

> "I built the system. I know how to fix it. I became the only person who knew how to fix it. That's not a superpower, it's a single point of failure — and it was also just really tiring."  
> — Marcus Chen

When one engineer holds all the operational knowledge, the company is one resignation away from a crisis. On-call rotation isn't just about fairness to the engineer — it's about resilience.

If anyone is the sole person who knows how to do something critical: that's a risk item, not a testament to their expertise.
