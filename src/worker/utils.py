"""
Utility functions for the worker module.

This module provides helper functions for worker operations,
including worker discovery, health checks, and statistics.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from src.queue import RedisBroker
from src.worker.worker import Worker, WorkerState, WorkerStatus
from src.logging_config import get_logger

logger = get_logger(__name__)


async def get_active_workers(
    broker: RedisBroker,
    timeout_seconds: int = 30,
) -> list[WorkerState]:
    """
    Get all workers that have sent a heartbeat within the timeout period.

    Args:
        broker: RedisBroker instance.
        timeout_seconds: Consider workers inactive if no heartbeat within this time.

    Returns:
        List of active WorkerState objects.

    Example:
        >>> active = await get_active_workers(broker, timeout_seconds=60)
        >>> print(f"Active workers: {len(active)}")
    """
    all_workers = await Worker.get_all_workers(broker)
    now = datetime.now(timezone.utc)
    timeout = timedelta(seconds=timeout_seconds)

    active_workers = [
        w for w in all_workers
        if (now - w.last_heartbeat) < timeout
    ]

    return active_workers


async def get_stale_workers(
    broker: RedisBroker,
    timeout_seconds: int = 30,
) -> list[WorkerState]:
    """
    Get workers that haven't sent a heartbeat within the timeout period.

    These workers may have crashed or lost connection and their tasks
    may need to be recovered.

    Args:
        broker: RedisBroker instance.
        timeout_seconds: Consider workers stale if no heartbeat within this time.

    Returns:
        List of stale WorkerState objects.

    Example:
        >>> stale = await get_stale_workers(broker, timeout_seconds=60)
        >>> for w in stale:
        ...     print(f"Stale worker: {w.worker_id}")
    """
    all_workers = await Worker.get_all_workers(broker)
    now = datetime.now(timezone.utc)
    timeout = timedelta(seconds=timeout_seconds)

    stale_workers = [
        w for w in all_workers
        if (now - w.last_heartbeat) >= timeout
    ]

    return stale_workers


async def cleanup_stale_workers(
    broker: RedisBroker,
    timeout_seconds: int = 60,
) -> int:
    """
    Remove stale workers from Redis.

    This function cleans up worker state for workers that haven't
    sent heartbeats within the timeout period.

    Args:
        broker: RedisBroker instance.
        timeout_seconds: Consider workers stale if no heartbeat within this time.

    Returns:
        Number of stale workers cleaned up.

    Example:
        >>> cleaned = await cleanup_stale_workers(broker)
        >>> print(f"Cleaned up {cleaned} stale workers")
    """
    stale_workers = await get_stale_workers(broker, timeout_seconds)

    for worker in stale_workers:
        worker_key = f"worker:{worker.worker_id}"
        await broker.client.delete(worker_key)
        await broker.client.srem("workers:active", worker.worker_id)

        logger.info(
            "Cleaned up stale worker",
            worker_id=worker.worker_id,
            last_heartbeat=worker.last_heartbeat.isoformat(),
        )

    return len(stale_workers)


async def get_worker_statistics(broker: RedisBroker) -> dict:
    """
    Get aggregate statistics for all workers.

    Args:
        broker: RedisBroker instance.

    Returns:
        Dictionary containing:
            - total_workers: Total number of registered workers
            - active_workers: Number of workers with recent heartbeat
            - idle_workers: Number of workers in idle state
            - busy_workers: Number of workers processing tasks
            - total_completed: Total tasks completed across all workers
            - total_failed: Total tasks failed across all workers

    Example:
        >>> stats = await get_worker_statistics(broker)
        >>> print(f"Active: {stats['active_workers']}, Busy: {stats['busy_workers']}")
    """
    all_workers = await Worker.get_all_workers(broker)
    active_workers = await get_active_workers(broker)

    idle_count = sum(
        1 for w in active_workers
        if w.status == WorkerStatus.IDLE
    )
    busy_count = sum(
        1 for w in active_workers
        if w.status == WorkerStatus.BUSY
    )

    total_completed = sum(w.tasks_completed for w in all_workers)
    total_failed = sum(w.tasks_failed for w in all_workers)

    return {
        "total_workers": len(all_workers),
        "active_workers": len(active_workers),
        "idle_workers": idle_count,
        "busy_workers": busy_count,
        "total_completed": total_completed,
        "total_failed": total_failed,
    }


async def recover_orphaned_tasks(
    broker: RedisBroker,
    queue_name: str,
    timeout_seconds: int = 60,
) -> int:
    """
    Recover tasks from stale workers by moving them back to pending.

    This function checks for tasks that were being processed by workers
    that have gone stale and moves them back to the pending queue.

    Args:
        broker: RedisBroker instance.
        queue_name: Name of the queue to check.
        timeout_seconds: Consider workers stale if no heartbeat within this time.

    Returns:
        Number of tasks recovered.

    Example:
        >>> recovered = await recover_orphaned_tasks(broker, "default")
        >>> print(f"Recovered {recovered} orphaned tasks")
    """
    stale_workers = await get_stale_workers(broker, timeout_seconds)

    recovered_count = 0

    for worker in stale_workers:
        if worker.current_task:
            try:
                from uuid import UUID
                from src.queue import Task, TaskStatus

                task = await broker.get_task(UUID(worker.current_task))

                if task and task.status == TaskStatus.PROCESSING:
                    # Move task back to pending
                    task.status = TaskStatus.PENDING
                    task.started_at = None

                    # Update task in Redis
                    task_key = f"task:{task.id}"
                    await broker.client.set(task_key, task.to_json())

                    # Move from processing to pending set
                    processing_key = f"queue:{queue_name}:processing"
                    pending_key = f"queue:{queue_name}:pending"

                    await broker.client.srem(processing_key, str(task.id))
                    await broker.client.zadd(
                        pending_key,
                        {str(task.id): -task.priority}
                    )

                    recovered_count += 1

                    logger.info(
                        "Recovered orphaned task",
                        task_id=str(task.id),
                        worker_id=worker.worker_id,
                    )

            except Exception as e:
                logger.error(
                    "Failed to recover task",
                    task_id=worker.current_task,
                    error=str(e),
                )

    return recovered_count
