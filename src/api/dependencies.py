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
    
    Implements lazy connection retry for serverless environments.

    Args:
        request: FastAPI request object containing app state.

    Returns:
        The shared RedisBroker instance.

    Raises:
        HTTPException: If broker cannot be initialized after retry.
    """
    from fastapi import HTTPException, status
    from src.logging_config import get_logger
    
    logger = get_logger(__name__)
    broker = getattr(request.app.state, "broker", None)
    
    # If broker is not connected, try to connect now (lazy initialization)
    if broker is None:
        pending_broker = getattr(request.app.state, "broker_pending", None)
        if pending_broker:
            try:
                logger.info("Attempting lazy Redis connection...")
                await pending_broker.connect()
                request.app.state.broker = pending_broker
                request.app.state.broker_pending = None
                logger.info("Redis connected successfully on retry")
                return pending_broker
            except Exception as e:
                logger.error("Failed to connect to Redis on retry", error=str(e))
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis connection unavailable. Please verify REDIS_URL environment variable is set correctly in Vercel."
        )
    
    return broker


# Type alias for dependency injection
BrokerDep = Annotated[RedisBroker, Depends(get_broker)]
