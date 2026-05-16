# SLACK THREAD EXPORT
## Channel: #engineering
## Date: 2025-02-12

---

**Alex Rivera** [2:31 PM]
hey team, for the new geolocation feature i'm thinking of using the Google Maps API. easiest integration by far

**Jake Morrison** [2:34 PM]
yeah google maps is the obvious choice. go for it

**Alex Rivera** [2:35 PM]
cool. i'll build the whole location layer on top of it, should be fast

**Marcus Chen** [2:37 PM]
how tightly coupled are you planning to make it? like is the google maps sdk going to be called directly from components?

**Alex Rivera** [2:38 PM]
yeah probably just import it where i need it, it's cleaner

---

*[AGENT INTERVENTION — 2:38 PM]*

---

**🔎 Memory** [2:38 PM]

> **Heads up — tight vendor coupling has hurt us before.**
>
> In April 2022, Marcus built the mapping feature directly on the Mapbox SDK — same approach, imported where needed. In November 2023, Mapbox raised prices 12x with 30 days notice. Every mapping session went from costing $0.04 to $0.51. The feature margin went negative overnight.
>
> Because the Mapbox SDK was called directly throughout the codebase, swapping vendors required a partial rewrite. Marcus and Alex spent 4 weeks on an emergency migration.
>
> The third-party dependency policy (Nov 2023) now requires: (1) an abstraction layer between our code and any vendor SDK for core features, and (2) Marcus to model what happens if the vendor raises prices 5x before integration starts.
>
> Google Maps pricing has changed significantly before — worth 10 minutes to put a service wrapper around it now rather than 4 weeks later.
>
> 📎 `Mapbox_Pricing_Crisis_2023.md` · `Third_Party_Dependency_Policy.md`

---

**Marcus Chen** [2:40 PM]
yeah exactly what it said. just wrap it in a LocationService class. costs you maybe an hour now

**Alex Rivera** [2:41 PM]
that's fair. i'll build a LocationService abstraction first, then the google maps adapter behind it

**Jake Morrison** [2:42 PM]
good call. also worth checking google maps pricing tiers before we scale this up

**Marcus Chen** [2:43 PM]
i'll send you the cost model template. fill it out before we ship 👍
