# Distributed Task Queue

A production-ready distributed task queue system with priority scheduling, automatic retries, and real-time monitoring dashboard.

## Overview

This project implements a scalable task queue architecture where tasks can be submitted via REST API, processed by distributed workers, and monitored through a real-time web dashboard. Built for high performance and reliability with features like priority-based scheduling, automatic retries with exponential backoff, and dead letter queues.

## Features

### Core Functionality
- **Priority-based Scheduling**: Tasks are processed by priority (1-10, higher priority first)
- **Automatic Retries**: Failed tasks automatically retry with configurable exponential backoff
- **Dead Letter Queue**: Failed tasks after max retries are moved to DLQ for analysis
- **Real-time Monitoring**: WebSocket-powered dashboard with live task updates
- **Multiple Task Types**: Built-in handlers for email, data processing, and image processing

### Technical Features
- **High Performance**: Redis sorted sets for O(log N) enqueue/dequeue operations
- **Graceful Shutdown**: Workers properly finish current tasks before stopping
- **Health Checks**: Built-in health endpoints for monitoring
- **Structured Logging**: JSON-formatted logs for easy parsing and analysis
- **Docker Ready**: Multi-stage builds and docker-compose for easy deployment

## Architecture

### Components

1. **FastAPI Server**: REST API for task submission and monitoring
2. **Redis Broker**: Message queue and task storage using sorted sets
3. **Workers**: Distributed workers that poll queues and execute tasks
4. **React Dashboard**: Real-time UI for monitoring tasks, queues, and workers

### Task Flow

1. Client submits task to API → Task stored in Redis → Added to priority queue
2. Worker polls queue → Gets highest priority task → Executes handler
3. On success: Task marked complete → WebSocket notification sent
4. On failure: Retry count incremented → Requeued or moved to DLQ

## Tech Stack

**Backend**
- Python 3.11+
- FastAPI (REST API)
- Redis (Message Broker)
- Pydantic (Data Validation)

**Frontend**
- React 18
- TypeScript
- Vite
- TailwindCSS
- WebSocket (Real-time updates)

**Infrastructure**
- Docker & Docker Compose
- Nginx (Production)

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### Quick Start with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access the application
# Dashboard: http://localhost
# API Docs: http://localhost:8000/docs
```

### Development Setup

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up

# The frontend will be available at http://localhost:5173
# API at http://localhost:8000
```

## API Usage

### Submit a Task

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "email",
    "payload": {"to": "user@example.com", "subject": "Hello"},
    "priority": 5
  }'
```

### Get Task Status

```bash
curl http://localhost:8000/api/tasks/{task_id}
```

### List Tasks

```bash
curl http://localhost:8000/api/tasks?status=pending&limit=10
```

## Task Handlers

### Built-in Handlers

1. **Email Handler** (`email`): Simulates sending emails
2. **Data Handler** (`data`): Processes data transformations
3. **Image Handler** (`image`): Handles image processing tasks

### Adding Custom Handlers

Create a new handler in `src/worker/handlers/`:

```python
from src.worker.handlers import register_handler

@register_handler("my_task")
async def my_task_handler(payload: dict) -> dict:
    # Your task logic here
    return {"status": "success"}
```

## Testing

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/test_api.py
```

## Deployment

### Vercel Deployment (Production)

This application can be deployed to Vercel for the frontend and API. **Important**: Workers must be deployed separately as Vercel uses serverless functions.

📚 **[Complete Vercel Deployment Guide](VERCEL_DEPLOYMENT.md)**

Quick steps:
1. Set up a cloud Redis instance (Upstash recommended)
2. Configure `REDIS_URL` in Vercel environment variables
3. Deploy to Vercel (automatic via GitHub)
4. Run workers on a separate server (VPS, Docker, etc.)

See [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md) for detailed instructions.

### Recent Production Fixes

✅ Fixed "unknown error" issues in production
✅ Added missing dependencies for Vercel
✅ Improved error messages for debugging
✅ Added comprehensive deployment documentation

See [PRODUCTION_FIXES.md](PRODUCTION_FIXES.md) for details on what was fixed.

## Testing

### Automated Tests
```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/test_api.py
```

### Manual Testing
See [TESTING_GUIDE.md](TESTING_GUIDE.md) for step-by-step testing instructions including:
- Local testing with Docker
- Production testing on Vercel
- Common issues and solutions

## Project Structure

```
.
├── src/
│   ├── api/           # FastAPI application
│   ├── queue/         # Queue and broker logic
│   └── worker/        # Worker implementation
├── frontend/          # React dashboard
├── tests/             # Test suite
├── docker/            # Docker configurations
├── docs/              # Documentation and guides
├── VERCEL_DEPLOYMENT.md      # Vercel deployment guide
├── PRODUCTION_FIXES.md       # Recent fixes and improvements
├── TESTING_GUIDE.md          # Manual testing instructions
└── docker-compose.yml # Service orchestration
```

## Documentation

- **[Vercel Deployment Guide](VERCEL_DEPLOYMENT.md)** - Deploy to production
- **[Production Fixes](PRODUCTION_FIXES.md)** - Recent bug fixes and improvements
- **[Testing Guide](TESTING_GUIDE.md)** - How to test locally and in production
- **[Beginner Guide](docs/BEGINNER_GUIDE.md)** - Learn the concepts
- **[Learning Path](docs/LEARNING_PATH.md)** - Study roadmap
- **[Interview Prep](docs/INTERVIEW_PREP.md)** - Interview questions
- **[Project Deep Dive](docs/PROJECT_DEEP_DIVE.md)** - Architecture details

## License

MIT
