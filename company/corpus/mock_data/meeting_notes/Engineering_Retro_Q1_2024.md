# MEETING NOTES
## Engineering Retrospective — Q1 2024

**Date:** 2024-01-22  
**Facilitator:** Priya Patel  
**Attendees:** Marcus Chen, Jake Morrison, Sarah Kim  
**Purpose:** Review the three major incidents from 2022–2023 and confirm process changes are embedded  

---

### Item 1 — API Outage August 2023

Marcus walked through the incident. The `/export` endpoint went to production without rate limiting. Six-hour outage. $94K ARR churned.

**Marcus:** "The middleware is done. It's two lines. I don't understand why we'd ever skip it now. I added it to the PR template."

**Jake:** "I approved that PR. I didn't know to look for it. The template change helps."

**Status:** Rate limiting middleware shipped. Pre-ship checklist added to PR template. No repeat incidents since August 2023. ✅

---

### Item 2 — AWS GPU Bill November 2022

Jake: "This one was me. I spun up the instances and assumed they'd get cleaned up. They didn't."

Marcus: "Billing alerts are set. Cost policy is in place. We have a Slack bot that pings #infra when any instance above t3.large has been running for 48 hours without a confirmed owner post."

**Status:** $0 surprise billing incidents since policy adoption in November 2022. ✅

---

### Item 3 — Helix Enterprise Deal 2023

This was the hardest conversation.

**Priya:** "We lost Alex. That's the real cost. The money is one thing but we lost a good engineer because we overloaded him on a deal that was scoped without him."

**Sarah:** "I understand why the process changed. I was optimising for closing. I didn't think through the delivery side."

**Jake:** "The new deal process has worked on the three enterprise deals we've done since. Vortex, Solaris, Northgate — all scoped with Marcus involved before signing. All delivered on time."

**Status:** Enterprise deal process in place. Technical review mandatory before contract. ✅

---

### General Observation

All three incidents had the same shape: someone moved fast, skipped a process step that felt like overhead, and the cost of skipping it was far higher than the step itself.

The rate limiting middleware takes 2 minutes. The billing alert takes 30 seconds to configure. The technical scope call takes 2 hours. 

Total time for all three process steps: under 3 hours.  
Total cost of skipping them: $94K ARR + $31K AWS bill + $130K net loss on Helix + one engineer resigned.

---

**Action:** Priya to include this retro summary in onboarding materials for all new engineers and sales hires. These three incidents are now part of how we explain what we've learned.
