# Memory-Claw Mission Control Dashboard

**Date:** 2026-05-16
**Status:** Approved
**Stack:** FastAPI + WebSockets (backend, same process) | React + Vite + Tremor + Tailwind (frontend)

## Purpose

Real-time dashboard for hackathon demo. Primary audience: judges watching a live presentation. Must tell the story of the RAG pipeline at a glance, feel alive, and look distinctive (mission control aesthetic).

## Aesthetic Direction

**Theme:** Mission Control / NASA ground station

- Background: dark slate (#0f1419) with subtle grid overlay
- Accent: electric cyan (#00d4ff) for active/success states
- Warning: amber (#ffb800)
- Error: red (#ff4444)
- Typography: monospace for telemetry data, sans-serif for labels
- Cards: faint border glow matching status color
- Signature: animated pipeline flow with glowing data packets traversing nodes

**Idle state:** Pipeline nodes have subtle pulse animation. Background grid drifts slowly. Dashboard feels alive even with no events.

**Burst state:** Multiple data packets cascade through pipeline. Events slide into feed rapidly with glow effects.

## Layout

Single page, no routing.

```
┌─────────────────────────────────────────────────────────────┐
│  MEMORY-CLAW MISSION CONTROL                    [ONLINE]    │
├─────────────────────────────────────────────────────────────┤
│ ● Slack ● Chroma ● Ollama ● Listener    Last event: 3s ago │
├─────────────────────────────────────────────────────────────┤
│  ┌─[INBOX]──→──[EMBED]──→──[CHROMA]──→──[SEARCH]──→──[SLACK]─┐ │
│  └────────────── animated pipeline flow ──────────────────────┘ │
├───────────────────────────────┬─────────────────────────────┤
│  LIVE TELEMETRY               │  RELEVANCE DISTRIBUTION     │
│  (curated event feed)         │  (area chart with threshold │
│                               │   line at 0.60)             │
├───────────────────────────────┼─────────────────────────────┤
│  RECENT QUERIES               │  KNOWLEDGE BASE STATUS      │
│  (table: query, score,        │  (documents, chunks, model, │
│   source, time)               │   collection, last ingest)  │
└───────────────────────────────┴─────────────────────────────┘
```

## Panels

### 1. System Status Strip

Top bar showing service health at a glance.

- **Indicators:** Slack connected, Chroma reachable, Ollama reachable, Listener running
- **Last event:** relative time since last audit event, turns amber if >60s stale
- **Visual:** green dot = healthy, amber = degraded, red = down. Listener dot pulses when actively polling.
- **Demo insurance:** if something breaks during demo, point here and explain.

### 2. Animated Pipeline Flow

SVG-based visualization of the data flow: INBOX → EMBED → CHROMA → SEARCH → SLACK.

- Each node is a rounded box with icon
- When event arrives, corresponding node pulses and a glowing dot ("data packet") animates along the path to next node
- Bursts create multiple packets cascading through the pipeline
- Idle: nodes have subtle breathing animation

### 3. Live Telemetry

Curated event feed (not raw logs).

- Human-readable labels:
  - "Draft processed" (type: draft_read)
  - "Memory search completed" (type: search)
  - "Slack reply sent" (type: slack_post)
  - "Below threshold — skipped" (type: search, no results above threshold)
  - "Error: ..." (type: error)
- Color-coded by category (cyan=search, green=slack, blue=ingest, red=error, amber=skipped)
- New events slide in from top with brief glow
- Each row expandable → raw JSON payload (collapsed by default)
- Max visible: ~15 most recent, scrollable

### 4. Relevance Distribution

Tremor AreaChart showing cosine similarity scores over time.

- X-axis: time (recent queries)
- Y-axis: relevance score (0.0 - 1.0)
- Threshold line at 0.60 glows amber
- Points above threshold: cyan fill
- Points below threshold: dim/grey
- Updates in real-time as search events arrive

### 5. Recent Queries

Tremor Table showing last N search operations.

- Columns: Query (truncated), Top Score, Source Matched, Time
- Scores color-coded: ≥0.80 bright cyan, 0.60-0.79 standard, <0.60 dim/amber
- Clickable rows could expand to show all hits (stretch goal)

### 6. Knowledge Base Status

Static-ish panel showing what the system "knows."

- Documents indexed (count)
- Total chunks
- Embedding model name (e.g., qwen3-embedding:8b)
- Collection name (e.g., org_memory)
- Last ingest timestamp (relative)

Refreshed on page load + after ingest events.

## Technical Architecture

### File Structure

```
institutional_memory/
  dashboard/
    __init__.py
    server.py         # FastAPI app, routes, WebSocket endpoint
    broadcast.py      # WebSocket connection manager + broadcast
    health.py         # Health check logic (ping Slack/Chroma/Ollama)
    static/           # Built Vite output (production)

dashboard-ui/         # React frontend (dev)
  src/
    App.tsx
    components/
      StatusStrip.tsx
      PipelineFlow.tsx
      LiveFeed.tsx
      RelevanceChart.tsx
      RecentQueries.tsx
      KnowledgeBase.tsx
    hooks/
      useWebSocket.ts
    lib/
      eventLabels.ts   # Maps audit event types → human-readable labels
    styles/
      theme.css        # CSS variables, grid background, glow effects
  tailwind.config.ts
  vite.config.ts
```

### Backend (FastAPI)

**WebSocket endpoint:** `/ws/events`
- Streams audit events to all connected clients in real-time
- On connect: sends last 50 events as backfill
- Reconnection-friendly (client re-subscribes, gets backfill)

**REST endpoints:**
- `GET /api/stats` — ChromaDB collection stats (doc count, chunk count, collection name, embedding model)
- `GET /api/recent-queries` — last N search events from audit log
- `GET /api/health` — service health (Slack token valid, Chroma ping, Ollama ping, listener status)

**Integration with existing code:**
- Hook into `audit.log_event()` — after writing to JSONL, also call `broadcast.send(event)` to push to WebSocket clients
- Import config directly (same process)
- Read `audit_log.jsonl` for historical data on startup/backfill

### Frontend (React + Vite)

**Dependencies:**
- React 19
- Vite
- Tailwind CSS v4
- @tremor/react (charts, tables, metric cards)
- Motion (framer-motion successor) for pipeline animations

**WebSocket hook:**
- Auto-reconnect with exponential backoff
- Dispatches events to relevant components via context/state
- Connection status feeds into StatusStrip

**Build & Serve:**
- Dev: `npm run dev` (Vite dev server, proxies API to FastAPI)
- Prod: `npm run build` → output to `institutional_memory/dashboard/static/`
- FastAPI serves static files from that directory + mounts API routes

### Data Flow

```
audit.log_event() called
  → writes to audit_log.jsonl (existing)
  → broadcasts to WebSocket clients (new)
      → frontend receives event
          → LiveFeed: adds to feed list
          → PipelineFlow: triggers node animation
          → RelevanceChart: adds data point (if search event)
          → RecentQueries: prepends row (if search event)
          → StatusStrip: updates "last event" time
```

## Running

```bash
# Dev mode (two terminals)
uv run python -m institutional_memory.dashboard.server   # FastAPI on :8000
cd dashboard-ui && npm run dev                           # Vite on :5173

# Production
cd dashboard-ui && npm run build   # outputs to institutional_memory/dashboard/static/
uv run python -m institutional_memory.dashboard.server   # serves everything on :8000
```

## Non-Goals

- User authentication (hackathon demo, no auth needed)
- Persistent storage for dashboard state (reads from existing audit log)
- Mobile responsiveness (demo is on a laptop/projector)
- Dark/light toggle (dark only)
