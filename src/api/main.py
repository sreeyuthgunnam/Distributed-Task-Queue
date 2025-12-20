"""
FastAPI application for the distributed task queue.

This module defines the main FastAPI application with:
- CORS middleware configuration
- Lifespan handler for Redis connection management
- All API routers mounted
- Health check endpoint
- OpenAPI documentation
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import __version__
from src.api.routers import (
    tasks_router,
    queues_router,
    workers_router,
    ws_router,
)
from src.api.schemas import HealthResponse, ErrorResponse
from src.config import get_settings
from src.queue import RedisBroker

# Configure logging with error handling for serverless
try:
    from src.logging_config import configure_logging, get_logger
    configure_logging()
    logger = get_logger(__name__)
except Exception as e:
    # Fallback to basic logging if structlog fails
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to configure structlog, using basic logging: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events:
    - Startup: Connect to Redis
    - Shutdown: Disconnect from Redis
    """
    settings = get_settings()
    
    # Startup
    logger.info("Starting API server")
    
    # Initialize Redis broker
    broker = RedisBroker(settings)
    app.state.broker = None
    
    # Try to connect to Redis, but don't fail if it's not available
    # This allows the function to start in serverless environments
    try:
        await broker.connect()
        app.state.broker = broker
        logger.info("Connected to Redis", url=settings.redis_url)
    except Exception as e:
        logger.warning(
            "Failed to connect to Redis on startup - will retry on first request",
            error=str(e),
            redis_url=settings.redis_url
        )
        # Store the broker for later retry attempts
        app.state.broker_pending = broker
    
    yield
    
    # Shutdown
    logger.info("Shutting down API server")
    
    if app.state.broker:
        await app.state.broker.disconnect()
        logger.info("Disconnected from Redis")


# Create FastAPI application
app = FastAPI(
    title="Distributed Task Queue API",
    description="""
    A distributed task queue system with Redis backend and priority support.
    
    ## Features
    
    - **Priority-based queuing**: Tasks are processed based on priority (1-10)
    - **Async processing**: Tasks are processed asynchronously by workers
    - **Retry support**: Failed tasks are automatically retried with exponential backoff
    - **Real-time updates**: WebSocket endpoints for live task and dashboard updates
    - **Worker monitoring**: Track worker status and performance
    
    ## Task Lifecycle
    
    1. **Submit** - Task is created and added to the queue (status: `pending`)
    2. **Process** - Worker picks up the task (status: `processing`)
    3. **Complete/Fail** - Task finishes (status: `completed` or `failed`)
    4. **Retry** (optional) - Failed tasks can be retried
    
    ## Quick Start
    
    1. Submit a task: `POST /tasks`
    2. Check status: `GET /api/tasks/{task_id}`
    3. Monitor in real-time: `WebSocket /api/ws/tasks/{task_id}`
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers with /api prefix for Vercel deployment
app.include_router(tasks_router, prefix="/api")
app.include_router(queues_router, prefix="/api")
app.include_router(workers_router, prefix="/api")
app.include_router(ws_router, prefix="/api")


@app.get(
    "/api",
    response_model=dict,
    tags=["Root"],
    summary="API root",
    description="Returns basic API information and links.",
)
async def root() -> dict:
    """
    API root endpoint.
    
    Returns basic information about the API.
    """
    return {
        "name": "Distributed Task Queue API",
        "version": __version__,
        "docs": "/api/docs",
        "redoc": "/api/redoc",
        "openapi": "/api/openapi.json",
        "health": "/api/health",
    }


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
    description="Check the health status of the API and its dependencies.",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Verifies connectivity to Redis and returns overall health status.
    Always returns 200 to verify the function itself is working.
    """
    redis_connected = False
    
    # Try to connect if broker is pending
    if app.state.broker is None and hasattr(app.state, 'broker_pending'):
        try:
            await app.state.broker_pending.connect()
            app.state.broker = app.state.broker_pending
            app.state.broker_pending = None
        except Exception:
            pass
    
    if app.state.broker:
        try:
            redis_connected = await app.state.broker.health_check()
        except Exception:
            redis_connected = False
    
    health_status = "healthy" if redis_connected else "unhealthy"
    
    response = HealthResponse(
        status=health_status,
        redis_connected=redis_connected,
        version=__version__,
    )
    
    if not redis_connected:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(),
        )
    
    return response


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
    )
