# RETROSPECTIVE
## HackerNews Launch — Infrastructure Not Ready, February 2023

**Author:** Jake Morrison  
**Date:** 2023-02-28  
**Outcome:** Product featured on HackerNews front page. Site down within 22 minutes. Traffic spike: 40x normal. No load testing had been done. Missed acquisition opportunity.  

---

### What Happened

On 2023-02-14, a user posted the product to HackerNews. The post reached the front page within 2 hours, peaking at position 4. This was the largest organic marketing moment in the company's history to that point.

Within 22 minutes of hitting the front page, the application was returning 503s for the majority of requests. The single EC2 instance running the app was overwhelmed. There was no auto-scaling configured. There was no CDN for static assets. The database connection pool was exhausted.

The site was effectively down for 3 hours during peak HackerNews traffic.

By the time Marcus had the application stable, the HN post had fallen off the front page. Total sign-ups captured during the window: 340. Estimated potential based on post position and engagement: 1,800–2,400.

We captured approximately 15–20% of the available sign-ups from the most visible product moment we'd had.

---

### Why We Weren't Ready

There was no formal "are we production-ready for a traffic spike" checklist. The infrastructure was built for steady-state usage, not for burst events. Nobody had asked the question "what happens if we suddenly get 40x traffic."

The HackerNews submission was by an organic user — we didn't plan or anticipate it. But "a user might post us to HN or Reddit at any time" is a foreseeable event that we had not prepared for.

---

### What Changed

Marcus implemented auto-scaling and a CDN within the 2 weeks following the incident. Load testing was added to the pre-release checklist for any infrastructure changes.

Jake introduced a "launch readiness" checklist that asks: "if we 10x traffic right now, does the site stay up?" It is reviewed before any marketing campaign or public launch.

---

### Estimated Cost

Sign-ups lost (estimated 1,400–2,000 at $0 CAC, organic): significant but unquantifiable  
Brand impression: negative for users who hit the 503 page (a product's first impression is hard to recover from)

---

### The Lesson

> "We got on HackerNews and our first impression for thousands of developers was a 503 page. We had one shot at that moment and we showed people a broken product."  
> — Jake Morrison

Your product will be discovered at an unpredictable moment. When it is, it needs to work. Load testing is not just about SLAs — it's about not wasting the moments that cost nothing in CAC but everything in first impressions.
