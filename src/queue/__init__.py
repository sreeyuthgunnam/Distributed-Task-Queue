"""
Queue module for the distributed task queue system.

This module provides the core components for task queue management:
- Task: Data model representing a task in the queue
- TaskStatus: Enumeration of possible task states
- RedisBroker: Redis-backed message broker for queue operations

Example:
    >>> from src.queue import Task, TaskStatus, RedisBroker
    >>> from src.config import get_settings
    >>>
    >>> # Create a broker and connect
    >>> broker = RedisBroker(get_settings())
    >>> await broker.connect()
    >>>
    >>> # Create and enqueue a task
    >>> task = Task.create(name="process_data", payload={"file": "data.csv"})
    >>> await broker.enqueue(task, priority=5)
    >>>
    >>> # Dequeue and process
    >>> task = await broker.dequeue()
    >>> if task:
    ...     # Process task
    ...     task.mark_completed(result={"rows_processed": 1000})
    ...     await broker.update_task(task)
"""

from src.queue.task import Task, TaskStatus
from src.queue.broker import RedisBroker

__all__ = ["Task", "TaskStatus", "RedisBroker"]
