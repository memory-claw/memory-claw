# RETROSPECTIVE
## Microservices Premature Architecture — The 2022 Complexity Tax

**Author:** Priya Patel  
**Date:** 2022-12-01  
**Type:** Architecture retrospective  
**Outcome:** Rewrote microservices back into a monolith over 3 months. Velocity recovered. 4 months of engineering time lost to the original over-engineering.  

---

### What Happened

In January 2022, Marcus proposed and the team agreed to build the product as a microservices architecture from the start. The reasoning: "we'll need to scale eventually, better to build it right from the beginning."

We built:
- `auth-service` — handles authentication and sessions
- `user-service` — user management
- `analytics-service` — data processing
- `notification-service` — emails and alerts
- `gateway-service` — routes requests between services

At the time of this decision, we had:
- 12 paying customers
- 3 engineers
- No demonstrated need to scale any component independently

By June 2022, the consequences were clear:

**Development velocity collapsed.** A simple feature that touched user data and analytics (adding a "last active" timestamp to the dashboard) required coordinated changes across 3 services, 3 separate deployments, and 2 inter-service API contracts. What should have taken a day took a week.

**Local development was a nightmare.** Running the full stack locally required Docker Compose with 7 containers, a service mesh config, and inter-service mocking. New engineer onboarding jumped from 1 day to nearly 2 weeks.

**Debugging across services was painful.** A single user action generated logs across 3–4 services with no shared trace ID (we hadn't implemented distributed tracing). Debugging a bug that crossed service boundaries took hours.

**Operational overhead was disproportionate.** 3 engineers were spending approximately 20% of their time on infrastructure maintenance, service mesh config, and inter-service contract management that added zero user value.

In August 2022, Priya and Marcus made the decision to consolidate back into a monolith. The migration took 3 months.

---

### The Cost

- Time building the microservices architecture: 3 months
- Time migrating back to monolith: 3 months
- Total: 6 months of engineering time, approximately $90,000 in engineering cost
- Opportunity cost: features not shipped during this period

---

### Why It Happened

"We'll need to scale" is a prediction, not a fact. At 12 customers and 3 engineers, the scaling bottleneck was feature velocity — not infrastructure. We optimised for a problem we didn't have while creating a problem (complexity) that we very much had.

The decision felt responsible and forward-thinking. It was actually premature optimisation at the architectural level.

---

### What We Do Now

Priya has introduced a simple heuristic: **we don't solve scale problems before we have scale.**

The monolith will become a bottleneck at some point. When it does, we'll split out the specific component that's causing the bottleneck. Until then, the monolith is the right architecture because it lets 4 engineers ship fast.

"Build for where you are, not where you hope to be" now applies to architecture as much as it applies to hiring.

---

### Lesson

> "We built microservices for 12 customers. We needed features for 12 customers. We paid for the microservices with 6 months of engineering time and didn't get the features."  
> — Priya Patel

If someone proposes a complex architectural pattern for a scale problem we don't have yet: the answer is no. Revisit when the specific bottleneck appears.
