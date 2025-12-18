"""
Worker implementation for the distributed task queue.

This module provides the Worker class that polls queues, executes tasks
with registered handlers, manages retries with exponential backoff,
and maintains worker status in Redis.
"""

import asyncio
import signal
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Optional
from uuid import UUID

from src.config import Settings, get_settings
from src.logging_config import get_logger
from src.queue import RedisBroker, Task, TaskStatus

# Type alias for task handler functions
TaskHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]

# Get module logger
logger = get_logger(__name__)


class WorkerStatus(str, Enum):
    """
    Enumeration of possible worker states.

    Attributes:
        IDLE: Worker is waiting for tasks.
        BUSY: Worker is currently processing a task.
        STARTING: Worker is initializing.
        STOPPING: Worker is shutting down gracefully.
        STOPPED: Worker has stopped.
    """

    IDLE = "idle"
    BUSY = "busy"
    STARTING = "starting"
    STOPPING = "stopping"
    STOPPED = "stopped"

    def __str__(self) -> str:
        """Return the string value of the status."""
        return self.value


@dataclass
class WorkerState:
    """
    Represents the current state of a worker.

    This state is stored in Redis for monitoring and coordination.

    Attributes:
        worker_id: Unique identifier for the worker.
        status: Current worker status (idle/busy/starting/stopping/stopped).
        current_task: ID of the task currently being processed (None if idle).
        current_task_name: Name of the current task (None if idle).
        last_heartbeat: Timestamp of the last heartbeat.
        tasks_completed: Total number of tasks completed by this worker.
        tasks_failed: Total number of tasks that failed.
        started_at: Timestamp when the worker started.
        queues: List of queues this worker is processing.
    """

    worker_id: str
    status: WorkerStatus = WorkerStatus.STARTING
    current_task: Optional[str] = None
    current_task_name: Optional[str] = None
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tasks_completed: int = 0
    tasks_failed: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    queues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert worker state to a dictionary for Redis storage."""
        return {
            "worker_id": self.worker_id,
            "status": self.status.value,
            "current_task": self.current_task,
            "current_task_name": self.current_task_name,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "started_at": self.started_at.isoformat(),
            "queues": self.queues,
        }

    def to_json(self) -> str:
        """Serialize worker state to JSON."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkerState":
        """Create a WorkerState from a dictionary."""
        return cls(
            worker_id=data["worker_id"],
            status=WorkerStatus(data["status"]),
            current_task=data.get("current_task"),
            current_task_name=data.get("current_task_name"),
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]),
            tasks_completed=data.get("tasks_completed", 0),
            tasks_failed=data.get("tasks_failed", 0),
            started_at=datetime.fromisoformat(data["started_at"]),
            queues=data.get("queues", []),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "WorkerState":
        """Create a WorkerState from a JSON string."""
        return cls.from_dict(json.loads(json_str))


class Worker:
    """
    Task worker that processes tasks from the distributed queue.

    The Worker polls configured queues for tasks, executes them using
    registered handlers, and manages task lifecycle including retries
    with exponential backoff.

    Features:
    - Multiple queue support with priority ordering
    - Concurrent task processing (configurable concurrency)
    - Exponential backoff retry mechanism
    - Dead letter queue for failed tasks
    - Graceful shutdown handling
    - Heartbeat for health monitoring

    Attributes:
        worker_id: Unique identifier for this worker instance.
        queues: List of queue names to process (in priority order).
        broker: RedisBroker instance for queue operations.
        concurrency: Number of concurrent tasks to process.
        settings: Application settings.

    Example:
        >>> worker = Worker(
        ...     worker_id="worker-1",
        ...     queues=["high-priority", "default"],
        ...     broker=broker,
        ...     concurrency=2,
        ... )
        >>>
        >>> @worker.register_handler("send_email")
        >>> async def handle_email(payload):
        ...     await send_email(**payload)
        ...     return {"sent": True}
        >>>
        >>> await worker.start()
    """

    # Constants for retry backoff
    BASE_RETRY_DELAY: float = 1.0  # Base delay in seconds
    MAX_RETRY_DELAY: float = 300.0  # Maximum delay (5 minutes)

    # Heartbeat interval
    HEARTBEAT_INTERVAL: float = 10.0  # seconds

    # Dead letter queue suffix
    DLQ_SUFFIX: str = ":dlq"

    def __init__(
        self,
        worker_id: str,
        queues: list[str],
        broker: RedisBroker,
        concurrency: int = 1,
        settings: Optional[Settings] = None,
    ) -> None:
        """
        Initialize the worker.

        Args:
            worker_id: Unique identifier for this worker instance.
            queues: List of queue names to process (in priority order).
            broker: RedisBroker instance for queue operations.
            concurrency: Number of concurrent tasks to process (default: 1).
            settings: Application settings. If None, loads from environment.
        """
        self.worker_id = worker_id
        self.queues = queues
        self.broker = broker
        self.concurrency = concurrency
        self.settings = settings or get_settings()

        # Handler registry: task_name -> handler_function
        self._handlers: dict[str, TaskHandler] = {}

        # Worker state
        self._state = WorkerState(
            worker_id=worker_id,
            queues=queues,
        )

        # Control flags
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Background tasks
        self._worker_tasks: list[asyncio.Task] = []
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Logger with worker context
        self._log = logger.bind(
            worker_id=worker_id,
            queues=queues,
            concurrency=concurrency,
        )

    def register_handler(
        self,
        task_name: str,
    ) -> Callable[[TaskHandler], TaskHandler]:
        """
        Decorator to register a task handler function.

        The handler function should be an async function that accepts
        a payload dictionary and returns a result dictionary.

        Args:
            task_name: The name of the task type this handler processes.

        Returns:
            Decorator function that registers the handler.

        Example:
            >>> @worker.register_handler("process_order")
            >>> async def handle_order(payload):
            ...     order_id = payload["order_id"]
            ...     # Process the order
            ...     return {"status": "processed", "order_id": order_id}
        """

        def decorator(handler: TaskHandler) -> TaskHandler:
            self._handlers[task_name] = handler
            self._log.info(
                "Registered task handler",
                task_name=task_name,
                handler=handler.__name__,
            )
            return handler

        return decorator

    def add_handler(self, task_name: str, handler: TaskHandler) -> None:
        """
        Register a task handler function directly (non-decorator style).

        Args:
            task_name: The name of the task type this handler processes.
            handler: Async function that processes the task payload.

        Example:
            >>> async def my_handler(payload):
            ...     return {"result": "done"}
            >>> worker.add_handler("my_task", my_handler)
        """
        self._handlers[task_name] = handler
        self._log.info(
            "Registered task handler",
            task_name=task_name,
            handler=handler.__name__,
        )

    async def start(self) -> None:
        """
        Start the worker and begin processing tasks.

        This method starts the main processing loop and heartbeat.
        It will run until graceful_shutdown() is called or a signal
        is received.

        The worker processes tasks from configured queues in priority
        order, executing registered handlers for each task type.

        Example:
            >>> await worker.start()  # Blocks until shutdown
        """
        self._log.info("Starting worker")
        self._running = True
        self._shutdown_event.clear()

        # Update initial state
        self._state.status = WorkerStatus.IDLE
        self._state.started_at = datetime.now(timezone.utc)
        await self._update_state()

        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(),
            name=f"heartbeat-{self.worker_id}",
        )

        # Start worker tasks based on concurrency
        for i in range(self.concurrency):
            task = asyncio.create_task(
                self._process_loop(i),
                name=f"worker-{self.worker_id}-{i}",
            )
            self._worker_tasks.append(task)

        self._log.info(
            "Worker started",
            concurrency=self.concurrency,
            handlers=list(self._handlers.keys()),
        )

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        # Wait for all tasks to complete
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Final state update
        self._state.status = WorkerStatus.STOPPED
        self._state.current_task = None
        self._state.current_task_name = None
        await self._update_state()

        self._log.info(
            "Worker stopped",
            tasks_completed=self._state.tasks_completed,
            tasks_failed=self._state.tasks_failed,
        )

    async def graceful_shutdown(self) -> None:
        """
        Initiate graceful shutdown of the worker.

        This method signals the worker to stop accepting new tasks
        and finish processing current tasks before shutting down.

        Example:
            >>> await worker.graceful_shutdown()
        """
        self._log.info("Initiating graceful shutdown")
        self._running = False
        self._state.status = WorkerStatus.STOPPING
        await self._update_state()

        # Signal shutdown
        self._shutdown_event.set()

    async def _process_loop(self, worker_index: int) -> None:
        """
        Main processing loop for a worker task.

        Continuously polls queues for tasks and processes them
        until shutdown is requested.

        Args:
            worker_index: Index of this worker task (for logging).
        """
        log = self._log.bind(worker_index=worker_index)
        log.debug("Processing loop started")

        while self._running:
            try:
                # Poll each queue in priority order
                task = await self._poll_queues()

                if task is None:
                    # No tasks available, short sleep before retry
                    await asyncio.sleep(0.1)
                    continue

                # Process the task
                await self._process_task(task)

            except asyncio.CancelledError:
                log.debug("Processing loop cancelled")
                break
            except Exception as e:
                log.error("Error in processing loop", error=str(e), exc_info=True)
                await asyncio.sleep(1)  # Brief pause before retrying

        log.debug("Processing loop stopped")

    async def _poll_queues(self) -> Optional[Task]:
        """
        Poll configured queues for available tasks.

        Polls queues in order (first queue has highest priority).
        Uses a short timeout to allow checking other queues.

        Returns:
            The next task to process, or None if no tasks available.
        """
        for queue_name in self.queues:
            try:
                # Short timeout for responsive polling
                task = await self.broker.dequeue(
                    queue_name=queue_name,
                    timeout=1,  # 1 second timeout
                )
                if task:
                    return task
            except Exception as e:
                self._log.error(
                    "Error polling queue",
                    queue=queue_name,
                    error=str(e),
                )

        return None

    async def _process_task(self, task: Task) -> None:
        """
        Process a single task.

        Executes the registered handler for the task type,
        handles timeouts, updates task status, and manages retries.

        Args:
            task: The task to process.
        """
        log = self._log.bind(
            task_id=str(task.id),
            task_name=task.name,
            retry=task.retries,
        )

        # Update worker state
        self._state.status = WorkerStatus.BUSY
        self._state.current_task = str(task.id)
        self._state.current_task_name = task.name
        await self._update_state()

        log.info("Processing task")

        # Get handler for task type
        handler = self._handlers.get(task.name)

        if handler is None:
            log.error("No handler registered for task type")
            task.mark_failed(error=f"No handler registered for task type: {task.name}")
            await self._handle_task_failure(task)
            # Reset worker state
            self._state.status = WorkerStatus.IDLE
            self._state.current_task = None
            self._state.current_task_name = None
            await self._update_state()
            return

        try:
            # Execute handler with timeout
            result = await asyncio.wait_for(
                handler(task.payload),
                timeout=self.settings.task_timeout,
            )

            # Task completed successfully
            task.mark_completed(result=result)
            await self.broker.update_task(task)

            self._state.tasks_completed += 1
            log.info(
                "Task completed successfully",
                duration=task.duration,
                result_keys=list(result.keys()) if result else None,
            )

        except asyncio.TimeoutError:
            log.error(
                "Task timed out",
                timeout=self.settings.task_timeout,
            )
            task.mark_failed(error=f"Task timed out after {self.settings.task_timeout}s")
            await self._handle_task_failure(task)

        except Exception as e:
            log.error("Task failed with exception", error=str(e), exc_info=True)
            task.mark_failed(error=str(e))
            await self._handle_task_failure(task)

        finally:
            # Reset worker state
            self._state.status = WorkerStatus.IDLE
            self._state.current_task = None
            self._state.current_task_name = None
            await self._update_state()

    async def _handle_task_failure(self, task: Task) -> None:
        """
        Handle a failed task, implementing retry logic.

        If the task can be retried, schedules it with exponential backoff.
        Otherwise, moves it to the dead letter queue.

        Args:
            task: The failed task.
        """
        log = self._log.bind(
            task_id=str(task.id),
            task_name=task.name,
            retries=task.retries,
            max_retries=task.max_retries,
        )

        self._state.tasks_failed += 1

        if task.can_retry():
            # Calculate exponential backoff delay
            delay = self._calculate_retry_delay(task.retries)
            log.info(
                "Scheduling task retry",
                retry_count=task.retries + 1,
                delay_seconds=delay,
            )

            # Prepare task for retry
            task.prepare_retry()
            await self.broker.update_task(task)

            # Note: In a production system, you might want to use
            # Redis delayed queue or separate retry scheduler
            # For simplicity, we just re-enqueue immediately
            # The actual delay would be handled by a retry scheduler

        else:
            # Move to dead letter queue
            log.warning(
                "Task exceeded max retries, moving to dead letter queue",
                error=task.error,
            )
            # First update the task status to move it from processing to failed in the original queue
            await self.broker.update_task(task)
            # Then move a copy to DLQ for later analysis
            await self._move_to_dlq(task)

    def _calculate_retry_delay(self, retry_count: int) -> float:
        """
        Calculate exponential backoff delay for retry.

        Uses formula: min(base_delay * 2^retry_count, max_delay)

        Args:
            retry_count: Current retry attempt number (0-based).

        Returns:
            Delay in seconds before next retry.
        """
        delay = self.BASE_RETRY_DELAY * (2 ** retry_count)
        return min(delay, self.MAX_RETRY_DELAY)

    async def _move_to_dlq(self, task: Task) -> None:
        """
        Move a failed task to the dead letter queue.

        The dead letter queue stores tasks that have failed all
        retry attempts for later analysis or manual intervention.

        Args:
            task: The failed task to move to DLQ.
        """
        # Determine original queue (use first configured queue as default)
        original_queue = self.queues[0] if self.queues else self.settings.default_queue
        dlq_name = f"{original_queue}{self.DLQ_SUFFIX}"

        # Store task in DLQ (as a regular enqueue, but to DLQ)
        # Reset status to failed for DLQ storage
        dlq_key = f"queue:{dlq_name}:failed"
        task_key = f"task:{task.id}"

        await self.broker.client.set(task_key, task.to_json())
        await self.broker.client.sadd(dlq_key, str(task.id))

        self._log.info(
            "Task moved to dead letter queue",
            task_id=str(task.id),
            dlq=dlq_name,
        )

    async def _heartbeat_loop(self) -> None:
        """
        Background task that sends periodic heartbeats.

        Updates the worker state in Redis every HEARTBEAT_INTERVAL seconds
        to indicate the worker is alive and healthy.
        """
        self._log.debug("Heartbeat loop started")

        while self._running:
            try:
                await self.heartbeat()
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log.error("Heartbeat error", error=str(e))
                await asyncio.sleep(1)

        self._log.debug("Heartbeat loop stopped")

    async def heartbeat(self) -> None:
        """
        Send a heartbeat to Redis.

        Updates the last_heartbeat timestamp in the worker state
        stored in Redis.

        Example:
            >>> await worker.heartbeat()
        """
        self._state.last_heartbeat = datetime.now(timezone.utc)
        await self._update_state()
        self._log.debug("Heartbeat sent")

    async def _update_state(self) -> None:
        """
        Update the worker state in Redis.

        Stores the current WorkerState as JSON in Redis under
        the key 'worker:{worker_id}'.
        """
        worker_key = f"worker:{self.worker_id}"
        await self.broker.client.set(worker_key, self._state.to_json())

        # Also add to workers set for discovery
        await self.broker.client.sadd("workers:active", self.worker_id)

    async def _remove_state(self) -> None:
        """
        Remove the worker state from Redis.

        Called during shutdown to clean up worker registration.
        """
        worker_key = f"worker:{self.worker_id}"
        await self.broker.client.delete(worker_key)
        await self.broker.client.srem("workers:active", self.worker_id)

    @property
    def state(self) -> WorkerState:
        """Get the current worker state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if the worker is currently running."""
        return self._running

    @classmethod
    async def get_worker_state(
        cls,
        broker: RedisBroker,
        worker_id: str,
    ) -> Optional[WorkerState]:
        """
        Retrieve a worker's state from Redis.

        Class method to fetch any worker's state for monitoring.

        Args:
            broker: RedisBroker instance.
            worker_id: ID of the worker to query.

        Returns:
            WorkerState if found, None otherwise.

        Example:
            >>> state = await Worker.get_worker_state(broker, "worker-1")
            >>> if state:
            ...     print(f"Status: {state.status}")
        """
        worker_key = f"worker:{worker_id}"
        state_json = await broker.client.get(worker_key)

        if state_json is None:
            return None

        return WorkerState.from_json(state_json)

    @classmethod
    async def get_all_workers(cls, broker: RedisBroker) -> list[WorkerState]:
        """
        Get the state of all active workers.

        Class method to fetch all registered workers for monitoring.

        Args:
            broker: RedisBroker instance.

        Returns:
            List of WorkerState objects for all active workers.

        Example:
            >>> workers = await Worker.get_all_workers(broker)
            >>> for w in workers:
            ...     print(f"{w.worker_id}: {w.status}")
        """
        worker_ids = await broker.client.smembers("workers:active")
        workers = []

        for worker_id in worker_ids:
            state = await cls.get_worker_state(broker, worker_id)
            if state:
                workers.append(state)

        return workers
