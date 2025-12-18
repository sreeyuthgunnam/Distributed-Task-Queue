"""
API routers package.

This package contains all FastAPI routers for the distributed task queue API.
"""

from src.api.routers.tasks import router as tasks_router
from src.api.routers.queues import router as queues_router
from src.api.routers.workers import router as workers_router
from src.api.routers.ws import router as ws_router

__all__ = [
    "tasks_router",
    "queues_router",
    "workers_router",
    "ws_router",
]
