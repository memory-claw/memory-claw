# DRAFT — AI Feature Proposal: Smart Search
## Internal spec — v0.2, work in progress

**Owner:** Alex Rivera  
**Date:** 2025-02-10  
**Status:** Draft — not reviewed by engineering or product yet  

---

### Overview

Proposal to add semantic search to the dashboard using OpenAI's embedding API. Users would be able to search their data using natural language rather than exact string matching.

---

### Proposed Implementation

Call OpenAI's `/v1/embeddings` endpoint directly from the backend on every search query. Store embeddings for user data in the existing Postgres database using pgvector.

Plan to import the OpenAI Python SDK and call it directly from the search service module.

---

### Cost Estimate

OpenAI embedding API: approximately $0.0001 per 1K tokens. At current usage, estimated $30–80/month. Seems manageable.

---

### Open Questions

- Should we cache embeddings or recompute on every search?
- Do we need a fallback if OpenAI is down?
- What happens to unit economics at 10x user growth?

---

### Next Steps

- [ ] Get Jake's sign-off on the feature
- [ ] Review with Marcus on implementation approach
- [ ] Ship behind a feature flag
