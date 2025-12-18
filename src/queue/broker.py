"""
Redis message broker for the distributed task queue.

This module provides the RedisBroker class that handles all interactions
with Redis for queue operations, including enqueueing, dequeueing,
and task status management using Redis sorted sets for priority queuing.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import redis.asyncio as redis
from redis.asyncio import Redis

from src.config import Settings, get_settings
from src.logging_config import get_logger
from src.queue.task import Task, TaskStatus

# Get module logger
logger = get_logger(__name__)


@dataclass
class QueueStats:
    """
    Statistics for a task queue.

    Attributes:
        queue_name: Name of the queue.
        pending: Number of tasks waiting to be processed.
        processing: Number of tasks currently being processed.
        completed: Number of successfully completed tasks.
        failed: Number of failed tasks.
        total: Total number of tasks in the queue.
    """

    queue_name: str
    pending: int
    processing: int
    completed: int
    failed: int

    @property
    def total(self) -> int:
        """Total number of tasks across all statuses."""
        return self.pending + self.processing + self.completed + self.failed


class RedisBroker:
    """
    Redis-backed message broker for the distributed task queue.

    This broker uses Redis sorted sets (ZADD/BZPOPMIN) to implement
    priority-based task queuing. Higher priority tasks (higher score)
    are processed first.

    Key Naming Convention:
        - queue:{queue_name}:pending - Sorted set for pending tasks (by priority)
        - queue:{queue_name}:processing - Set of task IDs being processed
        - queue:{queue_name}:completed - Set of completed task IDs
        - queue:{queue_name}:failed - Set of failed task IDs
        - task:{task_id} - Hash containing task data

    Attributes:
        settings: Application settings containing Redis configuration.
        _client: Redis async client instance (None until connected).

    Example:
        >>> settings = get_settings()
        >>> broker = RedisBroker(settings)
        >>> await broker.connect()
        >>>
        >>> # Enqueue a task
        >>> task = Task.create(name="process", payload={"key": "value"})
        >>> await broker.enqueue(task, priority=7)
        >>>
        >>> # Dequeue highest priority task
        >>> task = await broker.dequeue()
        >>> if task:
        ...     # Process and update
        ...     task.mark_completed(result={"success": True})
        ...     await broker.update_task(task)
        >>>
        >>> await broker.disconnect()
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """
        Initialize the Redis broker.

        Args:
            settings: Application settings. If None, loads from environment.
        """
        self.settings = settings or get_settings()
        self._client: Optional[Redis] = None
        self._log = logger.bind(component="RedisBroker")

    @property
    def client(self) -> Redis:
        """
        Get the Redis client, ensuring connection is established.

        Returns:
            The connected Redis client.

        Raises:
            RuntimeError: If not connected to Redis.
        """
        if self._client is None:
            raise RuntimeError(
                "Not connected to Redis. Call connect() first."
            )
        return self._client

    async def connect(self) -> None:
        """
        Establish connection to Redis server.

        Creates an async Redis client and verifies connectivity
        by sending a PING command.

        Raises:
            redis.ConnectionError: If unable to connect to Redis.

        Example:
            >>> broker = RedisBroker()
            >>> await broker.connect()
            >>> # Broker is now ready for operations
        """
        self._log.info("Connecting to Redis", url=self.settings.redis_url)

        self._client = redis.from_url(
            self.settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

        # Verify connection
        await self._client.ping()
        self._log.info("Successfully connected to Redis")

    async def disconnect(self) -> None:
        """
        Close the Redis connection.

        Safely closes the Redis client connection if one exists.

        Example:
            >>> await broker.disconnect()
        """
        if self._client:
            self._log.info("Disconnecting from Redis")
            await self._client.aclose()
            self._client = None
            self._log.info("Disconnected from Redis")

    def _queue_key(self, queue_name: str, status: str) -> str:
        """
        Generate a Redis key for a queue and status combination.

        Args:
            queue_name: Name of the queue.
            status: Status category (pending, processing, completed, failed).

        Returns:
            Redis key string.
        """
        return f"queue:{queue_name}:{status}"

    def _task_key(self, task_id: UUID) -> str:
        """
        Generate a Redis key for storing task data.

        Args:
            task_id: The task's unique identifier.

        Returns:
            Redis key string.
        """
        return f"task:{task_id}"

    async def enqueue(
        self,
        task: Task,
        queue_name: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> Task:
        """
        Add a task to the queue with the specified priority.

        Uses Redis sorted sets (ZADD) to maintain priority ordering.
        Higher priority values result in earlier processing.

        Args:
            task: The task to enqueue.
            queue_name: Name of the queue. Defaults to settings.default_queue.
            priority: Override the task's priority (1-10). If None, uses task.priority.

        Returns:
            The enqueued task (with potentially updated priority).

        Raises:
            ValueError: If priority is not between 1 and 10.
            RuntimeError: If not connected to Redis.

        Example:
            >>> task = Task.create(name="send_email", payload={"to": "user@example.com"})
            >>> await broker.enqueue(task, priority=8)
        """
        queue_name = queue_name or self.settings.default_queue
        task_priority = priority if priority is not None else task.priority

        if not 1 <= task_priority <= 10:
            raise ValueError(f"Priority must be between 1 and 10, got {task_priority}")

        # Update task priority if overridden
        if priority is not None:
            task.priority = priority

        self._log.info(
            "Enqueueing task",
            task_id=str(task.id),
            task_name=task.name,
            queue=queue_name,
            priority=task_priority,
        )

        # Store task data
        task_key = self._task_key(task.id)
        await self.client.set(task_key, task.to_json())

        # Add to pending sorted set with priority as score
        # Using negative priority so higher priority = lower score = popped first
        pending_key = self._queue_key(queue_name, "pending")
        await self.client.zadd(pending_key, {str(task.id): -task_priority})

        self._log.debug(
            "Task enqueued successfully",
            task_id=str(task.id),
            queue=queue_name,
        )

        return task

    async def dequeue(
        self,
        queue_name: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Optional[Task]:
        """
        Remove and return the highest priority task from the queue.

        Uses BZPOPMIN for blocking pop with timeout. Tasks are moved
        from pending to processing status atomically.

        Args:
            queue_name: Name of the queue. Defaults to settings.default_queue.
            timeout: Blocking timeout in seconds. Defaults to settings.task_timeout.
                Use 0 for non-blocking, None for infinite wait.

        Returns:
            The highest priority task, or None if timeout expires.

        Raises:
            RuntimeError: If not connected to Redis.

        Example:
            >>> task = await broker.dequeue(timeout=30)
            >>> if task:
            ...     print(f"Processing: {task.name}")
        """
        queue_name = queue_name or self.settings.default_queue
        wait_timeout = timeout if timeout is not None else self.settings.task_timeout

        pending_key = self._queue_key(queue_name, "pending")
        processing_key = self._queue_key(queue_name, "processing")

        self._log.debug(
            "Waiting for task",
            queue=queue_name,
            timeout=wait_timeout,
        )

        # Blocking pop from sorted set (lowest score = highest priority)
        result = await self.client.bzpopmin(pending_key, timeout=wait_timeout)

        if result is None:
            self._log.debug("Dequeue timeout, no tasks available", queue=queue_name)
            return None

        # result is (key, member, score)
        _, task_id_str, _ = result
        task_id = UUID(task_id_str)

        # Retrieve task data
        task_key = self._task_key(task_id)
        task_json = await self.client.get(task_key)

        if task_json is None:
            self._log.error(
                "Task data not found",
                task_id=str(task_id),
                queue=queue_name,
            )
            return None

        task = Task.from_json(task_json)

        # Mark as processing
        task.mark_processing()
        await self.client.set(task_key, task.to_json())

        # Add to processing set
        await self.client.sadd(processing_key, str(task.id))

        self._log.info(
            "Task dequeued",
            task_id=str(task.id),
            task_name=task.name,
            queue=queue_name,
            priority=task.priority,
        )

        return task

    async def get_task(self, task_id: UUID) -> Optional[Task]:
        """
        Retrieve a task by its ID.

        Args:
            task_id: The unique identifier of the task.

        Returns:
            The task if found, None otherwise.

        Raises:
            RuntimeError: If not connected to Redis.

        Example:
            >>> task = await broker.get_task(UUID("12345678-1234-..."))
            >>> if task:
            ...     print(f"Task status: {task.status}")
        """
        task_key = self._task_key(task_id)
        task_json = await self.client.get(task_key)

        if task_json is None:
            self._log.debug("Task not found", task_id=str(task_id))
            return None

        return Task.from_json(task_json)

    async def update_task(
        self,
        task: Task,
        queue_name: Optional[str] = None,
    ) -> Task:
        """
        Update a task's data in Redis and manage queue membership.

        This method updates the task data and moves it between queue
        sets based on its status (processing -> completed/failed).

        Args:
            task: The task with updated data.
            queue_name: Name of the queue. Defaults to settings.default_queue.

        Returns:
            The updated task.

        Raises:
            RuntimeError: If not connected to Redis.

        Example:
            >>> task.mark_completed(result={"rows": 100})
            >>> await broker.update_task(task)
        """
        queue_name = queue_name or self.settings.default_queue

        self._log.info(
            "Updating task",
            task_id=str(task.id),
            status=task.status.value,
            queue=queue_name,
        )

        # Update task data
        task_key = self._task_key(task.id)
        await self.client.set(task_key, task.to_json())

        processing_key = self._queue_key(queue_name, "processing")

        # Move from processing to final status set if completed or failed
        if task.status == TaskStatus.COMPLETED:
            completed_key = self._queue_key(queue_name, "completed")
            await self.client.smove(processing_key, completed_key, str(task.id))
            self._log.info(
                "Task completed",
                task_id=str(task.id),
                duration=task.duration,
            )

        elif task.status == TaskStatus.FAILED:
            failed_key = self._queue_key(queue_name, "failed")
            await self.client.smove(processing_key, failed_key, str(task.id))
            self._log.warning(
                "Task failed",
                task_id=str(task.id),
                error=task.error,
                retries=task.retries,
            )

        elif task.status == TaskStatus.PENDING:
            # Task is being retried - remove from processing and re-enqueue
            await self.client.srem(processing_key, str(task.id))
            pending_key = self._queue_key(queue_name, "pending")
            await self.client.zadd(pending_key, {str(task.id): -task.priority})
            self._log.info(
                "Task requeued for retry",
                task_id=str(task.id),
                retries=task.retries,
                max_retries=task.max_retries,
            )

        return task

    async def retry_task(
        self,
        task: Task,
        queue_name: Optional[str] = None,
    ) -> Optional[Task]:
        """
        Attempt to retry a failed or processing task.

        If the task can be retried (hasn't exceeded max_retries),
        it will be prepared for retry and re-enqueued.

        Args:
            task: The task to retry.
            queue_name: Name of the queue. Defaults to settings.default_queue.

        Returns:
            The task prepared for retry, or None if max retries exceeded.

        Raises:
            RuntimeError: If not connected to Redis.

        Example:
            >>> if task.can_retry():
            ...     task = await broker.retry_task(task)
        """
        if not task.can_retry():
            self._log.warning(
                "Task cannot be retried, max retries exceeded",
                task_id=str(task.id),
                retries=task.retries,
                max_retries=task.max_retries,
            )
            return None

        task.prepare_retry()
        await self.update_task(task, queue_name)

        self._log.info(
            "Task prepared for retry",
            task_id=str(task.id),
            retry_count=task.retries,
        )

        return task

    async def get_queue_stats(self, queue_name: Optional[str] = None) -> QueueStats:
        """
        Get statistics for a queue.

        Returns counts of tasks in each status category for the specified queue.

        Args:
            queue_name: Name of the queue. Defaults to settings.default_queue.

        Returns:
            QueueStats object with pending, processing, completed, and failed counts.

        Raises:
            RuntimeError: If not connected to Redis.

        Example:
            >>> stats = await broker.get_queue_stats()
            >>> print(f"Pending: {stats.pending}, Processing: {stats.processing}")
        """
        queue_name = queue_name or self.settings.default_queue

        pending_key = self._queue_key(queue_name, "pending")
        processing_key = self._queue_key(queue_name, "processing")
        completed_key = self._queue_key(queue_name, "completed")
        failed_key = self._queue_key(queue_name, "failed")

        # Get counts for each status
        pending_count = await self.client.zcard(pending_key)
        processing_count = await self.client.scard(processing_key)
        completed_count = await self.client.scard(completed_key)
        failed_count = await self.client.scard(failed_key)

        stats = QueueStats(
            queue_name=queue_name,
            pending=pending_count,
            processing=processing_count,
            completed=completed_count,
            failed=failed_count,
        )

        self._log.debug(
            "Queue stats retrieved",
            queue=queue_name,
            pending=stats.pending,
            processing=stats.processing,
            completed=stats.completed,
            failed=stats.failed,
            total=stats.total,
        )

        return stats

    async def get_pending_tasks(
        self,
        queue_name: Optional[str] = None,
        limit: int = 100,
    ) -> list[Task]:
        """
        Get a list of pending tasks in priority order.

        Args:
            queue_name: Name of the queue. Defaults to settings.default_queue.
            limit: Maximum number of tasks to return.

        Returns:
            List of pending tasks, ordered by priority (highest first).

        Raises:
            RuntimeError: If not connected to Redis.

        Example:
            >>> pending = await broker.get_pending_tasks(limit=10)
            >>> for task in pending:
            ...     print(f"{task.name}: priority {task.priority}")
        """
        queue_name = queue_name or self.settings.default_queue
        pending_key = self._queue_key(queue_name, "pending")

        # Get task IDs from sorted set (ordered by score/priority)
        task_ids = await self.client.zrange(pending_key, 0, limit - 1)

        tasks = []
        for task_id_str in task_ids:
            task = await self.get_task(UUID(task_id_str))
            if task:
                tasks.append(task)

        return tasks

    async def clear_queue(
        self,
        queue_name: Optional[str] = None,
        include_completed: bool = False,
    ) -> int:
        """
        Clear all tasks from a queue.

        By default, only clears pending and failed tasks. Set include_completed
        to True to also clear completed tasks.

        Args:
            queue_name: Name of the queue. Defaults to settings.default_queue.
            include_completed: Whether to also clear completed tasks.

        Returns:
            Number of tasks cleared.

        Raises:
            RuntimeError: If not connected to Redis.

        Example:
            >>> cleared = await broker.clear_queue(include_completed=True)
            >>> print(f"Cleared {cleared} tasks")
        """
        queue_name = queue_name or self.settings.default_queue

        keys_to_clear = [
            self._queue_key(queue_name, "pending"),
            self._queue_key(queue_name, "processing"),
            self._queue_key(queue_name, "failed"),
        ]

        if include_completed:
            keys_to_clear.append(self._queue_key(queue_name, "completed"))

        total_cleared = 0

        for key in keys_to_clear:
            # Get all task IDs before clearing
            if "pending" in key:
                task_ids = await self.client.zrange(key, 0, -1)
            else:
                task_ids = await self.client.smembers(key)

            # Delete task data
            for task_id in task_ids:
                task_key = self._task_key(UUID(task_id))
                await self.client.delete(task_key)
                total_cleared += 1

            # Clear the set/sorted set
            await self.client.delete(key)

        self._log.info(
            "Queue cleared",
            queue=queue_name,
            tasks_cleared=total_cleared,
            include_completed=include_completed,
        )

        return total_cleared

    async def health_check(self) -> bool:
        """
        Check if the Redis connection is healthy.

        Returns:
            True if connected and responsive, False otherwise.

        Example:
            >>> if await broker.health_check():
            ...     print("Redis connection is healthy")
        """
        try:
            await self.client.ping()
            return True
        except Exception as e:
            self._log.error("Health check failed", error=str(e))
            return False

    async def __aenter__(self) -> "RedisBroker":
        """Async context manager entry - connects to Redis."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - disconnects from Redis."""
        await self.disconnect()
