# Mission Control Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real-time mission control dashboard that visualizes the RAG pipeline, streams audit events over WebSocket, and displays system health — all in a distinctive dark theme for hackathon demo.

**Architecture:** FastAPI backend adds WebSocket broadcast + REST endpoints to the existing `institutional_memory` package. React frontend (Vite + Tremor + Tailwind) connects via WebSocket for live events and REST for stats/health. Single process serves both API and built static files.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, websockets | React 19, Vite, Tailwind CSS v4, @tremor/react, motion (framer-motion)

---

## Task 0: Project Scaffolding & Dependencies

**Goal:** Set up both backend (FastAPI) and frontend (React/Vite) project structures with all dependencies installed and a hello-world endpoint working end-to-end.

**Files:**
- Create: `institutional_memory/dashboard/__init__.py`
- Create: `institutional_memory/dashboard/server.py`
- Create: `dashboard-ui/package.json`
- Create: `dashboard-ui/vite.config.ts`
- Create: `dashboard-ui/tailwind.config.ts`
- Create: `dashboard-ui/tsconfig.json`
- Create: `dashboard-ui/index.html`
- Create: `dashboard-ui/src/main.tsx`
- Create: `dashboard-ui/src/App.tsx`
- Create: `dashboard-ui/src/styles/theme.css`
- Modify: `pyproject.toml` (add fastapi, uvicorn dependencies)

**Acceptance Criteria:**
- [ ] `uv run python -m institutional_memory.dashboard.server` starts on port 8000
- [ ] `GET /api/health` returns `{"status": "ok"}`
- [ ] `cd dashboard-ui && npm run dev` starts Vite on port 5173
- [ ] Vite proxies `/api/*` and `/ws/*` to FastAPI on 8000
- [ ] App renders "Mission Control" placeholder text in dark theme

**Verify:** `curl http://localhost:8000/api/health` → `{"status":"ok"}`

**Steps:**

- [ ] **Step 1: Add Python dependencies**

Add to `pyproject.toml` dependencies:
```toml
"fastapi>=0.115.0",
"uvicorn[standard]>=0.34.0",
```

Run: `uv sync`

- [ ] **Step 2: Create FastAPI server skeleton**

Create `institutional_memory/dashboard/__init__.py`:
```python
```

Create `institutional_memory/dashboard/server.py`:
```python
from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="Memory-Claw Mission Control")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Scaffold React frontend**

Run from project root:
```bash
npm create vite@latest dashboard-ui -- --template react-ts
cd dashboard-ui
npm install
npm install tailwindcss @tailwindcss/vite @tremor/react motion
```

- [ ] **Step 4: Configure Vite proxy**

Create `dashboard-ui/vite.config.ts`:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": {
        target: "http://localhost:8000",
        ws: true,
      },
    },
  },
  build: {
    outDir: "../institutional_memory/dashboard/static",
    emptyOutDir: true,
  },
});
```

- [ ] **Step 5: Set up Tailwind with mission control theme**

Create `dashboard-ui/src/styles/theme.css`:
```css
@import "tailwindcss";

:root {
  --mc-bg: #0f1419;
  --mc-surface: #1a2332;
  --mc-border: #2a3a4a;
  --mc-cyan: #00d4ff;
  --mc-amber: #ffb800;
  --mc-red: #ff4444;
  --mc-green: #00ff88;
  --mc-text: #e0e8f0;
  --mc-text-dim: #6b7b8b;
  --mc-glow: 0 0 10px rgba(0, 212, 255, 0.3);
}

body {
  background-color: var(--mc-bg);
  color: var(--mc-text);
  font-family: "JetBrains Mono", "Fira Code", monospace;
  background-image:
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}
```

- [ ] **Step 6: Create App placeholder**

Create `dashboard-ui/src/App.tsx`:
```tsx
export default function App() {
  return (
    <div className="min-h-screen p-6">
      <h1 className="text-2xl font-bold tracking-wider uppercase"
          style={{ color: "var(--mc-cyan)" }}>
        Memory-Claw Mission Control
      </h1>
    </div>
  );
}
```

Update `dashboard-ui/src/main.tsx`:
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/theme.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 7: Verify end-to-end**

Terminal 1: `uv run python -m institutional_memory.dashboard.server`
Terminal 2: `cd dashboard-ui && npm run dev`

Check: `curl http://localhost:8000/api/health` → `{"status":"ok"}`
Check: browser at http://localhost:5173 shows "Memory-Claw Mission Control" on dark background with grid

- [ ] **Step 8: Commit**

```bash
git add institutional_memory/dashboard/ dashboard-ui/ pyproject.toml uv.lock
git commit -m "feat(dashboard): scaffold FastAPI backend + React frontend"
```

---

## Task 1: WebSocket Broadcast Infrastructure

**Goal:** Create the WebSocket connection manager and hook it into `audit.log_event()` so events broadcast to all connected dashboard clients in real-time.

**Files:**
- Create: `institutional_memory/dashboard/broadcast.py`
- Modify: `institutional_memory/dashboard/server.py` (add WS endpoint)
- Modify: `institutional_memory/audit.py` (add broadcast hook)
- Create: `tests/test_broadcast.py`

**Acceptance Criteria:**
- [ ] WebSocket clients receive events pushed by `audit.log_event()`
- [ ] On connect, client receives last 50 historical events as backfill
- [ ] Multiple simultaneous clients all receive broadcasts
- [ ] Disconnected clients are cleaned up without errors

**Verify:** `uv run pytest tests/test_broadcast.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write broadcast manager tests**

Create `tests/test_broadcast.py`:
```python
import asyncio
import json
import pytest
from institutional_memory.dashboard.broadcast import ConnectionManager


@pytest.fixture
def manager():
    return ConnectionManager()


@pytest.mark.asyncio
async def test_backfill_on_connect(manager):
    manager._history.append({"type": "test", "ts": "2026-01-01T00:00:00Z"})
    backfill = manager.get_backfill()
    assert len(backfill) == 1
    assert backfill[0]["type"] == "test"


@pytest.mark.asyncio
async def test_history_capped_at_50(manager):
    for i in range(60):
        manager.record_event({"type": "test", "index": i})
    assert len(manager._history) == 50
    assert manager._history[0]["index"] == 10


def test_record_event(manager):
    manager.record_event({"type": "search", "query": "hello"})
    assert len(manager._history) == 1
```

- [ ] **Step 2: Implement ConnectionManager**

Create `institutional_memory/dashboard/broadcast.py`:
```python
from __future__ import annotations

import json
from collections import deque
from typing import Any

from fastapi import WebSocket

MAX_HISTORY = 50


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._history: deque[dict[str, Any]] = deque(maxlen=MAX_HISTORY)

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self._connections.remove(ws)

    def get_backfill(self) -> list[dict[str, Any]]:
        return list(self._history)

    def record_event(self, event: dict[str, Any]):
        self._history.append(event)

    async def broadcast(self, event: dict[str, Any]):
        self.record_event(event)
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)


manager = ConnectionManager()
```

- [ ] **Step 3: Add WebSocket endpoint to server**

Add to `institutional_memory/dashboard/server.py`:
```python
from fastapi import WebSocket, WebSocketDisconnect
from institutional_memory.dashboard.broadcast import manager


@app.websocket("/ws/events")
async def websocket_events(ws: WebSocket):
    await manager.connect(ws)
    try:
        backfill = manager.get_backfill()
        await ws.send_json({"type": "backfill", "events": backfill})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
```

- [ ] **Step 4: Hook audit.log_event() into broadcast**

Modify `institutional_memory/audit.py`:
```python
"""Append structured events to audit_log.jsonl."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any

from institutional_memory.config import AUDIT_LOG

_broadcast_fn: Any = None


def set_broadcast_fn(fn):
    global _broadcast_fn
    _broadcast_fn = fn


def log_event(event_type: str, **fields: Any) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "driver": fields.pop("driver", os.getenv("IMEM_DRIVER", "openclaw")),
        **fields,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if _broadcast_fn is not None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_broadcast_fn(entry))
        except RuntimeError:
            pass
```

- [ ] **Step 5: Wire broadcast on server startup**

Add to `institutional_memory/dashboard/server.py` startup:
```python
from institutional_memory.audit import set_broadcast_fn
from institutional_memory.dashboard.broadcast import manager


@app.on_event("startup")
async def startup():
    set_broadcast_fn(manager.broadcast)
    _load_history()


def _load_history():
    from institutional_memory.config import AUDIT_LOG
    if not AUDIT_LOG.exists():
        return
    lines = AUDIT_LOG.read_text(encoding="utf-8").strip().splitlines()
    for line in lines[-50:]:
        try:
            manager.record_event(json.loads(line))
        except json.JSONDecodeError:
            pass
```

- [ ] **Step 6: Run tests, verify, commit**

Run: `uv run pytest tests/test_broadcast.py -v`
Expected: all tests pass

```bash
git add institutional_memory/audit.py institutional_memory/dashboard/broadcast.py institutional_memory/dashboard/server.py tests/test_broadcast.py
git commit -m "feat(dashboard): websocket broadcast + audit hook"
```

---

## Task 2: REST API Endpoints (Stats, Health, Recent Queries)

**Goal:** Implement the three REST endpoints that provide snapshot data to the dashboard: system health, ChromaDB stats, and recent search queries.

**Files:**
- Create: `institutional_memory/dashboard/health.py`
- Modify: `institutional_memory/dashboard/server.py` (add routes)
- Create: `tests/test_dashboard_api.py`

**Acceptance Criteria:**
- [ ] `GET /api/health` returns status of Slack, Chroma, Ollama, last event time
- [ ] `GET /api/stats` returns document count, chunk count, collection name, embedding model
- [ ] `GET /api/recent-queries` returns last 20 search events with query, score, source, timestamp

**Verify:** `uv run pytest tests/test_dashboard_api.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write API tests**

Create `tests/test_dashboard_api.py`:
```python
import json
import pytest
from fastapi.testclient import TestClient
from institutional_memory.dashboard.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "slack" in data
    assert "chroma" in data
    assert "ollama" in data
    assert "last_event" in data


def test_stats_endpoint(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "documents" in data
    assert "chunks" in data
    assert "collection" in data
    assert "embedding_model" in data


def test_recent_queries_endpoint(client):
    resp = client.get("/api/recent-queries")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
```

- [ ] **Step 2: Implement health checks**

Create `institutional_memory/dashboard/health.py`:
```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from institutional_memory.config import (
    AUDIT_LOG,
    CHROMA_PATH,
    OLLAMA_BASE_URL,
    SLACK_BOT_TOKEN,
)


async def check_ollama() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return {"status": "online" if resp.status_code == 200 else "error"}
    except Exception:
        return {"status": "offline"}


async def check_chroma() -> dict[str, Any]:
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        client.heartbeat()
        return {"status": "online"}
    except Exception:
        return {"status": "offline"}


async def check_slack() -> dict[str, Any]:
    if not SLACK_BOT_TOKEN:
        return {"status": "not_configured"}
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.post(
                "https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            )
            data = resp.json()
            return {"status": "connected" if data.get("ok") else "error"}
    except Exception:
        return {"status": "offline"}


def get_last_event_time() -> str | None:
    if not AUDIT_LOG.exists():
        return None
    try:
        lines = AUDIT_LOG.read_text(encoding="utf-8").strip().splitlines()
        if lines:
            import json
            last = json.loads(lines[-1])
            return last.get("ts")
    except Exception:
        pass
    return None
```

- [ ] **Step 3: Add REST routes to server**

Add to `institutional_memory/dashboard/server.py`:
```python
from institutional_memory.dashboard.health import (
    check_chroma,
    check_ollama,
    check_slack,
    get_last_event_time,
)
from institutional_memory.config import (
    AUDIT_LOG,
    CHROMA_COLLECTION,
    EMBEDDING_MODEL,
)


@app.get("/api/health")
async def health():
    return {
        "slack": await check_slack(),
        "chroma": await check_chroma(),
        "ollama": await check_ollama(),
        "last_event": get_last_event_time(),
    }


@app.get("/api/stats")
async def stats():
    try:
        from institutional_memory.ingest import get_chroma_collection
        collection = get_chroma_collection()
        count = collection.count()
    except Exception:
        count = 0
    return {
        "documents": count,
        "chunks": count,
        "collection": CHROMA_COLLECTION,
        "embedding_model": EMBEDDING_MODEL,
        "last_ingest": _get_last_ingest_time(),
    }


@app.get("/api/recent-queries")
async def recent_queries():
    if not AUDIT_LOG.exists():
        return []
    lines = AUDIT_LOG.read_text(encoding="utf-8").strip().splitlines()
    searches = []
    for line in reversed(lines):
        try:
            event = json.loads(line)
            if event.get("type") == "memory_searched":
                searches.append({
                    "query": event.get("query", ""),
                    "top_score": event.get("top_score"),
                    "source": event.get("source"),
                    "ts": event.get("ts"),
                    "count": event.get("count", 0),
                })
                if len(searches) >= 20:
                    break
        except json.JSONDecodeError:
            continue
    return searches


def _get_last_ingest_time() -> str | None:
    if not AUDIT_LOG.exists():
        return None
    lines = AUDIT_LOG.read_text(encoding="utf-8").strip().splitlines()
    for line in reversed(lines):
        try:
            event = json.loads(line)
            if event.get("type") in ("ingested", "ingest"):
                return event.get("ts")
        except json.JSONDecodeError:
            continue
    return None
```

- [ ] **Step 4: Add httpx dependency**

Add to `pyproject.toml`:
```toml
"httpx>=0.28.0",
```

Run: `uv sync`

- [ ] **Step 5: Run tests, commit**

Run: `uv run pytest tests/test_dashboard_api.py -v`
Expected: all pass

```bash
git add institutional_memory/dashboard/ tests/test_dashboard_api.py pyproject.toml uv.lock
git commit -m "feat(dashboard): REST endpoints for health, stats, recent queries"
```

---

## Task 3: Frontend WebSocket Hook & Event Context

**Goal:** Create a React context + hook that manages the WebSocket connection, handles reconnection, and distributes events to all dashboard components.

**Files:**
- Create: `dashboard-ui/src/hooks/useWebSocket.ts`
- Create: `dashboard-ui/src/lib/eventLabels.ts`
- Create: `dashboard-ui/src/context/EventContext.tsx`
- Modify: `dashboard-ui/src/App.tsx` (wrap with provider)

**Acceptance Criteria:**
- [ ] WebSocket connects on mount, auto-reconnects with exponential backoff
- [ ] Backfill events are loaded into state on connect
- [ ] New events are appended to shared state accessible by all components
- [ ] Connection status (connected/disconnected/reconnecting) is available in context
- [ ] Event labels map audit types to human-readable strings

**Verify:** Browser console shows "WebSocket connected" and backfill events logged

**Steps:**

- [ ] **Step 1: Create event label mapping**

Create `dashboard-ui/src/lib/eventLabels.ts`:
```typescript
export type EventType =
  | "draft_read"
  | "draft_listed"
  | "memory_searched"
  | "slack_sent"
  | "processed"
  | "demo_reset"
  | "ingested"
  | "error"
  | "tool_error";

export interface AuditEvent {
  ts: string;
  type: EventType;
  driver?: string;
  [key: string]: unknown;
}

export interface LabeledEvent extends AuditEvent {
  label: string;
  color: string;
}

const EVENT_LABELS: Record<string, { label: string; color: string }> = {
  draft_read: { label: "Draft processed", color: "var(--mc-cyan)" },
  draft_listed: { label: "Drafts scanned", color: "var(--mc-cyan)" },
  memory_searched: { label: "Memory search completed", color: "var(--mc-cyan)" },
  slack_sent: { label: "Slack reply sent", color: "var(--mc-green)" },
  processed: { label: "Draft finalized", color: "var(--mc-green)" },
  demo_reset: { label: "Demo reset", color: "var(--mc-amber)" },
  ingested: { label: "Corpus ingested", color: "var(--mc-cyan)" },
  error: { label: "Error", color: "var(--mc-red)" },
  tool_error: { label: "Tool error", color: "var(--mc-red)" },
};

export function labelEvent(event: AuditEvent): LabeledEvent {
  const config = EVENT_LABELS[event.type] || {
    label: event.type,
    color: "var(--mc-text-dim)",
  };

  let label = config.label;
  if (event.type === "memory_searched" && event.count === 0) {
    label = "Below threshold — skipped";
    return { ...event, label, color: "var(--mc-amber)" };
  }

  return { ...event, label, color: config.color };
}
```

- [ ] **Step 2: Create WebSocket hook**

Create `dashboard-ui/src/hooks/useWebSocket.ts`:
```typescript
import { useEffect, useRef, useCallback, useState } from "react";
import type { AuditEvent } from "../lib/eventLabels";

type ConnectionStatus = "connected" | "disconnected" | "reconnecting";

interface UseWebSocketReturn {
  status: ConnectionStatus;
  events: AuditEvent[];
}

export function useWebSocket(): UseWebSocketReturn {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const maxRetries = 10;

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/events`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      retriesRef.current = 0;
    };

    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data);
      if (data.type === "backfill") {
        setEvents(data.events);
      } else {
        setEvents((prev) => [...prev, data]);
      }
    };

    ws.onclose = () => {
      setStatus("reconnecting");
      const delay = Math.min(1000 * 2 ** retriesRef.current, 30000);
      retriesRef.current += 1;
      if (retriesRef.current <= maxRetries) {
        setTimeout(connect, delay);
      } else {
        setStatus("disconnected");
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { status, events };
}
```

- [ ] **Step 3: Create EventContext**

Create `dashboard-ui/src/context/EventContext.tsx`:
```tsx
import { createContext, useContext, useMemo } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { labelEvent, type AuditEvent, type LabeledEvent } from "../lib/eventLabels";

interface EventContextValue {
  status: "connected" | "disconnected" | "reconnecting";
  events: AuditEvent[];
  labeledEvents: LabeledEvent[];
  searchEvents: AuditEvent[];
  lastEventTime: string | null;
}

const EventContext = createContext<EventContextValue | null>(null);

export function EventProvider({ children }: { children: React.ReactNode }) {
  const { status, events } = useWebSocket();

  const value = useMemo(() => {
    const labeledEvents = events.map(labelEvent);
    const searchEvents = events.filter((e) => e.type === "memory_searched");
    const lastEventTime = events.length > 0 ? events[events.length - 1].ts : null;
    return { status, events, labeledEvents, searchEvents, lastEventTime };
  }, [status, events]);

  return (
    <EventContext.Provider value={value}>{children}</EventContext.Provider>
  );
}

export function useEvents() {
  const ctx = useContext(EventContext);
  if (!ctx) throw new Error("useEvents must be inside EventProvider");
  return ctx;
}
```

- [ ] **Step 4: Wrap App with EventProvider**

Update `dashboard-ui/src/App.tsx`:
```tsx
import { EventProvider } from "./context/EventContext";

export default function App() {
  return (
    <EventProvider>
      <div className="min-h-screen p-6">
        <h1
          className="text-2xl font-bold tracking-wider uppercase"
          style={{ color: "var(--mc-cyan)" }}
        >
          Memory-Claw Mission Control
        </h1>
      </div>
    </EventProvider>
  );
}
```

- [ ] **Step 5: Verify in browser, commit**

Open browser, check console for "WebSocket connected" (or network tab showing WS connection).

```bash
git add dashboard-ui/src/
git commit -m "feat(dashboard): websocket hook + event context + labels"
```

---

## Task 4: System Status Strip Component

**Goal:** Build the top status bar showing service health indicators and last event time.

**Files:**
- Create: `dashboard-ui/src/components/StatusStrip.tsx`
- Modify: `dashboard-ui/src/App.tsx` (add component)

**Acceptance Criteria:**
- [ ] Shows Slack, Chroma, Ollama, Listener status with colored dots
- [ ] Polls `/api/health` every 10 seconds
- [ ] Last event time updates live from WebSocket context
- [ ] Turns amber if last event > 60s ago
- [ ] Listener dot pulses when WebSocket is connected

**Verify:** Visual check in browser — dots show green/amber/red based on actual service state

**Steps:**

- [ ] **Step 1: Create StatusStrip component**

Create `dashboard-ui/src/components/StatusStrip.tsx`:
```tsx
import { useEffect, useState } from "react";
import { useEvents } from "../context/EventContext";

interface HealthStatus {
  slack: { status: string };
  chroma: { status: string };
  ollama: { status: string };
  last_event: string | null;
}

function StatusDot({ status, pulse }: { status: string; pulse?: boolean }) {
  const color =
    status === "online" || status === "connected"
      ? "var(--mc-green)"
      : status === "not_configured"
        ? "var(--mc-text-dim)"
        : status === "offline" || status === "error"
          ? "var(--mc-red)"
          : "var(--mc-amber)";

  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${pulse ? "animate-pulse" : ""}`}
      style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}` }}
    />
  );
}

function RelativeTime({ ts }: { ts: string | null }) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  if (!ts) return <span style={{ color: "var(--mc-text-dim)" }}>No events</span>;

  const diff = Math.floor((now - new Date(ts).getTime()) / 1000);
  const color = diff > 60 ? "var(--mc-amber)" : "var(--mc-text-dim)";
  const label = diff < 5 ? "just now" : diff < 60 ? `${diff}s ago` : `${Math.floor(diff / 60)}m ago`;

  return <span style={{ color }}>{label}</span>;
}

export function StatusStrip() {
  const { status: wsStatus, lastEventTime } = useEvents();
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const resp = await fetch("/api/health");
        setHealth(await resp.json());
      } catch {}
    };
    poll();
    const interval = setInterval(poll, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className="flex items-center gap-6 px-4 py-2 text-xs uppercase tracking-widest"
      style={{ backgroundColor: "var(--mc-surface)", borderBottom: "1px solid var(--mc-border)" }}
    >
      <div className="flex items-center gap-2">
        <StatusDot status={health?.slack?.status || "unknown"} />
        <span>Slack</span>
      </div>
      <div className="flex items-center gap-2">
        <StatusDot status={health?.chroma?.status || "unknown"} />
        <span>Chroma</span>
      </div>
      <div className="flex items-center gap-2">
        <StatusDot status={health?.ollama?.status || "unknown"} />
        <span>Ollama</span>
      </div>
      <div className="flex items-center gap-2">
        <StatusDot status={wsStatus === "connected" ? "online" : "offline"} pulse={wsStatus === "connected"} />
        <span>Listener</span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <span style={{ color: "var(--mc-text-dim)" }}>Last event:</span>
        <RelativeTime ts={lastEventTime} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add to App layout**

Update `dashboard-ui/src/App.tsx`:
```tsx
import { EventProvider } from "./context/EventContext";
import { StatusStrip } from "./components/StatusStrip";

export default function App() {
  return (
    <EventProvider>
      <div className="min-h-screen flex flex-col">
        <header className="px-6 py-4 flex items-center justify-between"
                style={{ borderBottom: "1px solid var(--mc-border)" }}>
          <h1 className="text-lg font-bold tracking-wider uppercase"
              style={{ color: "var(--mc-cyan)" }}>
            Memory-Claw Mission Control
          </h1>
          <span className="text-xs uppercase tracking-widest px-2 py-1 rounded"
                style={{ color: "var(--mc-green)", border: "1px solid var(--mc-green)" }}>
            Online
          </span>
        </header>
        <StatusStrip />
        <main className="flex-1 p-6">
          {/* panels go here */}
        </main>
      </div>
    </EventProvider>
  );
}
```

- [ ] **Step 3: Verify in browser, commit**

Check: status strip shows with colored dots. If Ollama/Chroma running locally, dots show green.

```bash
git add dashboard-ui/src/
git commit -m "feat(dashboard): system status strip with health polling"
```

---

## Task 5: Animated Pipeline Flow

**Goal:** Build the SVG-based pipeline visualization that shows data flowing through INBOX → EMBED → CHROMA → SEARCH → SLACK with animated data packets.

**Files:**
- Create: `dashboard-ui/src/components/PipelineFlow.tsx`
- Modify: `dashboard-ui/src/App.tsx` (add component)

**Acceptance Criteria:**
- [ ] 5 pipeline nodes rendered as rounded boxes with labels
- [ ] Nodes connected by paths with directional arrows
- [ ] Idle state: nodes have subtle breathing/pulse animation
- [ ] On event: corresponding node glows brighter + data packet animates along path
- [ ] Multiple rapid events create cascading packets
- [ ] Event type maps to correct node (draft_read→INBOX, memory_searched→SEARCH, etc.)

**Verify:** Trigger `audit.log_event("draft_read", path="test")` — INBOX node pulses and packet flows to EMBED

**Steps:**

- [ ] **Step 1: Create PipelineFlow component**

Create `dashboard-ui/src/components/PipelineFlow.tsx`:
```tsx
import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useEvents } from "../context/EventContext";

const NODES = [
  { id: "inbox", label: "INBOX", x: 80, y: 50 },
  { id: "embed", label: "EMBED", x: 250, y: 50 },
  { id: "chroma", label: "CHROMA", x: 420, y: 50 },
  { id: "search", label: "SEARCH", x: 590, y: 50 },
  { id: "slack", label: "SLACK", x: 760, y: 50 },
];

const EVENT_TO_NODE: Record<string, string> = {
  draft_read: "inbox",
  draft_listed: "inbox",
  ingested: "embed",
  memory_searched: "search",
  slack_sent: "slack",
  processed: "chroma",
};

interface Packet {
  id: number;
  fromIndex: number;
  toIndex: number;
}

let packetId = 0;

export function PipelineFlow() {
  const { events } = useEvents();
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [packets, setPackets] = useState<Packet[]>([]);
  const prevLength = useRef(events.length);

  useEffect(() => {
    if (events.length <= prevLength.current) {
      prevLength.current = events.length;
      return;
    }
    const newEvents = events.slice(prevLength.current);
    prevLength.current = events.length;

    for (const event of newEvents) {
      const nodeId = EVENT_TO_NODE[event.type];
      if (!nodeId) continue;

      setActiveNode(nodeId);
      setTimeout(() => setActiveNode(null), 1500);

      const nodeIndex = NODES.findIndex((n) => n.id === nodeId);
      if (nodeIndex < NODES.length - 1) {
        const id = ++packetId;
        setPackets((prev) => [...prev, { id, fromIndex: nodeIndex, toIndex: nodeIndex + 1 }]);
        setTimeout(() => {
          setPackets((prev) => prev.filter((p) => p.id !== id));
        }, 1000);
      }
    }
  }, [events]);

  return (
    <div className="w-full py-4 px-6" style={{ backgroundColor: "var(--mc-surface)", borderBottom: "1px solid var(--mc-border)" }}>
      <svg viewBox="0 0 860 100" className="w-full h-20">
        {/* Connection lines */}
        {NODES.slice(0, -1).map((node, i) => (
          <line
            key={`line-${i}`}
            x1={node.x + 60}
            y1={node.y}
            x2={NODES[i + 1].x - 60}
            y2={NODES[i + 1].y}
            stroke="var(--mc-border)"
            strokeWidth="2"
            strokeDasharray="4 4"
          />
        ))}

        {/* Nodes */}
        {NODES.map((node) => (
          <g key={node.id}>
            <motion.rect
              x={node.x - 55}
              y={node.y - 22}
              width="110"
              height="44"
              rx="8"
              fill="var(--mc-surface)"
              stroke={activeNode === node.id ? "var(--mc-cyan)" : "var(--mc-border)"}
              strokeWidth={activeNode === node.id ? 2 : 1}
              animate={{
                filter: activeNode === node.id
                  ? "drop-shadow(0 0 12px rgba(0, 212, 255, 0.8))"
                  : "drop-shadow(0 0 4px rgba(0, 212, 255, 0.1))",
              }}
              transition={{ duration: 0.3 }}
            />
            <text
              x={node.x}
              y={node.y + 4}
              textAnchor="middle"
              fill={activeNode === node.id ? "var(--mc-cyan)" : "var(--mc-text)"}
              fontSize="11"
              fontFamily="monospace"
              fontWeight="bold"
              letterSpacing="1"
            >
              {node.label}
            </text>
            {/* Idle breathing animation */}
            <motion.rect
              x={node.x - 55}
              y={node.y - 22}
              width="110"
              height="44"
              rx="8"
              fill="none"
              stroke="var(--mc-cyan)"
              strokeWidth="1"
              initial={{ opacity: 0.05 }}
              animate={{ opacity: [0.05, 0.15, 0.05] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            />
          </g>
        ))}

        {/* Data packets */}
        <AnimatePresence>
          {packets.map((packet) => {
            const from = NODES[packet.fromIndex];
            const to = NODES[packet.toIndex];
            return (
              <motion.circle
                key={packet.id}
                r="5"
                fill="var(--mc-cyan)"
                filter="url(#glow)"
                initial={{ cx: from.x + 60, cy: from.y }}
                animate={{ cx: to.x - 60, cy: to.y }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.8, ease: "easeInOut" }}
              />
            );
          })}
        </AnimatePresence>

        {/* Glow filter */}
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      </svg>
    </div>
  );
}
```

- [ ] **Step 2: Add to App layout**

Add `<PipelineFlow />` between `<StatusStrip />` and `<main>` in App.tsx.

- [ ] **Step 3: Test with live event, commit**

Start both servers. In Python REPL:
```python
from institutional_memory.audit import log_event
log_event("draft_read", path="test.md")
```

Verify INBOX node glows and packet animates rightward.

```bash
git add dashboard-ui/src/
git commit -m "feat(dashboard): animated pipeline flow with data packets"
```

---

## Task 6: Live Telemetry Feed Component

**Goal:** Build the scrolling event feed that shows curated, human-readable events with expandable JSON details.

**Files:**
- Create: `dashboard-ui/src/components/LiveFeed.tsx`
- Modify: `dashboard-ui/src/App.tsx` (add to grid)

**Acceptance Criteria:**
- [ ] Shows last 15 events with human-readable labels
- [ ] Color-coded by event category
- [ ] New events animate in from top with glow effect
- [ ] Each row expandable to show raw JSON
- [ ] Auto-scrolls to latest event

**Verify:** Trigger events via `log_event()` — they appear with correct labels and colors

**Steps:**

- [ ] **Step 1: Create LiveFeed component**

Create `dashboard-ui/src/components/LiveFeed.tsx`:
```tsx
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useEvents } from "../context/EventContext";
import type { LabeledEvent } from "../lib/eventLabels";

function EventRow({ event }: { event: LabeledEvent }) {
  const [expanded, setExpanded] = useState(false);
  const time = new Date(event.ts).toLocaleTimeString();

  return (
    <motion.div
      initial={{ opacity: 0, y: -20, filter: "brightness(2)" }}
      animate={{ opacity: 1, y: 0, filter: "brightness(1)" }}
      transition={{ duration: 0.4 }}
      className="px-3 py-2 rounded cursor-pointer"
      style={{ borderLeft: `3px solid ${event.color}`, backgroundColor: "var(--mc-surface)" }}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-bold" style={{ color: event.color }}>
          {event.label}
        </span>
        <span className="text-xs" style={{ color: "var(--mc-text-dim)" }}>
          {time}
        </span>
      </div>
      {expanded && (
        <motion.pre
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          className="mt-2 text-xs overflow-x-auto p-2 rounded"
          style={{ backgroundColor: "var(--mc-bg)", color: "var(--mc-text-dim)" }}
        >
          {JSON.stringify(event, null, 2)}
        </motion.pre>
      )}
    </motion.div>
  );
}

export function LiveFeed() {
  const { labeledEvents } = useEvents();
  const containerRef = useRef<HTMLDivElement>(null);
  const visible = labeledEvents.slice(-15);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [visible.length]);

  return (
    <div className="flex flex-col h-full">
      <h2
        className="text-xs font-bold uppercase tracking-widest mb-3"
        style={{ color: "var(--mc-text-dim)" }}
      >
        Live Telemetry
      </h2>
      <div ref={containerRef} className="flex-1 overflow-y-auto space-y-2 max-h-72">
        <AnimatePresence initial={false}>
          {visible.map((event, i) => (
            <EventRow key={`${event.ts}-${i}`} event={event} />
          ))}
        </AnimatePresence>
        {visible.length === 0 && (
          <div className="text-xs italic" style={{ color: "var(--mc-text-dim)" }}>
            Waiting for events...
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add to App grid, commit**

Update App.tsx main area to use CSS grid with LiveFeed in left column.

```bash
git add dashboard-ui/src/
git commit -m "feat(dashboard): live telemetry feed with animations"
```

---

## Task 7: Relevance Distribution Chart

**Goal:** Build the area chart showing cosine similarity scores over time with a threshold line.

**Files:**
- Create: `dashboard-ui/src/components/RelevanceChart.tsx`
- Modify: `dashboard-ui/src/App.tsx` (add to grid)

**Acceptance Criteria:**
- [ ] Tremor AreaChart displays relevance scores over time
- [ ] Threshold line at 0.60 visible
- [ ] Points above threshold colored cyan, below colored dim
- [ ] Updates in real-time as search events arrive
- [ ] Graceful empty state when no search data exists

**Verify:** Run several `search-memory` commands — chart populates with data points

**Steps:**

- [ ] **Step 1: Create RelevanceChart component**

Create `dashboard-ui/src/components/RelevanceChart.tsx`:
```tsx
import { useMemo } from "react";
import { AreaChart } from "@tremor/react";
import { useEvents } from "../context/EventContext";

export function RelevanceChart() {
  const { searchEvents } = useEvents();

  const chartData = useMemo(() => {
    return searchEvents
      .filter((e) => e.top_score != null)
      .slice(-30)
      .map((e) => ({
        time: new Date(e.ts as string).toLocaleTimeString(),
        score: Number(e.top_score),
        threshold: 0.6,
      }));
  }, [searchEvents]);

  return (
    <div className="flex flex-col h-full">
      <h2
        className="text-xs font-bold uppercase tracking-widest mb-3"
        style={{ color: "var(--mc-text-dim)" }}
      >
        Relevance Distribution
      </h2>
      {chartData.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-xs italic"
             style={{ color: "var(--mc-text-dim)" }}>
          Awaiting search data...
        </div>
      ) : (
        <AreaChart
          className="h-52"
          data={chartData}
          index="time"
          categories={["score", "threshold"]}
          colors={["cyan", "amber"]}
          showLegend={false}
          showGridLines={false}
          curveType="monotone"
          yAxisWidth={40}
          minValue={0}
          maxValue={1}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add to App grid, commit**

Place in right column of top grid row.

```bash
git add dashboard-ui/src/
git commit -m "feat(dashboard): relevance distribution area chart"
```

---

## Task 8: Recent Queries Table & Knowledge Base Status

**Goal:** Build the bottom two panels — recent queries table and knowledge base stats.

**Files:**
- Create: `dashboard-ui/src/components/RecentQueries.tsx`
- Create: `dashboard-ui/src/components/KnowledgeBase.tsx`
- Modify: `dashboard-ui/src/App.tsx` (complete grid layout)

**Acceptance Criteria:**
- [ ] Recent Queries table shows query, score, source, time
- [ ] Scores color-coded by band (≥0.80 bright cyan, 0.60-0.79 standard, <0.60 amber)
- [ ] Knowledge Base shows document count, chunks, model, collection, last ingest
- [ ] KB panel refreshes after ingest events
- [ ] Full 2x2 grid layout assembled and responsive to container

**Verify:** Visual check — all 4 panels render in grid with correct data

**Steps:**

- [ ] **Step 1: Create RecentQueries component**

Create `dashboard-ui/src/components/RecentQueries.tsx`:
```tsx
import { useEffect, useState } from "react";
import { useEvents } from "../context/EventContext";

interface QueryRow {
  query: string;
  top_score: number | null;
  source: string | null;
  ts: string;
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score == null) return <span style={{ color: "var(--mc-text-dim)" }}>—</span>;
  const color =
    score >= 0.8 ? "var(--mc-cyan)" : score >= 0.6 ? "var(--mc-text)" : "var(--mc-amber)";
  return (
    <span className="font-bold" style={{ color }}>
      {score.toFixed(3)}
    </span>
  );
}

export function RecentQueries() {
  const { events } = useEvents();
  const [queries, setQueries] = useState<QueryRow[]>([]);

  useEffect(() => {
    fetch("/api/recent-queries")
      .then((r) => r.json())
      .then(setQueries)
      .catch(() => {});
  }, []);

  useEffect(() => {
    const searchEvents = events.filter((e) => e.type === "memory_searched");
    if (searchEvents.length > 0) {
      const latest = searchEvents.slice(-20).map((e) => ({
        query: (e.query as string) || "",
        top_score: (e.top_score as number) || null,
        source: (e.source as string) || null,
        ts: e.ts,
      }));
      setQueries((prev) => [...latest, ...prev].slice(0, 20));
    }
  }, [events]);

  return (
    <div className="flex flex-col h-full">
      <h2
        className="text-xs font-bold uppercase tracking-widest mb-3"
        style={{ color: "var(--mc-text-dim)" }}
      >
        Recent Queries
      </h2>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-xs">
          <thead>
            <tr style={{ color: "var(--mc-text-dim)" }}>
              <th className="text-left pb-2">Query</th>
              <th className="text-right pb-2">Score</th>
              <th className="text-left pb-2 pl-3">Source</th>
              <th className="text-right pb-2">Time</th>
            </tr>
          </thead>
          <tbody>
            {queries.map((q, i) => (
              <tr key={`${q.ts}-${i}`} className="border-t" style={{ borderColor: "var(--mc-border)" }}>
                <td className="py-1.5 max-w-[180px] truncate">{q.query}</td>
                <td className="py-1.5 text-right"><ScoreBadge score={q.top_score} /></td>
                <td className="py-1.5 pl-3 max-w-[120px] truncate" style={{ color: "var(--mc-text-dim)" }}>
                  {q.source || "—"}
                </td>
                <td className="py-1.5 text-right" style={{ color: "var(--mc-text-dim)" }}>
                  {new Date(q.ts).toLocaleTimeString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {queries.length === 0 && (
          <div className="text-xs italic pt-4" style={{ color: "var(--mc-text-dim)" }}>
            No searches yet...
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create KnowledgeBase component**

Create `dashboard-ui/src/components/KnowledgeBase.tsx`:
```tsx
import { useEffect, useState } from "react";
import { useEvents } from "../context/EventContext";

interface Stats {
  documents: number;
  chunks: number;
  collection: string;
  embedding_model: string;
  last_ingest: string | null;
}

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-center py-2"
         style={{ borderBottom: "1px solid var(--mc-border)" }}>
      <span className="text-xs uppercase tracking-wider" style={{ color: "var(--mc-text-dim)" }}>
        {label}
      </span>
      <span className="text-sm font-bold" style={{ color: "var(--mc-cyan)" }}>
        {value}
      </span>
    </div>
  );
}

export function KnowledgeBase() {
  const { events } = useEvents();
  const [stats, setStats] = useState<Stats | null>(null);

  const fetchStats = () => {
    fetch("/api/stats")
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {});
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    const hasIngest = events.some((e) => e.type === "ingested");
    if (hasIngest) fetchStats();
  }, [events]);

  if (!stats) return null;

  const lastIngest = stats.last_ingest
    ? new Date(stats.last_ingest).toLocaleTimeString()
    : "Never";

  return (
    <div className="flex flex-col h-full">
      <h2
        className="text-xs font-bold uppercase tracking-widest mb-3"
        style={{ color: "var(--mc-text-dim)" }}
      >
        Knowledge Base Status
      </h2>
      <div className="flex-1">
        <StatRow label="Documents" value={stats.documents} />
        <StatRow label="Chunks" value={stats.chunks} />
        <StatRow label="Model" value={stats.embedding_model} />
        <StatRow label="Collection" value={stats.collection} />
        <StatRow label="Last Ingest" value={lastIngest} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Assemble final App layout**

Update `dashboard-ui/src/App.tsx`:
```tsx
import { EventProvider } from "./context/EventContext";
import { StatusStrip } from "./components/StatusStrip";
import { PipelineFlow } from "./components/PipelineFlow";
import { LiveFeed } from "./components/LiveFeed";
import { RelevanceChart } from "./components/RelevanceChart";
import { RecentQueries } from "./components/RecentQueries";
import { KnowledgeBase } from "./components/KnowledgeBase";

export default function App() {
  return (
    <EventProvider>
      <div className="min-h-screen flex flex-col">
        <header
          className="px-6 py-4 flex items-center justify-between"
          style={{ borderBottom: "1px solid var(--mc-border)" }}
        >
          <h1
            className="text-lg font-bold tracking-wider uppercase"
            style={{ color: "var(--mc-cyan)" }}
          >
            Memory-Claw Mission Control
          </h1>
          <span
            className="text-xs uppercase tracking-widest px-2 py-1 rounded"
            style={{ color: "var(--mc-green)", border: "1px solid var(--mc-green)" }}
          >
            Online
          </span>
        </header>
        <StatusStrip />
        <PipelineFlow />
        <main className="flex-1 p-6 grid grid-cols-2 gap-6">
          <div
            className="p-4 rounded-lg"
            style={{ backgroundColor: "var(--mc-surface)", border: "1px solid var(--mc-border)" }}
          >
            <LiveFeed />
          </div>
          <div
            className="p-4 rounded-lg"
            style={{ backgroundColor: "var(--mc-surface)", border: "1px solid var(--mc-border)" }}
          >
            <RelevanceChart />
          </div>
          <div
            className="p-4 rounded-lg"
            style={{ backgroundColor: "var(--mc-surface)", border: "1px solid var(--mc-border)" }}
          >
            <RecentQueries />
          </div>
          <div
            className="p-4 rounded-lg"
            style={{ backgroundColor: "var(--mc-surface)", border: "1px solid var(--mc-border)" }}
          >
            <KnowledgeBase />
          </div>
        </main>
      </div>
    </EventProvider>
  );
}
```

- [ ] **Step 4: Verify full layout, commit**

Check: all 6 panels render correctly in browser. Grid is 2x2 below pipeline flow.

```bash
git add dashboard-ui/src/
git commit -m "feat(dashboard): recent queries table + knowledge base + full layout"
```

---

## Task 9: Production Build & Serve

**Goal:** Configure production build output so FastAPI serves the built React app as static files, making the dashboard a single-process deployment.

**Files:**
- Modify: `institutional_memory/dashboard/server.py` (static file serving order)
- Create: `dashboard-ui/.gitignore`
- Modify: root `.gitignore` (ignore node_modules, dashboard static build)

**Acceptance Criteria:**
- [ ] `cd dashboard-ui && npm run build` outputs to `institutional_memory/dashboard/static/`
- [ ] `uv run python -m institutional_memory.dashboard.server` serves dashboard at `/`
- [ ] API routes still work at `/api/*` and `/ws/*`
- [ ] No CORS issues in production mode (same origin)

**Verify:** Build frontend, start only FastAPI, open http://localhost:8000 — full dashboard loads

**Steps:**

- [ ] **Step 1: Create dashboard-ui/.gitignore**

```
node_modules/
dist/
```

- [ ] **Step 2: Update root .gitignore**

Add:
```
dashboard-ui/node_modules/
institutional_memory/dashboard/static/
```

- [ ] **Step 3: Fix server static mount order**

Ensure in `server.py` that API routes are registered BEFORE the static mount (FastAPI matches routes in order). The static mount with `html=True` should be last:

```python
# At the very end of server.py, after all @app routes:
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
```

- [ ] **Step 4: Build and test**

```bash
cd dashboard-ui && npm run build
cd ..
uv run python -m institutional_memory.dashboard.server
```

Open http://localhost:8000 — dashboard should load with all panels.

- [ ] **Step 5: Commit**

```bash
git add .gitignore dashboard-ui/.gitignore institutional_memory/dashboard/server.py
git commit -m "feat(dashboard): production build config + static serving"
```

---

## Dependency Order

```
Task 0 (scaffolding)
  ├── Task 1 (WebSocket broadcast) → Task 3 (frontend WS hook)
  ├── Task 2 (REST API)            → Task 4 (status strip)
  │                                → Task 8 (recent queries + KB)
  └── Task 3 (WS hook + context)
        ├── Task 4 (status strip)
        ├── Task 5 (pipeline flow)
        ├── Task 6 (live feed)
        ├── Task 7 (relevance chart)
        └── Task 8 (queries + KB)

Task 9 (production build) depends on all above
```

**Parallelizable:** After Tasks 0-3, Tasks 4-8 can all be built independently (they only depend on EventContext existing).
