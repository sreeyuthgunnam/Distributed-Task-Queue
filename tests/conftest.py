"""
Pytest configuration and fixtures for the distributed task queue tests.
"""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis_aioredis
from httpx import AsyncClient, ASGITransport

from src.queue.task import Task, TaskStatus
from src.queue.broker import RedisBroker


# ============================================================================
# Event Loop Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Redis Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def fake_redis() -> AsyncGenerator:
    """Create a fake Redis client for testing."""
    redis = fakeredis_aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.flushall()
    await redis.aclose()


@pytest_asyncio.fixture
async def broker(fake_redis) -> AsyncGenerator[RedisBroker, None]:
    """Create a RedisBroker with fake Redis for testing."""
    broker_instance = RedisBroker()
    broker_instance._client = fake_redis
    yield broker_instance


# ============================================================================
# Task Fixtures
# ============================================================================

@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task.create(
        name="test_task",
        payload={"key": "value", "count": 42},
        priority=5,
        max_retries=3,
    )


@pytest.fixture
def high_priority_task() -> Task:
    """Create a high priority task for testing."""
    return Task.create(
        name="urgent_task",
        payload={"urgent": True},
        priority=10,
        max_retries=3,
    )


@pytest.fixture
def low_priority_task() -> Task:
    """Create a low priority task for testing."""
    return Task.create(
        name="background_task",
        payload={"background": True},
        priority=1,
        max_retries=3,
    )


@pytest.fixture
def email_task() -> Task:
    """Create an email task for testing."""
    return Task.create(
        name="send_email",
        payload={
            "to": "test@example.com",
            "subject": "Test Email",
            "body": "This is a test email.",
        },
        priority=5,
        max_retries=3,
    )


@pytest.fixture
def image_task() -> Task:
    """Create an image processing task for testing."""
    return Task.create(
        name="process_image",
        payload={
            "image_url": "https://example.com/image.jpg",
            "operations": ["resize", "compress"],
            "width": 800,
            "height": 600,
        },
        priority=3,
        max_retries=2,
    )


@pytest.fixture
def batch_tasks() -> list[Task]:
    """Create a batch of tasks with varying priorities."""
    tasks = []
    for i in range(10):
        task = Task.create(
            name=f"batch_task_{i}",
            payload={"index": i},
            priority=(i % 10) + 1,
            max_retries=3,
        )
        tasks.append(task)
    return tasks


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def async_client(broker) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing the API."""
    from src.api.main import app
    
    # Override the broker dependency
    app.state.broker = broker
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ============================================================================
# Worker Fixtures
# ============================================================================

@pytest.fixture
def mock_handler() -> AsyncMock:
    """Create a mock task handler."""
    handler = AsyncMock()
    handler.return_value = {"status": "success", "processed": True}
    return handler


@pytest.fixture
def failing_handler() -> AsyncMock:
    """Create a mock handler that always fails."""
    handler = AsyncMock()
    handler.side_effect = Exception("Handler failed intentionally")
    return handler


@pytest.fixture
def slow_handler() -> AsyncMock:
    """Create a mock handler that takes a long time."""
    async def slow_execution(payload: dict) -> dict:
        await asyncio.sleep(10)
        return {"status": "success"}
    
    handler = AsyncMock(side_effect=slow_execution)
    return handler


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def task_factory():
    """Factory fixture for creating tasks with custom parameters."""
    def _create_task(
        name: str = "test_task",
        payload: dict = None,
        priority: int = 5,
        max_retries: int = 3,
    ) -> Task:
        return Task.create(
            name=name,
            payload=payload or {},
            priority=priority,
            max_retries=max_retries,
        )
    return _create_task
