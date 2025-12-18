"""
FastAPI API package for the distributed task queue.

This package provides the REST API and WebSocket endpoints for
managing tasks, queues, and workers.

Usage:
    uvicorn src.api.main:app --reload

Endpoints:
    - /tasks - Task management
    - /queues - Queue management  
    - /workers - Worker monitoring
    - /ws - WebSocket real-time updates
    - /health - Health check
    - /docs - Swagger UI documentation
    - /redoc - ReDoc documentation
"""

from src.api.main import app

__all__ = ["app"]
