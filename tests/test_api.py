"""
Tests for the FastAPI endpoints.

Tests cover:
- Health check endpoint
- Task CRUD operations
- Queue management
- Worker endpoints
- Error handling
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.queue.task import TaskStatus


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        """Test health endpoint returns OK."""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestTaskEndpoints:
    """Test task-related endpoints."""

    @pytest.mark.asyncio
    async def test_create_task(self, async_client: AsyncClient):
        """Test creating a new task."""
        task_data = {
            "name": "test_task",
            "payload": {"key": "value"},
            "queue": "default",
            "priority": 5,
        }
        
        response = await async_client.post("/tasks", json=task_data)
        
        assert response.status_code in [200, 201, 202]
        data = response.json()
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_task_with_high_priority(self, async_client: AsyncClient):
        """Test creating a high priority task."""
        task_data = {
            "name": "urgent_task",
            "payload": {"urgent": True},
            "queue": "default",
            "priority": 10,
        }
        
        response = await async_client.post("/tasks", json=task_data)
        
        assert response.status_code in [200, 201, 202]

    @pytest.mark.asyncio
    async def test_create_task_default_values(self, async_client: AsyncClient):
        """Test task creation with default values."""
        task_data = {
            "name": "simple_task",
            "payload": {},
        }
        
        response = await async_client.post("/tasks", json=task_data)
        
        assert response.status_code in [200, 201, 202]

    @pytest.mark.asyncio
    async def test_create_task_invalid_priority(self, async_client: AsyncClient):
        """Test task creation with invalid priority."""
        task_data = {
            "name": "test_task",
            "payload": {},
            "priority": 15,  # Invalid: must be 1-10
        }
        
        response = await async_client.post("/tasks", json=task_data)
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_task(self, async_client: AsyncClient):
        """Test retrieving a task by ID."""
        # First create a task
        create_response = await async_client.post("/tasks", json={
            "name": "test_task",
            "payload": {"test": True},
        })
        task_id = create_response.json()["id"]
        
        # Then retrieve it
        response = await async_client.get(f"/tasks/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, async_client: AsyncClient):
        """Test retrieving non-existent task."""
        response = await async_client.get("/tasks/nonexistent-id")
        
        assert response.status_code in [404, 422]

    @pytest.mark.asyncio
    async def test_list_tasks(self, async_client: AsyncClient):
        """Test listing tasks."""
        # Create some tasks
        for i in range(3):
            await async_client.post("/tasks", json={
                "name": f"task_{i}",
                "payload": {"index": i},
            })
        
        response = await async_client.get("/tasks")
        
        assert response.status_code == 200


class TestQueueEndpoints:
    """Test queue-related endpoints."""

    @pytest.mark.asyncio
    async def test_list_queues(self, async_client: AsyncClient):
        """Test listing all queues."""
        # Create task to ensure queue exists
        await async_client.post("/tasks", json={
            "name": "task1",
            "payload": {},
            "queue": "test_queue",
        })
        
        response = await async_client.get("/queues")
        
        assert response.status_code == 200
        data = response.json()
        assert "queues" in data

    @pytest.mark.asyncio
    async def test_get_queue_stats(self, async_client: AsyncClient):
        """Test getting queue statistics."""
        # Create some tasks
        await async_client.post("/tasks", json={
            "name": "test_task",
            "payload": {},
            "queue": "stats_queue",
        })
        
        response = await async_client.get("/queues/stats_queue/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "pending" in data


class TestWorkerEndpoints:
    """Test worker-related endpoints."""

    @pytest.mark.asyncio
    async def test_list_workers(self, async_client: AsyncClient):
        """Test listing all workers."""
        response = await async_client.get("/workers")
        
        assert response.status_code == 200
        data = response.json()
        assert "workers" in data


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_invalid_json(self, async_client: AsyncClient):
        """Test handling of invalid JSON."""
        response = await async_client.post(
            "/tasks",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_field(self, async_client: AsyncClient):
        """Test handling of missing required field."""
        response = await async_client.post("/tasks", json={
            "payload": {},
            # Missing 'name' field
        })
        
        assert response.status_code == 422
