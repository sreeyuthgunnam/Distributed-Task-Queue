"""
Tests for the Redis broker operations.

Tests cover:
- Connection management
- Task enqueueing with priority
- Task dequeuing with blocking
- Priority ordering
- Task status updates
- Queue statistics
- Task retrieval
"""

import pytest
import pytest_asyncio
from datetime import datetime

from src.queue.task import Task, TaskStatus
from src.queue.broker import RedisBroker


class TestEnqueue:
    """Test task enqueueing operations."""

    @pytest.mark.asyncio
    async def test_enqueue_single_task(self, broker: RedisBroker, sample_task: Task):
        """Test enqueueing a single task."""
        await broker.enqueue(sample_task)
        
        # Verify task data is stored
        task_key = f"task:{sample_task.id}"
        task_data = await broker._client.get(task_key)
        assert task_data is not None

    @pytest.mark.asyncio
    async def test_enqueue_stores_task_data(self, broker: RedisBroker, sample_task: Task):
        """Test that task data is stored correctly in Redis."""
        await broker.enqueue(sample_task, queue_name="default")
        
        # Verify task can be retrieved
        retrieved = await broker.get_task(sample_task.id)
        assert retrieved is not None
        assert retrieved.id == sample_task.id
        assert retrieved.name == sample_task.name
        assert retrieved.payload == sample_task.payload

    @pytest.mark.asyncio
    async def test_enqueue_with_priority_override(self, broker: RedisBroker, sample_task: Task):
        """Test that priority can be overridden during enqueue."""
        await broker.enqueue(sample_task, queue_name="default", priority=9)
        
        retrieved = await broker.get_task(sample_task.id)
        assert retrieved.priority == 9

    @pytest.mark.asyncio
    async def test_enqueue_multiple_tasks(self, broker: RedisBroker, batch_tasks: list[Task]):
        """Test enqueueing multiple tasks."""
        for task in batch_tasks:
            await broker.enqueue(task, queue_name="default")
        
        # All tasks should be retrievable
        for task in batch_tasks:
            retrieved = await broker.get_task(task.id)
            assert retrieved is not None

    @pytest.mark.asyncio
    async def test_enqueue_to_different_queues(
        self, broker: RedisBroker, sample_task: Task, email_task: Task
    ):
        """Test enqueueing to different queues."""
        await broker.enqueue(sample_task, queue_name="default")
        await broker.enqueue(email_task, queue_name="emails")
        
        # Both tasks should be retrievable
        assert await broker.get_task(sample_task.id) is not None
        assert await broker.get_task(email_task.id) is not None


class TestDequeue:
    """Test task dequeuing operations."""

    @pytest.mark.asyncio
    async def test_dequeue_single_task(self, broker: RedisBroker, sample_task: Task):
        """Test dequeuing a single task."""
        await broker.enqueue(sample_task, queue_name="default")
        
        dequeued = await broker.dequeue(queue_name="default", timeout=1)
        
        assert dequeued is not None
        assert dequeued.id == sample_task.id
        assert dequeued.name == sample_task.name

    @pytest.mark.asyncio
    async def test_dequeue_updates_status_to_processing(self, broker: RedisBroker, sample_task: Task):
        """Test that dequeue updates task status to processing."""
        await broker.enqueue(sample_task, queue_name="default")
        
        dequeued = await broker.dequeue(queue_name="default", timeout=1)
        
        assert dequeued.status == TaskStatus.PROCESSING
        assert dequeued.started_at is not None

    @pytest.mark.asyncio
    async def test_dequeue_empty_queue_returns_none(self, broker: RedisBroker):
        """Test dequeuing from empty queue returns None."""
        dequeued = await broker.dequeue(queue_name="empty_queue", timeout=1)
        assert dequeued is None


class TestPriorityOrdering:
    """Test priority-based task ordering."""

    @pytest.mark.asyncio
    async def test_higher_priority_dequeued_first(
        self, broker: RedisBroker, high_priority_task: Task, low_priority_task: Task
    ):
        """Test that higher priority tasks are dequeued first."""
        # Enqueue low priority first, then high priority
        await broker.enqueue(low_priority_task, queue_name="default")
        await broker.enqueue(high_priority_task, queue_name="default")
        
        # Should get high priority task first
        first = await broker.dequeue(queue_name="default", timeout=1)
        assert first.id == high_priority_task.id
        assert first.priority == 10
        
        # Then low priority task
        second = await broker.dequeue(queue_name="default", timeout=1)
        assert second.id == low_priority_task.id
        assert second.priority == 1

    @pytest.mark.asyncio
    async def test_priority_ordering_multiple_tasks(
        self, broker: RedisBroker, batch_tasks: list[Task]
    ):
        """Test priority ordering with multiple tasks."""
        # Enqueue all tasks
        for task in batch_tasks:
            await broker.enqueue(task, queue_name="default")
        
        # Dequeue and verify they come out in priority order
        dequeued = []
        for _ in range(len(batch_tasks)):
            task = await broker.dequeue(queue_name="default", timeout=1)
            if task:
                dequeued.append(task)
        
        # Verify tasks are ordered by priority (descending)
        priorities = [t.priority for t in dequeued]
        assert priorities == sorted(priorities, reverse=True)


class TestTaskOperations:
    """Test task get/update operations."""

    @pytest.mark.asyncio
    async def test_get_task(self, broker: RedisBroker, sample_task: Task):
        """Test retrieving a task by ID."""
        await broker.enqueue(sample_task, queue_name="default")
        
        retrieved = await broker.get_task(sample_task.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_task.id
        assert retrieved.name == sample_task.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, broker: RedisBroker):
        """Test retrieving a non-existent task returns None."""
        from uuid import uuid4
        task = await broker.get_task(uuid4())
        assert task is None

    @pytest.mark.asyncio
    async def test_update_task_status(self, broker: RedisBroker, sample_task: Task):
        """Test updating task status."""
        await broker.enqueue(sample_task, queue_name="default")
        
        # Get and modify task
        task = await broker.get_task(sample_task.id)
        task.mark_processing()
        task.mark_completed(result={"output": "success"})
        
        await broker.update_task(task)
        
        # Verify update persisted
        updated = await broker.get_task(sample_task.id)
        assert updated.status == TaskStatus.COMPLETED
        assert updated.result == {"output": "success"}

    @pytest.mark.asyncio
    async def test_update_task_error(self, broker: RedisBroker, sample_task: Task):
        """Test updating task with error."""
        await broker.enqueue(sample_task, queue_name="default")
        
        # Get and fail task
        task = await broker.get_task(sample_task.id)
        task.mark_processing()
        task.mark_failed("Something went wrong")
        
        await broker.update_task(task)
        
        updated = await broker.get_task(sample_task.id)
        assert updated.status == TaskStatus.FAILED
        assert updated.error == "Something went wrong"


class TestQueueStats:
    """Test queue statistics operations."""

    @pytest.mark.asyncio
    async def test_get_queue_stats_empty(self, broker: RedisBroker):
        """Test getting stats for empty queue."""
        stats = await broker.get_queue_stats("empty_queue")
        
        assert stats.pending == 0
        assert stats.processing == 0
        assert stats.completed == 0
        assert stats.failed == 0

    @pytest.mark.asyncio
    async def test_get_queue_stats_with_pending_tasks(
        self, broker: RedisBroker, batch_tasks: list[Task]
    ):
        """Test getting stats with tasks in queue."""
        for task in batch_tasks[:5]:
            await broker.enqueue(task, queue_name="stats_queue")
        
        stats = await broker.get_queue_stats("stats_queue")
        assert stats.pending == 5


class TestTaskModel:
    """Test Task model operations."""

    def test_task_creation(self):
        """Test task creation with factory method."""
        task = Task.create(
            name="test_task",
            payload={"key": "value"},
            priority=7,
            max_retries=5,
        )
        
        assert task.name == "test_task"
        assert task.payload == {"key": "value"}
        assert task.priority == 7
        assert task.max_retries == 5
        assert task.status == TaskStatus.PENDING
        assert task.id is not None

    def test_task_status_transitions(self, sample_task: Task):
        """Test valid task status transitions."""
        assert sample_task.status == TaskStatus.PENDING
        
        sample_task.mark_processing()
        assert sample_task.status == TaskStatus.PROCESSING
        assert sample_task.started_at is not None
        
        sample_task.mark_completed(result={"done": True})
        assert sample_task.status == TaskStatus.COMPLETED
        assert sample_task.completed_at is not None
        assert sample_task.result == {"done": True}

    def test_task_failure_transition(self, sample_task: Task):
        """Test task failure transition."""
        sample_task.mark_processing()
        sample_task.mark_failed("Error occurred")
        
        assert sample_task.status == TaskStatus.FAILED
        assert sample_task.error == "Error occurred"

    def test_task_retry_increment(self, sample_task: Task):
        """Test task retry count increment using prepare_retry."""
        sample_task.mark_processing()
        sample_task.mark_failed("First error")
        
        # Prepare for retry (resets status and increments retries)
        sample_task.status = TaskStatus.PROCESSING  # Needed before prepare_retry
        sample_task.prepare_retry()
        assert sample_task.retries == 1
        assert sample_task.status == TaskStatus.PENDING

    def test_task_can_retry(self, sample_task: Task):
        """Test can_retry method."""
        assert sample_task.can_retry() is True
        
        # Exhaust retries
        sample_task.retries = 3
        assert sample_task.can_retry() is False

    def test_task_serialization(self, sample_task: Task):
        """Test task JSON serialization."""
        json_str = sample_task.to_json()
        assert isinstance(json_str, str)
        
        # Verify it can be deserialized
        restored = Task.from_json(json_str)
        assert restored.id == sample_task.id
        assert restored.name == sample_task.name
        assert restored.payload == sample_task.payload

    def test_task_priority_validation(self):
        """Test task priority validation."""
        with pytest.raises(ValueError):
            Task.create(name="test", payload={}, priority=0)
        
        with pytest.raises(ValueError):
            Task.create(name="test", payload={}, priority=11)

    def test_task_to_dict(self, sample_task: Task):
        """Test task to_dict method."""
        data = sample_task.to_dict()
        
        assert data["name"] == sample_task.name
        assert data["payload"] == sample_task.payload
        assert data["status"] == "pending"
        assert data["priority"] == sample_task.priority
