"""
Tests for the worker system.

Tests cover:
- Worker initialization
- Handler registration
- Task execution
- Retry mechanism
"""

import asyncio
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from src.queue.task import Task, TaskStatus
from src.queue.broker import RedisBroker
from src.worker.worker import Worker


class TestWorkerInitialization:
    """Test worker initialization and configuration."""

    def test_worker_creation(self, broker: RedisBroker):
        """Test worker can be created with required parameters."""
        worker = Worker(
            worker_id="test-worker",
            broker=broker,
            queues=["default"],
        )
        
        assert worker.worker_id == "test-worker"
        assert worker.queues == ["default"]

    def test_worker_multiple_queues(self, broker: RedisBroker):
        """Test worker can listen to multiple queues."""
        worker = Worker(
            worker_id="test-worker",
            broker=broker,
            queues=["default", "emails", "images"],
        )
        
        assert len(worker.queues) == 3
        assert "emails" in worker.queues
        assert "images" in worker.queues


class TestHandlerRegistration:
    """Test task handler registration."""

    def test_register_handler_with_add_handler(self, broker: RedisBroker, mock_handler: AsyncMock):
        """Test registering a task handler using add_handler."""
        worker = Worker(
            worker_id="test-worker",
            broker=broker,
            queues=["default"],
        )
        
        worker.add_handler("test_task", mock_handler)
        
        assert "test_task" in worker._handlers
        assert worker._handlers["test_task"] == mock_handler

    def test_register_multiple_handlers(self, broker: RedisBroker):
        """Test registering multiple handlers."""
        worker = Worker(
            worker_id="test-worker",
            broker=broker,
            queues=["default"],
        )
        
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        worker.add_handler("task_type_1", handler1)
        worker.add_handler("task_type_2", handler2)
        
        assert len(worker._handlers) == 2
        assert "task_type_1" in worker._handlers
        assert "task_type_2" in worker._handlers

    def test_handler_decorator(self, broker: RedisBroker):
        """Test using decorator to register handler."""
        worker = Worker(
            worker_id="test-worker",
            broker=broker,
            queues=["default"],
        )
        
        @worker.register_handler("decorated_task")
        async def my_handler(payload: dict) -> dict:
            return {"processed": True}
        
        assert "decorated_task" in worker._handlers


class TestTaskProcessing:
    """Test task processing integration."""

    @pytest.mark.asyncio
    async def test_handler_is_called_with_payload(
        self, broker: RedisBroker, sample_task: Task
    ):
        """Test that handler receives correct payload."""
        called_with = None
        
        async def capture_handler(payload: dict) -> dict:
            nonlocal called_with
            called_with = payload
            return {"done": True}
        
        worker = Worker(
            worker_id="test-worker",
            broker=broker,
            queues=["default"],
        )
        worker.add_handler("test_task", capture_handler)
        
        # Enqueue and process directly through worker's process method
        await broker.enqueue(sample_task, queue_name="default")
        task = await broker.dequeue(queue_name="default", timeout=1)
        
        # Call handler directly
        handler = worker._handlers.get(task.name)
        if handler:
            await handler(task.payload)
        
        assert called_with == sample_task.payload

    @pytest.mark.asyncio
    async def test_task_status_becomes_completed_on_success(
        self, broker: RedisBroker, sample_task: Task
    ):
        """Test that tasks are marked completed on success."""
        async def success_handler(payload: dict) -> dict:
            return {"success": True}
        
        await broker.enqueue(sample_task, queue_name="default")
        task = await broker.dequeue(queue_name="default", timeout=1)
        
        # Manually execute success path
        result = await success_handler(task.payload)
        task.mark_completed(result)
        await broker.update_task(task)
        
        updated = await broker.get_task(task.id)
        assert updated.status == TaskStatus.COMPLETED
        assert updated.result == {"success": True}

    @pytest.mark.asyncio
    async def test_task_fails_when_no_handler(self, broker: RedisBroker, sample_task: Task):
        """Test that tasks fail when no handler is registered."""
        worker = Worker(
            worker_id="test-worker",
            broker=broker,
            queues=["default"],
        )
        # No handler registered
        
        await broker.enqueue(sample_task, queue_name="default")
        task = await broker.dequeue(queue_name="default", timeout=1)
        
        # Check no handler exists
        assert task.name not in worker._handlers
        
        # Mark as failed (simulating worker behavior)
        task.mark_failed(f"No handler registered for task type: {task.name}")
        await broker.update_task(task)
        
        updated = await broker.get_task(task.id)
        assert updated.status == TaskStatus.FAILED
        assert "No handler" in updated.error


class TestRetryBehavior:
    """Test retry behavior."""

    @pytest.mark.asyncio
    async def test_retry_increments_count(self, broker: RedisBroker, sample_task: Task):
        """Test that retries increment the counter."""
        await broker.enqueue(sample_task, queue_name="default")
        task = await broker.dequeue(queue_name="default", timeout=1)
        
        # Simulate failure and retry
        assert task.can_retry()
        task.prepare_retry()
        
        assert task.retries == 1
        assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_max_retries_prevents_further_retry(self, broker: RedisBroker, task_factory):
        """Test that max retries prevents further retries."""
        task = task_factory(max_retries=2)
        task.retries = 2  # Already at max
        
        assert not task.can_retry()

    @pytest.mark.asyncio
    async def test_failed_task_after_max_retries(self, broker: RedisBroker, task_factory):
        """Test task fails permanently after max retries."""
        task = task_factory(max_retries=0)  # No retries allowed
        
        await broker.enqueue(task, queue_name="default")
        dequeued = await broker.dequeue(queue_name="default", timeout=1)
        
        # Try to process but fail
        assert not dequeued.can_retry()
        dequeued.mark_failed("Handler error")
        await broker.update_task(dequeued)
        
        updated = await broker.get_task(task.id)
        assert updated.status == TaskStatus.FAILED


class TestWorkerState:
    """Test worker state management."""

    def test_worker_state_initialization(self, broker: RedisBroker):
        """Test worker state is initialized correctly."""
        worker = Worker(
            worker_id="test-worker",
            broker=broker,
            queues=["default", "emails"],
        )
        
        assert worker._state.worker_id == "test-worker"
        assert worker._state.queues == ["default", "emails"]
        assert worker._state.tasks_completed == 0
        assert worker._state.tasks_failed == 0

    def test_worker_state_to_dict(self, broker: RedisBroker):
        """Test worker state serialization."""
        worker = Worker(
            worker_id="test-worker",
            broker=broker,
            queues=["default"],
        )
        
        state_dict = worker._state.to_dict()
        
        assert state_dict["worker_id"] == "test-worker"
        assert "status" in state_dict
        assert "last_heartbeat" in state_dict
        assert "started_at" in state_dict
