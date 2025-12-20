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
    from fastapi import HTTPException, status
    
    broker = getattr(request.app.state, "broker", None)
    if broker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis broker not initialized. Please check Redis connection."
        )
    return broker


# Type alias for dependency injection
BrokerDep = Annotated[RedisBroker, Depends(get_broker)]
