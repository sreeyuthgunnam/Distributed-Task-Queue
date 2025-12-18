"""
Worker module for the distributed task queue system.

This module provides the Worker class for processing tasks from the queue,
along with utilities for handler registration and worker management.

Example:
    >>> from src.worker import Worker
    >>> from src.queue import RedisBroker
    >>>
    >>> broker = RedisBroker()
    >>> worker = Worker(worker_id="worker-1", queues=["default"], broker=broker)
    >>>
    >>> @worker.register_handler("send_email")
    >>> async def handle_email(payload):
    ...     # Process email task
    ...     return {"sent": True}
    >>>
    >>> await worker.start()
"""

from src.worker.worker import Worker, WorkerStatus, WorkerState

__all__ = ["Worker", "WorkerStatus", "WorkerState"]
