# Incident Management System (IMS)

A mission-critical, real-time Incident Management System built to monitor distributed infrastructure and manage failure resolution workflows from signal ingestion to root cause analysis.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│              Signal Sources (Monitored Stack)            │
│   APIs · MCP Hosts · Caches · Queues · RDBMS · NoSQL   │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP POST /api/v1/signals
                         ▼
┌─────────────────────────────────────────────────────────┐
│            Ingestion Layer (FastAPI)                     │
│   Rate Limiter (500/min) → In-Memory Queue (50k cap)    │
│            Debouncer (100 signals/10s → 1 WI)           │
└──────┬─────────────────┬───────────────────┬────────────┘
       │                 │                   │
       ▼                 ▼                   ▼
┌────────────┐  ┌──────────────┐  ┌──────────────────┐
│  MongoDB   │  │  PostgreSQL  │  │     Redis         │
│ Raw signal │  │  Work Items  │  │  Dashboard cache  │
│ audit log  │  │  RCA records │  │  Debounce state   │
│ (Data Lake)│  │  (ACID txns) │  │  Metrics          │
└────────────┘  └──────────────┘  └──────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Workflow Engine                             │
│   State Machine: OPEN→INVESTIGATING→RESOLVED→CLOSED     │
│   Alert Strategy: P0 (page) · P1 (slack) · P2 (ticket) │
└─────────────────────────────────────────────────────────┘
                         │ REST API + WebSocket
                         ▼
┌─────────────────────────────────────────────────────────┐
│              React Frontend                              │
│   Live Feed · Incident Detail · RCA Form · MTTR         │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- Git

### Run Everything (1 command)

```bash
git clone <your-repo-url>
cd ims-zeotap

docker compose up --build
```

Wait about 30 seconds for all services to start, then:

| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Health Check | http://localhost:8000/health |
| API Docs | http://localhost:8000/docs |

### Simulate a Failure

```bash
# Install requests first
pip install requests

# Run simulation (sends 310 signals across 4 components)
python scripts/simulate_failure.py
```

Then open http://localhost:5173 to see incidents appear on the dashboard.

---

## How Backpressure Works

This is a critical design decision for handling 10,000 signals/second.

**The Problem:** If signals arrive faster than the database can save them, the system crashes.

**Our Solution — Bounded Async Queue:**

```
Signal arrives → enqueue_signal()
                      │
                      ▼
           asyncio.Queue(maxsize=50,000)
                      │
          ┌───────────┴───────────┐
          │    Is queue full?      │
          ▼                       ▼
     YES: Drop signal          NO: Add to queue
     Return 429                Return 202 Accepted
     Log warning                      │
                                      ▼
                          10 Worker coroutines
                          drain queue at DB speed
```

**Key points:**
- The HTTP endpoint NEVER blocks — it accepts or rejects in microseconds
- Workers process signals at the pace the database can handle
- If queue fills up, callers get a 429 to slow down (backpressure signal)
- Dropped signals are logged with a counter for observability

---

## Tech Stack Choices

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | Python + FastAPI | Async-native, fast, great WebSocket support |
| Task Queue | asyncio.Queue | Zero dependencies, bounded, non-blocking |
| Source of Truth | PostgreSQL | ACID transactions for work items and RCA |
| Data Lake | MongoDB | Flexible schema for raw signals, great for audit logs |
| Hot Cache | Redis | Sub-millisecond reads for dashboard, atomic operations for debounce |
| Frontend | React + Vite | Fast dev, component-based, easy WebSocket integration |
| Containerization | Docker Compose | One-command startup, isolated environments |

---

## Design Patterns Used

### State Pattern (Work Item Lifecycle)
```
OPEN → INVESTIGATING → RESOLVED → CLOSED
```
Each state knows what transitions are valid. Invalid moves are rejected with a 409 error. Closing without an RCA raises a 422 error. Implemented in `backend/app/core/state_machine.py`.

### Strategy Pattern (Alert Routing)
Different components get different alert handling:
- **P0** (RDBMS, MCP_HOST) → Pages on-call engineer immediately
- **P1** (API, QUEUE) → Notifies team Slack channel
- **P2** (CACHE, NOSQL) → Creates ticket for business hours

Implemented in `backend/app/core/alert_strategies.py`.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/signals` | Ingest single signal |
| POST | `/api/v1/signals/batch` | Ingest up to 500 signals |
| GET | `/api/v1/incidents` | List all incidents |
| GET | `/api/v1/incidents/{id}` | Get incident detail |
| PATCH | `/api/v1/incidents/{id}/status` | Advance incident status |
| POST | `/api/v1/incidents/{id}/rca` | Submit RCA |
| GET | `/api/v1/incidents/{id}/signals` | Get raw signals from MongoDB |
| GET | `/health` | Health check (all backends) |
| WS | `/ws/incidents` | Live incident feed |

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## Non-Functional Highlights (Bonus Points)

- **Rate Limiting:** 500 requests/minute per IP via `slowapi`
- **Retry Logic:** All DB writes use `tenacity` (3 retries, exponential backoff)
- **Row-level Locking:** Status transitions use `SELECT FOR UPDATE` to prevent race conditions
- **Observability:** `/health` endpoint + throughput metrics printed every 5 seconds
- **Auto-reconnect WebSocket:** Frontend reconnects automatically if connection drops
- **CORS configured:** Ready for deployment behind a reverse proxy
