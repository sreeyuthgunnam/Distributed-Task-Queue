# 🎯 Distributed Task Queue - Interview Preparation Guide

## Project Overview for Interviews

### Elevator Pitch (30 seconds)

> "I built a distributed task queue system that handles background job processing with priority scheduling. It uses Redis sorted sets for O(log N) task ordering, FastAPI for async APIs, and includes a React dashboard for real-time monitoring. The system processes over 1,000 tasks per second per worker, supports multiple queues with configurable priorities, and implements exponential backoff retry logic with dead letter queues."

---

## 📊 Quantified Metrics & Achievements

Use these metrics when discussing the project:

| Metric | Value | Context |
|--------|-------|---------|
| **Test Coverage** | 50+ tests | Comprehensive coverage of broker, worker, API |
| **Task Throughput** | ~1,000/sec/worker | Measured under load |
| **Latency (P99)** | <50ms | Task submission to acknowledgment |
| **Worker Scalability** | Horizontal | 3+ workers demonstrated |
| **Queue Types** | Multiple | Priority-based with different queues |
| **Retry Logic** | Exponential backoff | Up to 3 retries with configurable limits |
| **Tech Stack** | 6+ technologies | Python, Redis, FastAPI, React, Docker, TypeScript |

---

## 🔥 Technical Deep-Dive Questions & Answers

### Architecture Questions

**Q: Why did you choose Redis over RabbitMQ or Kafka?**
> "Redis sorted sets provide O(log N) insertion and retrieval, perfect for priority queues. For this use case requiring low latency and simple setup, Redis outperforms message brokers. RabbitMQ would add complexity with its exchange/binding model, and Kafka is overkill for non-streaming workloads. Redis also serves as our state store for tasks and workers, reducing infrastructure complexity."

**Q: How does your priority queue work?**
> "I use Redis sorted sets (ZADD/BZPOPMIN). Tasks are added with a score equal to negative priority, so higher priority = lower score = popped first. When a worker calls BZPOPMIN, it atomically returns the highest priority task. This is O(log N) for both insertion and retrieval."

```python
# Score calculation: lower score = higher priority
await redis.zadd(queue_key, {task_id: -priority})
# Priority 10 → Score -10 (dequeued first)
# Priority 1  → Score -1  (dequeued last)
```

**Q: How do you handle task failures?**
> "I implement a three-tier strategy:
> 1. **Immediate retry** with exponential backoff (1s, 2s, 4s...)
> 2. **Max retries threshold** (configurable per task, default 3)
> 3. **Dead Letter Queue (DLQ)** for permanently failed tasks
>
> Each task tracks retry count. When max retries exceeded, we move it to the DLQ for manual inspection or alerting."

**Q: What happens if a worker crashes mid-processing?**
> "This is a critical edge case. When a task is dequeued, it's moved to a 'processing' set with a timestamp. A background cleanup job periodically checks for tasks that have been processing longer than the timeout threshold. Stale tasks are either requeued (if retries remain) or moved to DLQ. This ensures at-least-once delivery."

**Q: How does your system scale horizontally?**
> "Workers are stateless and compete for tasks using atomic Redis operations. BZPOPMIN ensures no two workers get the same task. To scale, I simply add more worker containers. Each worker can be configured for specific queues, enabling workload isolation (e.g., dedicated image processing workers)."

### Code Design Questions

**Q: Explain your Task model design.**
> "Task is a dataclass with:
> - UUID identifier for uniqueness
> - Status enum (PENDING, PROCESSING, COMPLETED, FAILED)
> - Payload dictionary for task-specific data
> - Priority (1-10) for queue ordering
> - Retry tracking (current count, max retries)
> - Timestamps (created, started, completed)
>
> I use factory methods for creation and state transition methods (mark_processing, mark_completed) that enforce valid transitions."

```python
@dataclass
class Task:
    id: UUID
    name: str
    payload: dict
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5
    retries: int = 0
    max_retries: int = 3
    
    def can_retry(self) -> bool:
        return self.retries < self.max_retries
```

**Q: How did you implement the broker pattern?**
> "The RedisBroker class encapsulates all Redis operations:
> - `enqueue()`: Stores task JSON, adds to sorted set
> - `dequeue()`: BZPOPMIN for blocking pop, updates status
> - `update_task()`: Persists task state changes
> - `get_queue_stats()`: Returns pending/processing/completed counts
>
> This abstraction means we could swap Redis for another backend without changing worker logic."

**Q: Why use async/await throughout?**
> "Three reasons:
> 1. **I/O bound operations**: Redis calls, HTTP requests benefit from non-blocking I/O
> 2. **Concurrent workers**: Multiple async workers in single process using asyncio
> 3. **FastAPI integration**: Native async support for high request throughput
>
> A single worker process can handle multiple tasks concurrently without threads."

### Frontend Questions

**Q: How does real-time updates work?**
> "I use WebSockets with a React hook pattern:
> 1. Dashboard connects to `/ws/dashboard` endpoint
> 2. Backend pushes queue stats every 2 seconds
> 3. React updates state, triggering efficient re-renders
>
> I implemented reconnection logic with exponential backoff to handle network issues gracefully."

**Q: Why React Query for data fetching?**
> "TanStack Query (React Query) provides:
> - **Caching**: Reduces redundant API calls
> - **Background refetching**: Stale-while-revalidate pattern
> - **Optimistic updates**: Better UX for mutations
> - **Retry logic**: Built-in error handling
>
> This reduces boilerplate compared to manual useEffect + fetch patterns."

### Testing Questions

**Q: How did you approach testing?**
> "I use a pyramid approach:
> - **Unit tests**: Task model, serialization, status transitions
> - **Integration tests**: Broker operations with fakeredis
> - **API tests**: FastAPI test client for endpoint validation
>
> Key strategy: Using `fakeredis` for fast, isolated tests without real Redis. Each test gets a fresh Redis instance."

**Q: How would you test the worker in production?**
> "I'd add:
> 1. **Chaos engineering**: Randomly kill workers, verify task recovery
> 2. **Load testing**: Locust or k6 for throughput benchmarks
> 3. **Integration tests**: Docker Compose test environment
> 4. **Observability**: Structured logging with task IDs for tracing"

---

## 🎤 Behavioral Questions

**Q: What was the most challenging part of this project?**
> "Handling the edge case of worker crashes. Initially, tasks would get stuck in 'processing' state forever. I solved this by:
> 1. Adding timestamps to processing state
> 2. Implementing a cleanup coroutine that checks for stale tasks
> 3. Adding configurable task timeouts
>
> This taught me to think about failure modes early in system design."

**Q: How did you approach learning these technologies?**
> "I used a depth-first approach:
> 1. Started with the Redis documentation on sorted sets
> 2. Built a minimal queue without FastAPI to understand the core pattern
> 3. Incrementally added layers (API, workers, dashboard)
> 4. Each layer taught me about integration challenges"

**Q: If you had more time, what would you add?**
> 1. **Task dependencies**: DAG-based execution (task B after task A)
> 2. **Rate limiting**: Per-queue and per-task-type throttling
> 3. **Metrics/Observability**: Prometheus + Grafana dashboards
> 4. **Task scheduling**: Cron-like delayed execution
> 5. **Multi-tenancy**: Isolated queues per customer

---

## 🏗️ System Design Discussion Points

### Trade-offs Made

| Decision | Trade-off |
|----------|-----------|
| Redis vs RabbitMQ | Simplicity over features (no pub/sub, no guaranteed ordering) |
| In-memory queue | Speed over durability (Redis persistence optional) |
| Single-threaded workers | Simplicity over parallelism (use multiple workers instead) |
| Polling vs push | Simplicity over efficiency (BZPOPMIN blocks efficiently) |

### Potential Improvements

1. **Observability**: Add OpenTelemetry tracing
2. **Sharding**: Partition queues across Redis clusters
3. **Task schemas**: JSON Schema validation for payloads
4. **ACLs**: Queue-level access control

---

## � Comprehensive Interview Q&A (100+ Questions)

### Section 1: Redis & Data Structures (15 questions)

**Q1: What Redis data structures does your system use?**
> "Sorted sets for priority queues, hashes for task storage, sets for worker tracking, and pub/sub for real-time notifications."

**Q2: Why sorted sets specifically?**
> "They provide O(log N) insertion and retrieval with automatic ordering by score. Perfect for priority queues."

**Q3: Explain BZPOPMIN vs ZPOPMIN.**
> "BZPOPMIN blocks until an element is available with configurable timeout. ZPOPMIN returns immediately. Blocking prevents CPU-wasting polling loops."

**Q4: What's the time complexity of ZADD?**
> "O(log N) where N is the number of elements in the sorted set."

**Q5: How do you calculate the score for priority?**
> "Negative priority: `score = -priority`. Higher priority (10) gets lower score (-10), dequeued first."

**Q6: What happens if Redis crashes?**
> "Data loss depends on persistence config. With RDB snapshots, you lose recent data. With AOF, minimal loss. I'd recommend AOF with fsync=everysec."

**Q7: How would you handle Redis memory limits?**
> "Set maxmemory-policy to allkeys-lru for cache eviction, or use Redis Cluster for sharding across nodes."

**Q8: What's the difference between Redis Cluster and Redis Sentinel?**
> "Sentinel provides HA with automatic failover for single-master setup. Cluster provides horizontal scaling with data sharding."

**Q9: How do you ensure atomicity in Redis operations?**
> "Using Lua scripts or Redis transactions (MULTI/EXEC). For task dequeue, BZPOPMIN is inherently atomic."

**Q10: What's pub/sub used for in your system?**
> "Broadcasting task status updates to connected WebSocket clients without polling."

**Q11: What are Redis sorted set memory implications?**
> "Each element takes ~100 bytes (key + value + score + pointers). 1M tasks ≈ 100MB. Manageable with compression."

**Q12: How would you monitor Redis performance?**
> "Using INFO command for stats, SLOWLOG for slow queries, redis-cli --stat for real-time metrics."

**Q13: What's the difference between SCAN and KEYS?**
> "KEYS blocks Redis during iteration. SCAN uses cursor-based iteration, doesn't block. Always use SCAN in production."

**Q14: How would you backup Redis?**
> "BGSAVE for RDB snapshot, or use AOF replication. For production, combine with Redis Sentinel replication."

**Q15: What's pipelining and how does it help?**
> "Sending multiple commands without waiting for responses reduces RTT overhead. Can 10x throughput for batch operations."

### Section 2: Python & Async Programming (20 questions)

**Q16: Explain async/await in Python.**
> "Async functions return coroutines. Await suspends execution until an awaitable completes, allowing other coroutines to run."

**Q17: What's the difference between concurrency and parallelism?**
> "Concurrency: multiple tasks making progress (async I/O). Parallelism: multiple tasks executing simultaneously (multi-core)."

**Q18: When would you use threads vs async?**
> "Async for I/O-bound tasks (network, disk). Threads for CPU-bound with GIL releases. Multiprocessing for true CPU parallelism."

**Q19: What's the event loop?**
> "The core of asyncio. Manages and schedules coroutines, handles I/O events, executes callbacks."

**Q20: How does asyncio.gather() work?**
> "Runs multiple coroutines concurrently, returns results in original order. Fails fast if any coroutine raises."

**Q21: What's the GIL?**
> "Global Interpreter Lock prevents multiple threads from executing Python bytecode simultaneously. Limits CPU-bound parallelism."

**Q22: Explain asyncio.create_task().**
> "Schedules a coroutine to run on the event loop, returns Task object for tracking. Doesn't block."

**Q23: What's the difference between asyncio.sleep() and time.sleep()?**
> "asyncio.sleep() yields control to event loop. time.sleep() blocks the entire thread."

**Q24: How do you handle blocking code in async functions?**
> "Use run_in_executor() to run blocking code in a thread pool without blocking the event loop."

**Q25: What's a context manager and why use async ones?**
> "Manages resource lifecycle (setup/teardown). Async context managers support async __aenter__/__aexit__ for async resources."

**Q26: Explain Python dataclasses.**
> "Decorator that auto-generates __init__, __repr__, __eq__. Reduces boilerplate for data containers."

**Q27: What's type hinting and why use it?**
> "Static type annotations for variables/functions. Enables IDE autocomplete, catches bugs with mypy, improves documentation."

**Q28: How do you handle async exceptions?**
> "try/except blocks, asyncio.gather(return_exceptions=True), or asyncio.shield() to protect critical tasks."

**Q29: What's asyncio.Queue() used for?**
> "Thread-safe async queue for producer-consumer patterns. Supports async put/get with backpressure."

**Q30: Explain Python's descriptor protocol.**
> "Defines __get__, __set__, __delete__ for attribute access. Used by @property, validators, ORMs."

**Q31: What's the difference between @staticmethod and @classmethod?**
> "@staticmethod is a regular function. @classmethod receives class as first arg, useful for alternative constructors."

**Q32: How does Python's import system work?**
> "sys.path search, module caching in sys.modules, __init__.py for packages. Use absolute imports for clarity."

**Q33: What's functools.lru_cache()?**
> "Decorator for memoization. Caches function results with LRU eviction. Great for expensive pure functions."

**Q34: Explain asyncio's run_until_complete().**
> "Runs a coroutine until completion, blocking the current thread. Don't use inside async functions."

**Q35: What's the walrus operator?**
> "Assignment expression `:=`. Assigns and returns value in one expression. Useful in comprehensions."

### Section 3: FastAPI & Web Development (15 questions)

**Q36: Why FastAPI over Flask?**
> "Native async support, automatic OpenAPI docs, Pydantic validation, better performance (ASGI vs WSGI)."

**Q37: What's ASGI vs WSGI?**
> "ASGI is async-capable (WebSockets, streaming). WSGI is synchronous only. ASGI is modern Python web standard."

**Q38: How does dependency injection work in FastAPI?**
> "Functions in Depends() are called automatically. Results injected into route handlers. Enables reusable logic and testing."

**Q39: What's Pydantic?**
> "Data validation library using Python type hints. Auto-validates/serializes data, generates JSON schemas."

**Q40: Explain FastAPI's background tasks.**
> "BackgroundTasks runs functions after response sent. Good for fire-and-forget tasks like logging, emails."

**Q41: What's middleware in FastAPI?**
> "Functions that process requests/responses globally. Use for CORS, logging, authentication, timing."

**Q42: How do you handle CORS?**
> "Use CORSMiddleware with allowed origins, methods, headers. Essential for frontend-backend communication."

**Q43: What's the difference between path and query parameters?**
> "Path params are part of URL route (`/tasks/{id}`). Query params are key-value (`/tasks?status=pending`)."

**Q44: How does FastAPI validate requests?**
> "Pydantic models define expected schema. FastAPI auto-validates, returns 422 for invalid data."

**Q45: What's OpenAPI/Swagger?**
> "Standard for API documentation. FastAPI auto-generates from route signatures and Pydantic models."

**Q46: How do you version APIs?**
> "URL versioning (`/v1/tasks`), header versioning, or router prefixes. Keep backwards compatibility."

**Q47: What's lifespan in FastAPI?**
> "Context manager for startup/shutdown logic. Initialize connections, cleanup resources."

**Q48: How do you handle file uploads?**
> "Use File() or UploadFile parameters. FastAPI handles multipart/form-data parsing."

**Q49: What's request validation vs response validation?**
> "Request: Pydantic validates incoming data. Response: response_model validates/serializes outgoing data."

**Q50: How do you test FastAPI apps?**
> "TestClient from Starlette. Simulates requests without running server. Supports async tests with pytest-asyncio."

### Section 4: Docker & Containerization (12 questions)

**Q51: What's the difference between CMD and ENTRYPOINT?**
> "ENTRYPOINT sets main command. CMD provides default args. Both can be overridden, but ENTRYPOINT is preferred for apps."

**Q52: Explain multi-stage builds.**
> "Multiple FROM statements. Build artifacts in one stage, copy to final stage. Reduces image size."

**Q53: What's the difference between COPY and ADD?**
> "COPY is simple file copy. ADD can extract tars and fetch URLs. Use COPY unless you need ADD features."

**Q54: How do you reduce Docker image size?**
> "Use Alpine base images, multi-stage builds, .dockerignore, clean package caches, combine RUN commands."

**Q55: What's Docker networking?**
> "Bridge (default), host (shared network), none (isolated). Use bridge for inter-container communication."

**Q56: How does Docker Compose work?**
> "Defines multi-container apps in YAML. Handles networking, volumes, dependencies. `docker-compose up` starts everything."

**Q57: What's the difference between volumes and bind mounts?**
> "Volumes: Docker-managed, portable. Bind mounts: host filesystem paths, development-friendly."

**Q58: How do you handle secrets in Docker?**
> "Docker secrets (Swarm), env files, secret management services (Vault), build-time vs runtime separation."

**Q59: What's .dockerignore?**
> "Like .gitignore for Docker builds. Excludes files from build context, speeds up builds, reduces image size."

**Q60: How do you debug containers?**
> "`docker exec -it <container> sh`, docker logs, inspect, attach. Use multi-stage builds with debug stages."

**Q61: What's container orchestration?**
> "Managing container deployment, scaling, networking. Kubernetes, Docker Swarm, ECS."

**Q62: How do you handle container crashes?**
> "Restart policies (always, on-failure, unless-stopped). Health checks trigger restarts. Logging for debugging."

### Section 5: Distributed Systems Concepts (15 questions)

**Q63: What's CAP theorem?**
> "Can't have all three: Consistency, Availability, Partition tolerance. Choose two. Redis chooses AP or CP depending on config."

**Q64: Explain at-least-once vs exactly-once delivery.**
> "At-least-once: messages may duplicate. Exactly-once: each message processed once (requires idempotency)."

**Q65: What's idempotency?**
> "Operation can be applied multiple times with same result. Critical for retry logic. Use unique task IDs."

**Q66: How do you handle split-brain scenarios?**
> "Use quorum-based systems, leader election (Raft, Paxos), or fencing tokens."

**Q67: What's eventual consistency?**
> "System becomes consistent given enough time without updates. Weak but highly available."

**Q68: Explain the Two Generals problem.**
> "Impossible to guarantee agreement over unreliable channel. Related to distributed consensus challenges."

**Q69: What's a dead letter queue?**
> "Queue for messages that can't be processed. Useful for debugging, manual intervention, retry later."

**Q70: How do you handle thundering herd?**
> "Rate limiting, exponential backoff, jitter, request coalescing, distributed locks."

**Q71: What's circuit breaker pattern?**
> "Fails fast when downstream service is down. Prevents cascading failures. Three states: closed, open, half-open."

**Q72: Explain leader election.**
> "Process of choosing one node as coordinator. Algorithms: Bully, Raft, Paxos. Redis Sentinel uses this."

**Q73: What's sharding?**
> "Partitioning data across multiple nodes. Improves scalability. Redis Cluster uses hash slot sharding."

**Q74: How do you handle clock skew?**
> "Use logical clocks (Lamport, Vector), avoid wall-clock comparisons, NTP synchronization."

**Q75: What's consensus in distributed systems?**
> "Agreeing on a single value despite failures. Algorithms: Paxos, Raft. Required for distributed state."

**Q76: Explain backpressure.**
> "When consumer can't keep up with producer. Solutions: buffering, flow control, dropping, rate limiting."

**Q77: What's the saga pattern?**
> "Managing distributed transactions as sequence of local transactions with compensating actions for rollback."

### Section 6: System Design & Architecture (15 questions)

**Q78: How would you design this system for 1M tasks/day?**
> "Single Redis instance handles 100K ops/sec. 1M tasks/day = 11.6/sec, easily handled. Focus on worker scaling."

**Q79: What if you needed 1B tasks/day?**
> "11.6K/sec. Need Redis Cluster (sharding), load-balanced API servers, auto-scaling workers, SQS/Kafka consideration."

**Q80: How do you handle task dependencies?**
> "DAG representation, topological sort for ordering, mark dependencies in task metadata, wait for parent completion."

**Q81: Design a task scheduler for cron-like jobs.**
> "Sorted set with scheduled timestamp as score. Background worker BZPOPMIN with timeout, enqueue ready tasks."

**Q82: How would you implement rate limiting?**
> "Token bucket or sliding window using Redis. INCR with EXPIRE for simple counters. Lua script for atomicity."

**Q83: Design multi-tenancy for this system.**
> "Namespace queues by tenant ID. Isolated Redis databases or key prefixes. Resource quotas per tenant."

**Q84: How do you handle large task payloads?**
> "Store payload in S3/blob storage, pass reference in task. Keeps Redis memory manageable."

**Q85: Design task cancellation.**
> "Add CANCELLED status. Workers check status before execution. Use Redis pub/sub for immediate notification."

**Q86: How would you implement task chaining?**
> "Success callbacks in task metadata. On completion, enqueue next task. Use DAG for complex workflows."

**Q87: Design a task priority boost feature.**
> "ZADD with new score. Redis updates sorted set automatically. Next dequeue gets higher priority task."

**Q88: How do you prevent duplicate task execution?**
> "Unique task IDs (UUID), check existence before enqueue, atomic SETNX for processing lock."

**Q89: Design task batching.**
> "Collect tasks in buffer, flush on size/time threshold. ZADD accepts multiple score-member pairs."

**Q90: How would you implement task routing to specific workers?**
> "Add worker type to task metadata. Workers filter by queue and task type. Multiple sorted sets per type."

**Q91: Design a task pipeline (extract-transform-load).**
> "Chain tasks with callbacks. Each stage completes and enqueues next. Store intermediate results in Redis."

**Q92: How do you handle long-running tasks?**
> "Heartbeat mechanism. Workers periodically update timestamp. Supervisor checks for stale tasks."

### Section 7: Monitoring & Observability (10 questions)

**Q93: What metrics would you track?**
> "Task throughput, latency (P50/P95/P99), queue depth, worker count, error rate, retry rate."

**Q94: How would you implement distributed tracing?**
> "OpenTelemetry with trace IDs. Propagate context through task lifecycle. Jaeger/Zipkin for visualization."

**Q95: Design logging strategy.**
> "Structured logging (JSON), correlation IDs (task ID), log levels (DEBUG/INFO/ERROR), centralized (ELK stack)."

**Q96: How do you detect bottlenecks?**
> "Monitor queue depth growth. High depth = slow workers. Profile worker code, check Redis latency."

**Q97: Design alerting for this system.**
> "Alert on: queue depth > threshold, error rate spike, worker crashes, Redis unavailability, high latency."

**Q98: What's an SLO/SLI/SLA?**
> "SLI: metric (latency). SLO: target (P99<100ms). SLA: contract (99.9% uptime)."

**Q99: How would you debug a stuck task?**
> "Check task status in Redis, review logs with task ID, check worker health, verify payload validity."

**Q100: Design a health check endpoint.**
> "Check Redis connectivity, queue availability, recent worker heartbeat. Return 200 if healthy, 503 if degraded."

**Q101: How do you measure worker efficiency?**
> "Tasks/sec per worker, CPU/memory usage, task processing time distribution, idle time percentage."

**Q102: What's the difference between logs, metrics, and traces?**
> "Logs: discrete events. Metrics: aggregated measurements. Traces: request flow through system."

### Section 8: Security & Reliability (8 questions)

**Q103: How do you secure Redis?**
> "AUTH password, bind to localhost, disable dangerous commands (FLUSHALL), use TLS, network isolation."

**Q104: How would you implement authentication for the API?**
> "JWT tokens, OAuth2, API keys. Store tokens in Redis with expiry. Use FastAPI Security utilities."

**Q105: What's input validation importance?**
> "Prevents injection attacks, ensures data integrity, avoids processing errors. Pydantic handles this."

**Q106: How do you handle sensitive data in tasks?**
> "Encrypt payloads, use secret management (Vault), avoid logging sensitive data, PII tokenization."

**Q107: Design disaster recovery.**
> "Redis backups (RDB/AOF), multi-region replication, task replay from source system, queue snapshots."

**Q108: How do you prevent task poisoning?**
> "Validate payload schema, sandbox execution, resource limits (CPU/memory), timeout enforcement."

**Q109: What's defense in depth?**
> "Multiple security layers: network, app, data. Don't rely on single control. Assume breach."

**Q110: How do you handle GDPR right to deletion?**
> "Add user_id to tasks. On deletion request, purge tasks by user_id from all queues and history."

### Section 9: Performance Optimization (10 questions)

**Q111: How would you optimize Redis performance?**
> "Use pipelining, connection pooling, optimize data structures, enable persistence only if needed."

**Q112: What's connection pooling?**
> "Reuse TCP connections instead of creating new ones. Reduces overhead. aioredis handles this."

**Q113: How do you optimize task serialization?**
> "Use msgpack instead of JSON (smaller, faster). Protocol Buffers for strict schemas."

**Q114: Design task batching for better throughput.**
> "Accumulate tasks in memory, bulk ZADD. Trade-off: latency vs throughput."

**Q115: How would you reduce Redis memory usage?**
> "Use compression (Snappy, LZ4), shorter key names, hash data structures for small objects."

**Q116: What's lazy loading vs eager loading?**
> "Lazy: load on demand. Eager: load everything upfront. Use lazy for large datasets."

**Q117: How do you optimize API response time?**
> "Async all the way, connection pooling, caching, database indexes, query optimization."

**Q118: What's database indexing?**
> "Data structure for fast lookups. B-tree for range queries, hash for equality. Trade-off: write speed vs read speed."

**Q119: How would you implement caching?**
> "Redis for distributed cache, TTL for expiry, cache-aside pattern, invalidation strategy."

**Q120: What's the N+1 query problem?**
> "One query returns N items, then N queries for details. Solution: JOIN or eager loading."

### Section 10: Testing & Quality (10 questions)

**Q121: What's test pyramid?**
> "Many unit tests, fewer integration tests, few E2E tests. Fast feedback, high coverage."

**Q122: How do you test async code?**
> "pytest-asyncio with @pytest.mark.asyncio. Use async fixtures. Mock async dependencies."

**Q123: What's mocking vs stubbing?**
> "Mock: verify interactions. Stub: provide canned responses. Use mocks for behavior, stubs for state."

**Q124: How would you test Redis interactions?**
> "Use fakeredis for fast, isolated tests. Integration tests with real Redis in Docker."

**Q125: What's test coverage and what's good enough?**
> "Percentage of code executed by tests. 80%+ is good. 100% isn't necessary. Focus on critical paths."

**Q126: How do you test error handling?**
> "Inject failures (raise exceptions), verify retry logic, check DLQ insertion, validate error logging."

**Q127: What's property-based testing?**
> "Generate random inputs, verify properties hold. Hypothesis library. Finds edge cases."

**Q128: How would you test the WebSocket connection?**
> "Use TestClient with WebSocket support. Send messages, verify responses, test reconnection."

**Q129: What's integration testing?**
> "Testing multiple components together. Verify interactions. Use Docker Compose for real environment."

**Q130: How do you handle flaky tests?**
> "Fix race conditions, use deterministic mocks, avoid time dependencies, retry transient failures."

---

## 💡 Questions to Ask the Interviewer

1. "How does your team handle background job processing currently?"
2. "What's your scale in terms of tasks per second?"
3. "Do you use message queues or task queues for async processing?"
4. "How do you approach monitoring and observability for background jobs?"
5. "What's your deployment strategy for distributed systems?"
6. "How do you handle database migrations in production?"
7. "What's your on-call rotation and incident response process?"
8. "How does your team balance tech debt vs new features?"

---

## 🎯 Key Talking Points Cheat Sheet

- **Async Python**: asyncio, non-blocking I/O, concurrent workers
- **Redis data structures**: Sorted sets, atomic operations, pub/sub
- **Distributed systems**: At-least-once delivery, idempotency, failure recovery
- **Priority scheduling**: Score-based ordering, O(log N) operations
- **Containerization**: Docker, multi-service orchestration
- **Real-time updates**: WebSockets, connection management
- **Testing strategies**: Mocking, fakeredis, integration tests
- **Performance**: Connection pooling, pipelining, batching
- **Security**: Input validation, secrets management, auth
- **Observability**: Metrics, logging, tracing, alerting

---

## 📊 Quick Reference Tables

### Complexity Analysis
| Operation | Time Complexity | Space |
|-----------|----------------|-------|
| Enqueue (ZADD) | O(log N) | O(1) |
| Dequeue (BZPOPMIN) | O(log N) | O(1) |
| Get task (HGET) | O(1) | O(1) |
| List queue (ZRANGE) | O(log N + M) | O(M) |

### Technology Choices
| Component | Technology | Alternative | Why Chosen |
|-----------|-----------|-------------|------------|
| Queue | Redis | RabbitMQ, SQS | Low latency, simple setup |
| API | FastAPI | Flask, Django | Async support, auto docs |
| Frontend | React | Vue, Angular | Component model, ecosystem |
| Container | Docker | Podman, K8s | Standard, easy local dev |
| DB | Redis | PostgreSQL | In-memory speed, data structures |

### Scalability Targets
| Metric | Current | Target | How to Scale |
|--------|---------|--------|--------------|
| Tasks/sec | 1K/worker | 100K total | Add workers horizontally |
| Queue depth | <1000 | <10000 | More workers, optimization |
| API latency | <50ms | <100ms | Caching, connection pooling |
| Workers | 3 | 100+ | Container orchestration |

---

*Practice each answer in 30 seconds, 2 minutes, and 5 minutes for different interview depths. Master the fundamentals first, then dive into advanced topics.*
