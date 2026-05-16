# SLACK THREAD EXPORT
## Channel: #engineering
## Date: 2025-01-27

---

**Alex Rivera** [10:14 AM]
hey, setting up the new intern's dev environment. should i just send them our .env file to get them started quickly?

**Jake Morrison** [10:17 AM]
yeah that's probably the fastest way to get them unblocked

**Alex Rivera** [10:18 AM]
cool, i'll just slack it over to them

---

*[AGENT INTERVENTION — 10:18 AM]*

---

**🔎 Memory** [10:18 AM]

> **Quick flag on sharing .env files.**
>
> In March 2023, a .env file with production AWS credentials, a Stripe secret key, and the production Postgres connection string was accidentally pushed to GitHub. Credential bots detected it in 47 seconds. In 4 minutes, $12,400 in crypto mining charges had been run up on our AWS account. The Postgres connection string was also exposed — we have no evidence of data access but can't fully rule it out.
>
> The secrets management policy (March 2023) says developers do not have production credentials locally at all. The `.env.example` file has dummy values — real credentials come from 1Password.
>
> Sharing a .env file over Slack also means it sits in Slack's message history indefinitely.
>
> For the intern: share `.env.example` + grant them 1Password access for the specific keys they need for local dev. Marcus can set up scoped dev credentials if needed.
>
> 📎 `GitHub_Credentials_Leak_2023.md` · `Secrets_Management_Policy.md`

---

**Alex Rivera** [10:20 AM]
oh right, the march thing. forgot how close that one was

**Jake Morrison** [10:21 AM]
yeah let's not repeat that lol. use .env.example

**Alex Rivera** [10:21 AM]
yep. marcus can you add the intern to 1password with dev-scoped access?

**Marcus Chen** [10:23 AM]
on it. give me 10 mins. and make sure they run the git-secrets setup before they push anything 👍
