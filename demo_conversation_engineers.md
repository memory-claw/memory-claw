# Engineer Demo — Staged Conversation

**Channel: `#engineering`**

---

**Arav** [2:14 PM]
@aidan hey, the new contractor starts tomorrow on the analytics repo. can you get them set up?

**Aidan** [2:15 PM]
yeah on it. should i just send them our .env to get them started? has all the API keys and the database connection string they'll need

**Arav** [2:16 PM]
yeah just send it over slack, fastest way to unblock them

---

*[MEMORYCLAW AUTO-TRIGGERS — matches "send them our .env"]*

---

**MemoryClaw** [2:16 PM]
> **Careful — sharing .env files has burned us before.**
>
> On 2023-03-17, a `.env` with live AWS keys, Stripe secret, and the production Postgres connection string was pushed to a public repo. Automated bots detected exposed credentials within **47 seconds**. Four unauthorized EC2 instances spun up mining crypto before Marcus could kill them.
>
> Net cost: **$3,200**. The production database connection string was exposed for 4 minutes — no confirmed data access, but it can't be ruled out.
>
> **What to do instead:**
> - Use 1Password shared vaults for credentials (per `Secrets_Management_Policy.md`)
> - Generate scoped, time-limited tokens for contractor access
> - Never share files containing production secrets via Slack, email, or repo
>
> :page_facing_up: `GitHub_Credentials_Leak_2023.md` · `Secrets_Management_Policy.md`

---

**Aidan** [2:17 PM]
oh wait, legit? that's wild. so what's the right move here?

**Arav** [2:17 PM]
@MemoryClaw what's our current policy for giving new contractors API access?

---

*[MEMORYCLAW RESPONDS TO DIRECT TAG]*

---

**MemoryClaw** [2:18 PM]
> Per `Secrets_Management_Policy.md`:
>
> 1. **No local .env files with production credentials** — developers use 1Password CLI (`op run`) to inject secrets at runtime
> 2. **Contractors get scoped credentials** — time-limited, staging-only, generated through the admin panel
> 3. **Pre-commit hooks** (`git-secrets`) block any push containing key patterns like `AKIA*`, `sk_live_*`, or connection strings
> 4. **No secrets in Slack/email** — if you've already sent one, rotate immediately
>
> For the new contractor: generate a staging-only API key from `/admin/keys` with a 30-day TTL. Takes ~2 minutes.
>
> :page_facing_up: `Secrets_Management_Policy.md`

---

**Aidan** [2:19 PM]
got it, i'll just gen a scoped key from the admin panel. way better than what i was about to do lol

**Arav** [2:20 PM]
yeah let's not be the team that leaks prod creds to a contractor on day one :skull:

**Aidan** [2:21 PM]
done — staging key created, 30 day expiry, sent them the onboarding doc link instead. thanks robot :robot_face:

---

## Demo Beats

| Beat | What it shows |
|------|---------------|
| Natural convo between Arav + Aidan | Bot watches passively, not always talking |
| Auto-trigger on ".env" pattern | Proactive institutional memory, no tag needed |
| Specific numbers ($3,200, 47 seconds) | Cites real incidents, not generic advice |
| @MemoryClaw direct question | Also works as on-demand lookup tool |
| Policy + actionable steps | Doesn't just warn — tells you what to do |
| Engineers adopt it naturally | Thread resolves positively, no annoyance |
