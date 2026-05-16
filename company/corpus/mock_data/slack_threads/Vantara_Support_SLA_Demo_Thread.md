# SLACK THREAD EXPORT
## Channel: #support
## Date: 2025-02-14

---

**Sarah Kim** [9:31 AM]
hey marcus, Vantara opened a high priority ticket yesterday — their report export is failing. haven't had a chance to look at it yet, been a busy week

**Marcus Chen** [9:34 AM]
yeah i saw it. got a few things on my plate today. i'll get to it by end of week

**Sarah Kim** [9:35 AM]
ok cool. they're an enterprise account so just flagging

**Marcus Chen** [9:36 AM]
noted, will try to get to it tomorrow or wednesday

---

*[AGENT INTERVENTION — 9:36 AM]*

---

**🔎 Memory** [9:36 AM]

> **"End of week" on a high-priority ticket from an enterprise account is how we lost Orion.**
>
> In 2024, Orion Financial ($96,000 ARR) opened a high-priority ticket about a data export failure affecting their compliance reporting. First substantive response came after 76 hours. A second high-priority ticket went 84 hours. Neither triggered an escalation because we had no systems to notice.
>
> Orion's Head of Operations emailed Priya directly. By then, Orion had already started evaluating alternatives. They churned. **$96,000 ARR lost.**
>
> The enterprise support SLA policy (July 2024) sets 8-hour first response and 24-hour substantive update targets for high-priority enterprise tickets (>$30K ARR). Vantara qualifies. A report export failure is a P2.
>
> "End of wednesday" is outside SLA. If capacity is the issue, Sarah can reassign or escalate — but the clock is running.
>
> 📎 `Orion_Financial_Churn_Analysis_2024.md` · `Enterprise_Support_SLA_Policy.md`

---

**Marcus Chen** [9:38 AM]
ok yeah fair. i'll look at the vantara ticket this morning

**Sarah Kim** [9:39 AM]
thank you. i'll send them an acknowledgement now so they know it's in progress

**Marcus Chen** [10:14 AM]
found the issue — their export job was hitting the rate limit because they've grown significantly. bumping their limit now and pushing a fix. will be resolved within the hour

**Sarah Kim** [10:15 AM]
perfect. updating the ticket and letting them know 👍
