# Collective Memory Agent — Mock Dataset

Complete interconnected mock data for the hackathon demo.  
Three corporate memory arcs, five named employees, zero filler.

---

## Dataset Structure

```
mock_data/
├── contracts/
│   ├── NHS_SouthWest_2022_FAILED.md        # ARC 1 — The failure
│   └── NHS_Midlands_2024_WON.md            # ARC 1 — The win (after fix)
├── postmortems/
│   ├── NHS_SouthWest_2022_Postmortem.md    # ARC 1 — Why we lost
│   ├── DataVault_Security_Breach_2021_Postmortem.md  # ARC 2 — Vendor breach
│   └── FinCo_Margin_Collapse_2023_Postmortem.md      # ARC 3 — Margin loss
├── legal_memos/
│   └── Sarah_Chen_Liability_Clause_Revision_2024.md  # ARC 1 — The fix
├── policy_docs/
│   ├── Vendor_Security_Gate_Policy.md      # ARC 2 — The fix
│   ├── Bid_Pricing_SignOff_Policy.md       # ARC 3 — The fix
│   ├── Leeds_Office_Relocation_2024.md     # NOISE — should not trigger
│   └── IT_Password_Policy_v3.md           # NOISE — should not trigger
├── slack_threads/
│   ├── NHS_NorthEast_Liability_Demo_Thread.md  # ARC 1 — MAIN DEMO THREAD
│   ├── CloudNest_Vendor_Onboarding_Thread.md   # ARC 2 — Demo thread
│   ├── Meridian_Pricing_Thread.md              # ARC 3 — Demo thread
│   └── Lunch_Plans_Noise_Thread.md             # NOISE — should not trigger
├── meeting_notes/
│   └── Q1_2024_Legal_Review_Meeting_Notes.md
├── Team_Directory.md
└── ingest_mock_data.py                     # Run this first
```

---

## The Three Arcs

### ARC 1 — NHS Liability Clause
The core demo arc. The one to use on stage.

| Doc | Year | Outcome |
|-----|------|---------|
| NHS_SouthWest_2022_FAILED | 2022 | Loss — £4.2M contract rejected |
| NHS_SouthWest_2022_Postmortem | 2022 | Root cause: 10% liability cap |
| Sarah_Chen_Liability_Clause_Revision_2024 | 2024 | Fix: Clause 7.3b (100% cap) |
| NHS_Midlands_2024_WON | 2024 | Win — £3.8M, clause 7.3b cited |

**Trigger conversation:** Someone in Slack says "let's use the standard 10% liability cap" on an NHS bid.  
**Agent surfaces:** 2022 failure + Sarah's fix + 2024 win.  
**Outcome changes:** Team pulls in Sarah before submitting.

---

### ARC 2 — Vendor Security Fast-Track
| Doc | Year | Outcome |
|-----|------|---------|
| DataVault_Security_Breach_2021_Postmortem | 2021 | Breach — ICO fine £180K |
| Vendor_Security_Gate_Policy | 2021 | Fix: 5-point security gate |

**Trigger:** Someone suggests onboarding a vendor without completing security checks.  
**Agent surfaces:** DataVault breach + mandatory policy.

---

### ARC 3 — Pricing Without Delivery Review
| Doc | Year | Outcome |
|-----|------|---------|
| FinCo_Margin_Collapse_2023_Postmortem | 2023 | -£640,000 delivered at a loss |
| Bid_Pricing_SignOff_Policy | 2023 | Fix: Delivery sign-off mandatory |

**Trigger:** Someone suggests submitting a bid price without looping in Delivery.  
**Agent surfaces:** FinCo margin collapse + mandatory pricing sign-off policy.

---

## Named Employees (for agent grounding)

| Name | Role | Key Arc |
|------|------|---------|
| Sarah Chen | Legal Counsel | ARC 1 — wrote the fix clause |
| Tom Walker | Sales Director | All arcs — the bid submitter |
| Emma Patel | Procurement | ARC 2 — approved vendor without checks |
| James Liu | Delivery Lead | ARC 3 — introduced pricing policy |
| Rachel Moore | Compliance | All arcs — authors every postmortem |

---

## How to Ingest

```bash
# Install dependencies
pip install chromadb

# Run ingestion (pull Ollama nomic-embed-text first)
ollama pull nomic-embed-text
python mock_data/ingest_mock_data.py
```

---

## Demo Script (ARC 1)

Use the `NHS_NorthEast_Liability_Demo_Thread.md` as your script.  
Two humans discuss accepting a 10% liability cap on an NHS bid.  
Agent intervenes unprompted at message 9.  
Decision changes at message 10.

That's the product.
