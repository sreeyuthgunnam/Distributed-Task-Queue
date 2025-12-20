"""
Task management API routes.

This module provides endpoints for task submission, status checking,
listing, cancellation, and retry operations.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.dependencies import BrokerDep
from src.api.schemas import (
    TaskCreate,
    TaskCreateResponse,
    TaskResponse,
    TaskListResponse,
    TaskCancelResponse,
    TaskRetryResponse,
    TaskStatusEnum,
    ErrorResponse,
)
from src.queue import Task, TaskStatus
from src.logging_config import get_logger

router = APIRouter(prefix="/tasks", tags=["Tasks"])
logger = get_logger(__name__)


@router.post(
    "",
    response_model=TaskCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Task submitted successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Submit a new task",
    description="""
    Submit a new task to the queue for asynchronous processing.
    
    The task will be queued with the specified priority and processed
    by available workers. Returns immediately with the task ID.
    
    **Priority levels:**
    - 1-3: Low priority
    - 4-6: Normal priority
    - 7-9: High priority
    - 10: Critical priority
    """,
)
async def create_task(
    task_data: TaskCreate,
    broker: BrokerDep,
) -> TaskCreateResponse:
    """
    Submit a new task to the queue.

    The task is created and enqueued immediately. Processing happens
    asynchronously by worker processes.
    """
    logger.info(
        "Creating task",
        task_name=task_data.name,
        queue=task_data.queue,
        priority=task_data.priority,
    )

    try:
        # Create task
        task = Task.create(
            name=task_data.name,
            payload=task_data.payload,
            priority=task_data.priority,
            max_retries=task_data.max_retries,
        )

        # Enqueue task
        await broker.enqueue(task, queue_name=task_data.queue)

        logger.info("Task created", task_id=str(task.id))

        return TaskCreateResponse(
            id=task.id,
            status=TaskStatusEnum.PENDING,
            queue=task_data.queue,
            message="Task submitted successfully",
        )

    except ConnectionError as e:
        logger.error("Redis connection error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis connection unavailable. Please check Redis server.",
        )
    except ValueError as e:
        logger.error("Invalid task data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task data: {str(e)}",
        )
    except Exception as e:
        logger.error("Failed to create task", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {str(e)}",
        )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    responses={
        200: {"description": "Task details"},
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
    summary="Get task status and details",
    description="Retrieve the current status and details of a task by its ID.",
)
async def get_task(
    task_id: UUID,
    broker: BrokerDep,
) -> TaskResponse:
    """
    Get task status and details by ID.

    Returns the complete task information including status, result,
    and timing information.
    """
    task = await broker.get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return TaskResponse(
        id=task.id,
        name=task.name,
        payload=task.payload,
        status=TaskStatusEnum(task.status.value),
        priority=task.priority,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        result=task.result,
        error=task.error,
        retries=task.retries,
        max_retries=task.max_retries,
    )


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List tasks",
    description="""
    List tasks with optional filtering by status and queue.
    
    Results are paginated using limit and offset parameters.
    Tasks are returned in order of creation (newest first).
    """,
)
async def list_tasks(
    broker: BrokerDep,
    status_filter: Optional[TaskStatusEnum] = Query(
        None,
        alias="status",
        description="Filter by task status",
    ),
    queue: str = Query(
        "default",
        description="Queue name to list tasks from",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of tasks to return",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of tasks to skip",
    ),
) -> TaskListResponse:
    """
    List tasks with optional filtering.

    Retrieves tasks from the specified queue with optional status filtering.
    """
    tasks: list[TaskResponse] = []
    
    # Get tasks based on status filter
    if status_filter is None or status_filter == TaskStatusEnum.PENDING:
        # Get pending tasks from sorted set
        pending_key = f"queue:{queue}:pending"
        task_ids = await broker.client.zrange(pending_key, 0, -1)
        
        for task_id_str in task_ids:
            task = await broker.get_task(UUID(task_id_str))
            if task:
                tasks.append(TaskResponse(
                    id=task.id,
                    name=task.name,
                    payload=task.payload,
                    status=TaskStatusEnum(task.status.value),
                    priority=task.priority,
                    created_at=task.created_at,
                    started_at=task.started_at,
                    completed_at=task.completed_at,
                    result=task.result,
                    error=task.error,
                    retries=task.retries,
                    max_retries=task.max_retries,
                ))

    # Get tasks from other status sets if needed
    for status_type in ["processing", "completed", "failed"]:
        if status_filter is None or status_filter.value == status_type:
            set_key = f"queue:{queue}:{status_type}"
            task_ids = await broker.client.smembers(set_key)
            
            for task_id_str in task_ids:
                task = await broker.get_task(UUID(task_id_str))
                if task:
                    tasks.append(TaskResponse(
                        id=task.id,
                        name=task.name,
                        payload=task.payload,
                        status=TaskStatusEnum(task.status.value),
                        priority=task.priority,
                        created_at=task.created_at,
                        started_at=task.started_at,
                        completed_at=task.completed_at,
                        result=task.result,
                        error=task.error,
                        retries=task.retries,
                        max_retries=task.max_retries,
                    ))

    # Sort by created_at descending
    tasks.sort(key=lambda t: t.created_at, reverse=True)

    # Apply pagination
    total = len(tasks)
    paginated_tasks = tasks[offset : offset + limit]

    return TaskListResponse(
        tasks=paginated_tasks,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.delete(
    "/{task_id}",
    response_model=TaskCancelResponse,
    responses={
        200: {"description": "Task cancelled"},
        400: {"model": ErrorResponse, "description": "Task cannot be cancelled"},
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
    summary="Cancel a pending task",
    description="""
    Cancel a task that is still pending in the queue.
    
    Only tasks with status 'pending' can be cancelled.
    Tasks that are already processing, completed, or failed cannot be cancelled.
    """,
)
async def cancel_task(
    task_id: UUID,
    broker: BrokerDep,
    queue: str = Query("default", description="Queue name"),
) -> TaskCancelResponse:
    """
    Cancel a pending task.

    Removes the task from the pending queue if it hasn't started processing.
    """
    task = await broker.get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    if task.status != TaskStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task with status '{task.status.value}'. Only pending tasks can be cancelled.",
        )

    # Remove from pending queue
    pending_key = f"queue:{queue}:pending"
    removed = await broker.client.zrem(pending_key, str(task_id))

    if removed:
        # Delete task data
        task_key = f"task:{task_id}"
        await broker.client.delete(task_key)

        logger.info("Task cancelled", task_id=str(task_id))

        return TaskCancelResponse(
            id=task_id,
            cancelled=True,
            message="Task cancelled successfully",
        )
    else:
        return TaskCancelResponse(
            id=task_id,
            cancelled=False,
            message="Task was not in pending queue (may have already started)",
        )


@router.post(
    "/{task_id}/retry",
    response_model=TaskRetryResponse,
    responses={
        200: {"description": "Task queued for retry"},
        400: {"model": ErrorResponse, "description": "Task cannot be retried"},
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
    summary="Retry a failed task",
    description="""
    Retry a task that has failed.
    
    The task will be re-queued with its retry counter incremented.
    Tasks can only be retried if they haven't exceeded their max_retries limit.
    """,
)
async def retry_task(
    task_id: UUID,
    broker: BrokerDep,
    queue: str = Query("default", description="Queue name"),
) -> TaskRetryResponse:
    """
    Retry a failed task.

    Re-queues the task for processing, incrementing the retry counter.
    """
    task = await broker.get_task(task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    if task.status != TaskStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry task with status '{task.status.value}'. Only failed tasks can be retried.",
        )

    if not task.can_retry():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task has exceeded maximum retries ({task.max_retries})",
        )

    # Remove from failed set
    failed_key = f"queue:{queue}:failed"
    await broker.client.srem(failed_key, str(task_id))

    # Prepare for retry and re-enqueue
    task.prepare_retry()
    await broker.update_task(task, queue_name=queue)

    logger.info(
        "Task queued for retry",
        task_id=str(task_id),
        retry_count=task.retries,
    )

    return TaskRetryResponse(
        id=task_id,
        retried=True,
        retry_count=task.retries,
        message="Task queued for retry",
    )
