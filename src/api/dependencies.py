"""
Dependency injection for FastAPI routes.

This module provides shared dependencies used across API routes,
including the Redis broker instance and common utilities.
"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends, Request

from src.queue import RedisBroker


async def get_broker(request: Request) -> RedisBroker:
    """
    Get the Redis broker instance from application state.

    Args:
        request: FastAPI request object containing app state.

    Returns:
        The shared RedisBroker instance.

    Raises:
        RuntimeError: If broker is not initialized.
    """
    broker = request.app.state.broker
    if broker is None:
        raise RuntimeError("Redis broker not initialized")
    return broker


# Type alias for dependency injection
BrokerDep = Annotated[RedisBroker, Depends(get_broker)]
