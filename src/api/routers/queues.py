"""
Queue management API routes.

This module provides endpoints for queue statistics, management,
and dead letter queue operations.
"""

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import BrokerDep
from src.api.schemas import (
    QueueStats,
    QueueListResponse,
    QueueActionResponse,
    DeadLetterClearResponse,
    ErrorResponse,
)
from src.logging_config import get_logger

router = APIRouter(prefix="/queues", tags=["Queues"])
logger = get_logger(__name__)

# Key for storing paused queues
PAUSED_QUEUES_KEY = "queues:paused"


async def get_queue_paused_status(broker, queue_name: str) -> bool:
    """Check if a queue is paused."""
    return await broker.client.sismember(PAUSED_QUEUES_KEY, queue_name)


async def get_all_queue_names(broker) -> set[str]:
    """
    Discover all queue names by scanning Redis keys.
    
    Returns a set of unique queue names.
    """
    queue_names = set()
    
    # Scan for queue keys
    cursor = 0
    while True:
        cursor, keys = await broker.client.scan(
            cursor=cursor,
            match="queue:*:*",
            count=100,
        )
        
        for key in keys:
            # Extract queue name from key pattern "queue:{name}:{status}"
            parts = key.split(":")
            if len(parts) >= 3:
                queue_name = parts[1]
                # Exclude DLQ from main queue list
                if not queue_name.endswith(":dlq"):
                    queue_names.add(queue_name)
        
        if cursor == 0:
            break
    
    # Always include default queue
    queue_names.add("default")
    
    return queue_names


@router.get(
    "",
    response_model=QueueListResponse,
    summary="List all queues with statistics",
    description="""
    Get a list of all queues in the system with their current statistics.
    
    Statistics include:
    - **pending**: Tasks waiting to be processed
    - **processing**: Tasks currently being processed
    - **completed**: Successfully completed tasks
    - **failed**: Failed tasks (including those in DLQ)
    - **paused**: Whether the queue is paused
    """,
)
async def list_queues(broker: BrokerDep) -> QueueListResponse:
    """
    List all queues with their statistics.

    Discovers queues by scanning Redis keys and aggregates statistics.
    """
    queue_names = await get_all_queue_names(broker)
    queues: list[QueueStats] = []

    for queue_name in sorted(queue_names):
        stats = await broker.get_queue_stats(queue_name)
        paused = await get_queue_paused_status(broker, queue_name)
        
        queues.append(QueueStats(
            queue_name=stats.queue_name,
            pending=stats.pending,
            processing=stats.processing,
            completed=stats.completed,
            failed=stats.failed,
            total=stats.total,
            paused=paused,
        ))

    return QueueListResponse(
        queues=queues,
        total_queues=len(queues),
    )


@router.get(
    "/{queue_name}/stats",
    response_model=QueueStats,
    responses={
        200: {"description": "Queue statistics"},
    },
    summary="Get detailed queue statistics",
    description="Get detailed statistics for a specific queue.",
)
async def get_queue_stats(
    queue_name: str,
    broker: BrokerDep,
) -> QueueStats:
    """
    Get detailed statistics for a specific queue.

    Returns counts for pending, processing, completed, and failed tasks.
    """
    stats = await broker.get_queue_stats(queue_name)
    paused = await get_queue_paused_status(broker, queue_name)

    return QueueStats(
        queue_name=stats.queue_name,
        pending=stats.pending,
        processing=stats.processing,
        completed=stats.completed,
        failed=stats.failed,
        total=stats.total,
        paused=paused,
    )


@router.delete(
    "/{queue_name}/dead-letter",
    response_model=DeadLetterClearResponse,
    summary="Clear dead letter queue",
    description="""
    Clear all tasks from the dead letter queue (DLQ) for the specified queue.
    
    The DLQ contains tasks that have failed all retry attempts.
    This operation permanently deletes these tasks.
    """,
)
async def clear_dead_letter_queue(
    queue_name: str,
    broker: BrokerDep,
) -> DeadLetterClearResponse:
    """
    Clear the dead letter queue for a specific queue.

    Permanently removes all failed tasks from the DLQ.
    """
    dlq_name = f"{queue_name}:dlq"
    dlq_key = f"queue:{dlq_name}:failed"

    # Get task IDs in DLQ
    task_ids = await broker.client.smembers(dlq_key)
    cleared_count = len(task_ids)

    # Delete task data
    for task_id in task_ids:
        task_key = f"task:{task_id}"
        await broker.client.delete(task_key)

    # Clear the DLQ set
    await broker.client.delete(dlq_key)

    logger.info(
        "Dead letter queue cleared",
        queue=queue_name,
        cleared_count=cleared_count,
    )

    return DeadLetterClearResponse(
        queue_name=dlq_name,
        cleared_count=cleared_count,
        message=f"Cleared {cleared_count} tasks from dead letter queue",
    )


@router.post(
    "/{queue_name}/pause",
    response_model=QueueActionResponse,
    responses={
        200: {"description": "Queue paused"},
        400: {"model": ErrorResponse, "description": "Queue already paused"},
    },
    summary="Pause queue processing",
    description="""
    Pause processing of tasks from the specified queue.
    
    Workers will stop picking up new tasks from this queue until resumed.
    Tasks already being processed will continue to completion.
    """,
)
async def pause_queue(
    queue_name: str,
    broker: BrokerDep,
) -> QueueActionResponse:
    """
    Pause task processing for a queue.

    Adds the queue to the paused set. Workers should check this
    before dequeuing tasks.
    """
    already_paused = await get_queue_paused_status(broker, queue_name)

    if already_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Queue '{queue_name}' is already paused",
        )

    await broker.client.sadd(PAUSED_QUEUES_KEY, queue_name)

    logger.info("Queue paused", queue=queue_name)

    return QueueActionResponse(
        queue_name=queue_name,
        action="paused",
        success=True,
        message=f"Queue '{queue_name}' paused successfully",
    )


@router.post(
    "/{queue_name}/resume",
    response_model=QueueActionResponse,
    responses={
        200: {"description": "Queue resumed"},
        400: {"model": ErrorResponse, "description": "Queue not paused"},
    },
    summary="Resume queue processing",
    description="""
    Resume processing of tasks from a paused queue.
    
    Workers will start picking up tasks from this queue again.
    """,
)
async def resume_queue(
    queue_name: str,
    broker: BrokerDep,
) -> QueueActionResponse:
    """
    Resume task processing for a paused queue.

    Removes the queue from the paused set.
    """
    is_paused = await get_queue_paused_status(broker, queue_name)

    if not is_paused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Queue '{queue_name}' is not paused",
        )

    await broker.client.srem(PAUSED_QUEUES_KEY, queue_name)

    logger.info("Queue resumed", queue=queue_name)

    return QueueActionResponse(
        queue_name=queue_name,
        action="resumed",
        success=True,
        message=f"Queue '{queue_name}' resumed successfully",
    )
