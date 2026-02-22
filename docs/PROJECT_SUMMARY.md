# Distributed Task Queue — Complete Project Summary

## Overview

This is a **full-stack distributed task queue system** built with Python (FastAPI) on the backend, React (TypeScript) on the frontend, and Redis as the message broker. It demonstrates a production-grade architecture for asynchronous job processing with priority scheduling, retry logic, dead letter queues, real-time monitoring, and containerized deployment.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
│   React + TypeScript + TailwindCSS + Recharts               │
│   (Dashboard, Tasks, Queues, Workers pages)                 │
│   Served via Nginx (production) / Vite (development)        │
└─────────────────┬───────────────────────┬───────────────────┘
                  │ REST API              │ WebSocket
                  ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                        │
│   /api/tasks    - Task CRUD & submission                    │
│   /api/queues   - Queue stats, pause/resume                 │
│   /api/workers  - Worker monitoring & stats                 │
│   /api/ws       - Real-time WebSocket updates               │
│   /api/health   - Health check endpoint                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Redis (Message Broker)                    │
│   Sorted Sets  → Priority queuing (ZADD/BZPOPMIN)           │
│   Sets         → Processing/completed/failed tracking       │
│   Strings      → Task data (JSON) & worker state            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Worker Processes (1-N)                    │
│   Poll queues → Execute handlers → Update task status       │
│   Retry with exponential backoff → Dead letter queue        │
│   Heartbeat monitoring → Graceful shutdown                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer       | Technology                                                    |
|-------------|---------------------------------------------------------------|
| **Backend** | Python 3.11, FastAPI, Pydantic v2, Uvicorn, structlog         |
| **Broker**  | Redis 7 (async via `redis-py`), sorted sets for priority      |
| **Workers** | Async Python, concurrent task processing, signal handling     |
| **Frontend**| React 18, TypeScript, TailwindCSS, Recharts, React Query      |
| **Routing** | React Router v6 (SPA with sidebar navigation)                |
| **Testing** | pytest, pytest-asyncio, fakeredis, httpx (ASGI transport)     |
| **DevOps**  | Docker, Docker Compose, Nginx reverse proxy, Makefile         |
| **Deploy**  | Vercel (serverless), Docker (production), local dev           |

---

## Project Structure

### Backend (`src/`)

| File/Module             | Purpose                                                        |
|-------------------------|----------------------------------------------------------------|
| `config.py`             | Pydantic-settings config loaded from env vars / `.env`         |
| `logging_config.py`     | Structured logging with structlog (JSON prod, colored dev)     |
| `api/main.py`           | FastAPI app creation, lifespan (Redis connect/disconnect), CORS, error handlers |
| `api/schemas.py`        | 20+ Pydantic models for request/response validation            |
| `api/dependencies.py`   | Dependency injection — lazy Redis broker with retry            |
| `api/routers/tasks.py`  | Task CRUD: create, get, list, cancel, retry                   |
| `api/routers/queues.py` | Queue stats, pause/resume, dead letter queue management        |
| `api/routers/workers.py`| Worker listing, individual stats, health monitoring            |
| `api/routers/ws.py`     | WebSocket endpoints for real-time task & dashboard updates     |
| `queue/task.py`         | `Task` dataclass with status transitions, serialization, retry logic |
| `queue/broker.py`       | `RedisBroker` — enqueue/dequeue/update with priority sorted sets |
| `worker/worker.py`      | `Worker` class — polling loop, handler execution, heartbeat    |
| `worker/main.py`        | CLI entry point with arg parsing, signal handling, handler discovery |
| `worker/utils.py`       | Worker stats, stale worker cleanup, orphaned task recovery     |
| `worker/handlers/`      | 3 example handlers: email, image resize, data processing       |

### Frontend (`frontend/src/`)

| File/Module              | Purpose                                                      |
|--------------------------|--------------------------------------------------------------|
| `App.tsx`                | React Router route definitions                               |
| `main.tsx`               | App entry point with React Query + BrowserRouter              |
| `pages/Dashboard.tsx`    | Overview dashboard with queue/worker stats                   |
| `pages/Tasks.tsx`        | Task list with filtering, creation modal, detail panel       |
| `pages/Queues.tsx`       | Queue list with stats, pause/resume controls                 |
| `pages/Workers.tsx`      | Worker list with status, heartbeat, task counts              |
| `components/Layout.tsx`  | Sidebar navigation layout with Lucide icons                  |
| `components/StatusBadge.tsx`     | Color-coded status badge component                   |
| `components/TaskSubmitModal.tsx` | Task creation form modal                             |
| `components/TaskDetailPanel.tsx` | Slide-in task detail panel                           |
| `components/RealTimeChart.tsx`   | Recharts-based live chart with data hook             |
| `lib/api.ts`             | Axios/fetch API client for backend communication             |
| `lib/websocket.ts`       | WebSocket client for real-time updates                       |
| `types/index.ts`         | TypeScript type definitions matching API schemas             |

### Infrastructure

| File                     | Purpose                                                      |
|--------------------------|--------------------------------------------------------------|
| `docker-compose.yml`     | Production stack: Redis, API, 3 workers, Nginx frontend      |
| `docker-compose.dev.yml` | Dev overrides: hot reload, Vite dev server, Redis Commander   |
| `docker/Dockerfile.api`  | Multi-stage API image (pip + slim Python)                    |
| `docker/Dockerfile.worker` | Multi-stage worker image                                   |
| `docker/Dockerfile.frontend` | Multi-stage frontend (Node build → Nginx serve)          |
| `docker/nginx.conf`      | Reverse proxy: SPA serving, API/WS proxy, gzip, rate limiting|
| `Makefile`               | 30+ commands for dev, test, build, deploy, cleanup           |
| `api/index.py`           | Vercel serverless entry point                                |
| `vercel.json`            | Vercel deployment configuration                              |

---

## Core Concepts

### Task Lifecycle

```
  PENDING ──────► PROCESSING ──────► COMPLETED
     ▲                │
     │                │ (failure)
     │                ▼
     └──── RETRY ◄── FAILED ──────► DEAD LETTER QUEUE
          (if retries              (if max retries
           remaining)               exceeded)
```

1. **Submit** — Client sends `POST /api/tasks` with name, payload, priority (1-10), queue name
2. **Enqueue** — Task stored in Redis, added to priority sorted set (ZADD with negative priority score so higher priority = popped first)
3. **Dequeue** — Worker uses `BZPOPMIN` to atomically pop the highest-priority task
4. **Process** — Worker looks up registered handler by task name, executes with timeout
5. **Complete/Fail** — Task moved between Redis sets (processing → completed/failed)
6. **Retry** — Failed tasks get exponential backoff retry (base × 2^attempt, max 5 min)
7. **Dead Letter** — Tasks that exhaust retries go to a DLQ for manual analysis

### Priority Queue Implementation

Uses Redis sorted sets where the **score is the negative priority** (-10 to -1). `BZPOPMIN` pops the lowest score first, meaning priority 10 tasks are processed before priority 1 tasks.

### Worker Design

- **Multi-queue polling** — Workers poll multiple queues in configured order
- **Configurable concurrency** — Multiple async tasks per worker process
- **Handler registry** — Handlers are auto-discovered from `src/worker/handlers/` or registered via decorator
- **Heartbeat** — Workers send heartbeats every 10 seconds to Redis for health monitoring
- **Graceful shutdown** — SIGTERM/SIGINT triggers orderly shutdown, finishing current tasks

### Redis Key Schema

| Key Pattern                       | Type       | Purpose                     |
|-----------------------------------|------------|-----------------------------|
| `queue:{name}:pending`            | Sorted Set | Priority-ordered pending tasks |
| `queue:{name}:processing`         | Set        | Currently processing task IDs |
| `queue:{name}:completed`          | Set        | Completed task IDs          |
| `queue:{name}:failed`             | Set        | Failed task IDs             |
| `queue:{name}:dlq:failed`         | Set        | Dead letter queue entries    |
| `task:{uuid}`                     | String     | JSON task data              |
| `worker:{id}`                     | String     | JSON worker state           |
| `workers:active`                  | Set        | Active worker IDs           |
| `queues:paused`                   | Set        | Paused queue names          |

---

## API Endpoints

### Tasks (`/api/tasks`)
| Method   | Endpoint                    | Description                     |
|----------|-----------------------------|---------------------------------|
| `POST`   | `/api/tasks`                | Submit a new task               |
| `GET`    | `/api/tasks/{id}`           | Get task status & details       |
| `GET`    | `/api/tasks`                | List tasks (filter by status/queue, pagination) |
| `DELETE` | `/api/tasks/{id}`           | Cancel a pending task           |
| `POST`   | `/api/tasks/{id}/retry`     | Retry a failed task             |

### Queues (`/api/queues`)
| Method   | Endpoint                              | Description                 |
|----------|---------------------------------------|-----------------------------|
| `GET`    | `/api/queues`                         | List all queues with stats  |
| `GET`    | `/api/queues/{name}/stats`            | Get detailed queue stats    |
| `POST`   | `/api/queues/{name}/pause`            | Pause queue processing      |
| `POST`   | `/api/queues/{name}/resume`           | Resume paused queue         |
| `DELETE` | `/api/queues/{name}/dead-letter`      | Clear dead letter queue     |

### Workers (`/api/workers`)
| Method   | Endpoint                        | Description                     |
|----------|---------------------------------|---------------------------------|
| `GET`    | `/api/workers`                  | List all workers with status    |
| `GET`    | `/api/workers/{id}`             | Get specific worker details     |
| `GET`    | `/api/workers/{id}/stats`       | Get worker performance stats    |

### WebSocket (`/api/ws`)
| Endpoint                    | Description                              |
|-----------------------------|------------------------------------------|
| `/api/ws/tasks/{id}`        | Real-time task status updates (polls 500ms) |
| `/api/ws/dashboard`         | Live dashboard stats stream (every 1s)   |

### System
| Method | Endpoint       | Description              |
|--------|----------------|--------------------------|
| `GET`  | `/api`         | API root info & links    |
| `GET`  | `/api/health`  | Health check (Redis connectivity) |
| `GET`  | `/api/docs`    | Swagger UI documentation |
| `GET`  | `/api/redoc`   | ReDoc documentation      |

---

## Example Task Handlers

### Email Handler (`send_email`)
Simulates sending an email with a 2-second delay. Validates `to`, `subject`, `body` fields. Returns message ID.

### Image Handler (`resize_image`)
Simulates image resizing with a 5-second delay. Validates `url`, `width`, `height` fields. Returns resized URL and file size.

### Data Handler (`process_data`)
Simulates data processing with a 3-second delay. Accepts `data` (list/dict), `operation` (transform/aggregate/filter/validate). Returns processing statistics.

---

## How to Run

### Local Development (without Docker)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. Start Redis (required)
# Option A: via Docker
docker run -d -p 6379:6379 redis:7-alpine

# 3. Start the API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 4. Start a worker (in separate terminal)
python -m src.worker.main --worker-id local-worker --queues default,emails,images,data

# 5. Start the frontend (in separate terminal)
cd frontend && npm install && npm run dev
```

### Docker Compose (Production)

```bash
docker compose up -d          # Start all services
docker compose logs -f        # View logs
docker compose down           # Stop all services
```

### Docker Compose (Development, with hot reload)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Run Tests

```bash
pytest tests/ -v              # All 50 tests
pytest tests/test_api.py -v   # API tests only
pytest tests/test_broker.py   # Broker tests only
pytest tests/test_worker.py   # Worker tests only
```

---

## Issues Found & Fixed

### 1. API Test URLs Missing `/api` Prefix (12 tests failing)
**Problem:** All test URLs used `/health`, `/tasks`, `/queues`, `/workers` but the FastAPI app mounts all routers under `/api` prefix.
**Fix:** Updated all test URLs in `tests/test_api.py` to include the `/api` prefix (e.g., `/api/health`, `/api/tasks`).
**Result:** 50/50 tests now pass.

### 2. Dockerfiles Used Poetry (Build Failure)
**Problem:** `Dockerfile.api` and `Dockerfile.worker` installed Poetry and ran `poetry export` to generate requirements.txt. But the project doesn't use Poetry — it uses pip with a plain `requirements.txt` file and hatchling build backend. No `poetry.lock` file exists.
**Fix:** Replaced Poetry installation and export steps with simple `COPY requirements.txt` + `pip install`.

### 3. Nginx Proxy Stripping API Prefix (404s in Production)
**Problem:** `nginx.conf` used `proxy_pass http://api_backend/;` (with trailing slash) which strips the `/api/` prefix from requests. The backend expects routes at `/api/tasks`, `/api/queues`, etc., but nginx was forwarding to `/tasks`, `/queues` — resulting in 404s.
**Fix:** Changed to `proxy_pass http://api_backend;` (no trailing slash) to preserve the full URI path. Applied same fix to WebSocket proxy.

### 4. Frontend Dockerfile Wrong Port (Health Check Failing)
**Problem:** `Dockerfile.frontend` had `EXPOSE 3000` and health check on port 3000, but `nginx.conf` listens on port 8080.
**Fix:** Changed to `EXPOSE 8080` and updated health check URL to `http://localhost:8080/`.

### 5. Docker Compose Dev Overrides Invalid
**Problem:** `docker-compose.dev.yml` had deprecated `version: "3.9"` key, redundant build config that overrode the base, and the development frontend service lacked `networks: - taskqueue-network`.
**Fix:** Removed `version` key, removed redundant `build` section from `api` override, added network config to frontend dev service.

### 6. API Health Check Dockerfile URL
**Problem:** `Dockerfile.api` health check pointed to `/health` instead of `/api/health`.
**Fix:** Updated to `/api/health`.

---

## Testing Strategy

| Test File         | Tests | Coverage Area                                        |
|-------------------|-------|------------------------------------------------------|
| `test_api.py`     | 13    | Health check, task CRUD, queue stats, worker list, error handling |
| `test_broker.py`  | 19    | Enqueue, dequeue, priority ordering, task ops, queue stats, task model serialization |
| `test_worker.py`  | 13    | Worker init, handler registration, task processing, retry behavior, worker state |

All tests use `fakeredis` (in-memory Redis mock) and `httpx` ASGI transport for zero-infrastructure testing.

---

## Production Deployment

### Docker Services
| Service          | Port  | Description                              |
|------------------|-------|------------------------------------------|
| `redis`          | 6379  | Redis 7 with AOF persistence             |
| `api`            | 8000  | FastAPI with Uvicorn                     |
| `worker-1`       | —     | Processes `default`, `emails` queues     |
| `worker-2`       | —     | Processes `default`, `images` queues     |
| `worker-3`       | —     | Processes `default`, `data` queues       |
| `frontend`       | 8080  | Nginx serving React SPA + API proxy      |

### Development Extras
| Service            | Port  | Description                            |
|--------------------|-------|----------------------------------------|
| `frontend-dev`     | 3000  | Vite dev server with HMR              |
| `redis-commander`  | 8081  | Redis GUI for debugging               |

### Vercel (Serverless)
The API can also deploy as a Vercel serverless function via `api/index.py`, with routes rewritten through `vercel.json`. Requires `REDIS_URL` environment variable pointing to a cloud Redis instance.
