"""
Worker monitoring API routes.

This module provides endpoints for monitoring worker status,
health, and performance statistics.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import BrokerDep
from src.api.schemas import (
    WorkerResponse,
    WorkerListResponse,
    WorkerStatsResponse,
    WorkerStatusEnum,
    ErrorResponse,
)
from src.worker import Worker, WorkerStatus
from src.worker.utils import get_active_workers, get_worker_statistics
from src.logging_config import get_logger

router = APIRouter(prefix="/workers", tags=["Workers"])
logger = get_logger(__name__)


def worker_state_to_response(state) -> WorkerResponse:
    """Convert WorkerState to WorkerResponse schema."""
    return WorkerResponse(
        worker_id=state.worker_id,
        status=WorkerStatusEnum(state.status.value),
        current_task=state.current_task,
        current_task_name=state.current_task_name,
        last_heartbeat=state.last_heartbeat,
        tasks_completed=state.tasks_completed,
        tasks_failed=state.tasks_failed,
        started_at=state.started_at,
        queues=state.queues,
    )


@router.get(
    "",
    response_model=WorkerListResponse,
    summary="List all workers",
    description="""
    Get a list of all registered workers with their current status.
    
    Worker statuses:
    - **idle**: Waiting for tasks
    - **busy**: Currently processing a task
    - **starting**: Worker is initializing
    - **stopping**: Worker is shutting down
    - **stopped**: Worker has stopped
    
    Workers are considered active if they've sent a heartbeat in the last 30 seconds.
    """,
)
async def list_workers(broker: BrokerDep) -> WorkerListResponse:
    """
    List all registered workers with their status.

    Returns all workers that have registered with the system,
    along with aggregate statistics.
    """
    all_workers = await Worker.get_all_workers(broker)
    active_workers = await get_active_workers(broker, timeout_seconds=30)
    stats = await get_worker_statistics(broker)

    workers = [worker_state_to_response(w) for w in all_workers]

    return WorkerListResponse(
        workers=workers,
        total_workers=stats["total_workers"],
        active_workers=stats["active_workers"],
        idle_workers=stats["idle_workers"],
        busy_workers=stats["busy_workers"],
    )


@router.get(
    "/{worker_id}",
    response_model=WorkerResponse,
    responses={
        200: {"description": "Worker details"},
        404: {"model": ErrorResponse, "description": "Worker not found"},
    },
    summary="Get worker details",
    description="""
    Get detailed information about a specific worker.
    
    Includes current task being processed (if any), heartbeat timestamp,
    and statistics.
    """,
)
async def get_worker(
    worker_id: str,
    broker: BrokerDep,
) -> WorkerResponse:
    """
    Get details for a specific worker.

    Returns the worker's current status, current task, and statistics.
    """
    state = await Worker.get_worker_state(broker, worker_id)

    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker '{worker_id}' not found",
        )

    return worker_state_to_response(state)


@router.get(
    "/{worker_id}/stats",
    response_model=WorkerStatsResponse,
    responses={
        200: {"description": "Worker statistics"},
        404: {"model": ErrorResponse, "description": "Worker not found"},
    },
    summary="Get worker statistics",
    description="""
    Get detailed performance statistics for a specific worker.
    
    Includes:
    - Tasks completed and failed counts
    - Success rate percentage
    - Uptime in seconds
    - Average task duration (if available)
    """,
)
async def get_worker_stats(
    worker_id: str,
    broker: BrokerDep,
) -> WorkerStatsResponse:
    """
    Get detailed statistics for a specific worker.

    Calculates success rate, uptime, and other performance metrics.
    """
    state = await Worker.get_worker_state(broker, worker_id)

    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker '{worker_id}' not found",
        )

    # Calculate statistics
    total_tasks = state.tasks_completed + state.tasks_failed
    success_rate = (
        (state.tasks_completed / total_tasks * 100)
        if total_tasks > 0
        else 100.0
    )

    now = datetime.now(timezone.utc)
    uptime_seconds = (now - state.started_at).total_seconds()

    # Note: Average task duration would require additional tracking
    # For now, we return None
    avg_task_duration_ms = None

    return WorkerStatsResponse(
        worker_id=worker_id,
        tasks_completed=state.tasks_completed,
        tasks_failed=state.tasks_failed,
        success_rate=round(success_rate, 2),
        uptime_seconds=round(uptime_seconds, 2),
        avg_task_duration_ms=avg_task_duration_ms,
    )
