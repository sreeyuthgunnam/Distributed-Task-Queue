"""
Pydantic schemas for the FastAPI API.

This module defines all request and response models used by the API endpoints,
with validation, examples, and OpenAPI documentation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Enums
# =============================================================================


class TaskStatusEnum(str, Enum):
    """Task status enumeration for API responses."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkerStatusEnum(str, Enum):
    """Worker status enumeration for API responses."""

    IDLE = "idle"
    BUSY = "busy"
    STARTING = "starting"
    STOPPING = "stopping"
    STOPPED = "stopped"


# =============================================================================
# Task Schemas
# =============================================================================


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "send_email",
                "payload": {
                    "to": "user@example.com",
                    "subject": "Hello!",
                    "body": "This is a test email.",
                },
                "priority": 5,
                "queue": "default",
                "max_retries": 3,
            }
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Task type/name (e.g., 'send_email', 'process_image')",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Task-specific data and parameters",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Task priority (1-10, higher = more important)",
    )
    queue: str = Field(
        default="default",
        min_length=1,
        max_length=100,
        description="Queue name to submit the task to",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts",
    )


class TaskResponse(BaseModel):
    """Schema for task response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "send_email",
                "payload": {
                    "to": "user@example.com",
                    "subject": "Hello!",
                    "body": "This is a test email.",
                },
                "status": "completed",
                "priority": 5,
                "created_at": "2024-01-15T10:30:00Z",
                "started_at": "2024-01-15T10:30:05Z",
                "completed_at": "2024-01-15T10:30:07Z",
                "result": {"success": True, "message_id": "msg_abc123"},
                "error": None,
                "retries": 0,
                "max_retries": 3,
            }
        }
    )

    id: UUID = Field(..., description="Unique task identifier")
    name: str = Field(..., description="Task type/name")
    payload: dict[str, Any] = Field(..., description="Task payload data")
    status: TaskStatusEnum = Field(..., description="Current task status")
    priority: int = Field(..., description="Task priority (1-10)")
    created_at: datetime = Field(..., description="Task creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    result: Optional[dict[str, Any]] = Field(None, description="Task result (on success)")
    error: Optional[str] = Field(None, description="Error message (on failure)")
    retries: int = Field(..., description="Number of retry attempts made")
    max_retries: int = Field(..., description="Maximum retry attempts allowed")


class TaskCreateResponse(BaseModel):
    """Schema for task creation response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "queue": "default",
                "message": "Task submitted successfully",
            }
        }
    )

    id: UUID = Field(..., description="Unique task identifier")
    status: TaskStatusEnum = Field(..., description="Initial task status")
    queue: str = Field(..., description="Queue the task was submitted to")
    message: str = Field(..., description="Status message")


class TaskListResponse(BaseModel):
    """Schema for paginated task list response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tasks": [],
                "total": 100,
                "limit": 10,
                "offset": 0,
                "has_more": True,
            }
        }
    )

    tasks: list[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks matching filters")
    limit: int = Field(..., description="Maximum tasks returned")
    offset: int = Field(..., description="Number of tasks skipped")
    has_more: bool = Field(..., description="Whether more tasks are available")


class TaskCancelResponse(BaseModel):
    """Schema for task cancellation response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "cancelled": True,
                "message": "Task cancelled successfully",
            }
        }
    )

    id: UUID = Field(..., description="Task identifier")
    cancelled: bool = Field(..., description="Whether cancellation was successful")
    message: str = Field(..., description="Status message")


class TaskRetryResponse(BaseModel):
    """Schema for task retry response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "retried": True,
                "retry_count": 1,
                "message": "Task queued for retry",
            }
        }
    )

    id: UUID = Field(..., description="Task identifier")
    retried: bool = Field(..., description="Whether retry was successful")
    retry_count: int = Field(..., description="Current retry count")
    message: str = Field(..., description="Status message")


# =============================================================================
# Queue Schemas
# =============================================================================


class QueueStats(BaseModel):
    """Schema for queue statistics."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queue_name": "default",
                "pending": 25,
                "processing": 5,
                "completed": 150,
                "failed": 3,
                "total": 183,
                "paused": False,
            }
        }
    )

    queue_name: str = Field(..., description="Queue name")
    pending: int = Field(..., description="Number of pending tasks")
    processing: int = Field(..., description="Number of tasks being processed")
    completed: int = Field(..., description="Number of completed tasks")
    failed: int = Field(..., description="Number of failed tasks")
    total: int = Field(..., description="Total tasks in queue")
    paused: bool = Field(default=False, description="Whether queue is paused")


class QueueListResponse(BaseModel):
    """Schema for list of queues with stats."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queues": [
                    {
                        "queue_name": "default",
                        "pending": 25,
                        "processing": 5,
                        "completed": 150,
                        "failed": 3,
                        "total": 183,
                        "paused": False,
                    }
                ],
                "total_queues": 1,
            }
        }
    )

    queues: list[QueueStats] = Field(..., description="List of queues with stats")
    total_queues: int = Field(..., description="Total number of queues")


class QueueActionResponse(BaseModel):
    """Schema for queue action responses (pause/resume/clear)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queue_name": "default",
                "action": "paused",
                "success": True,
                "message": "Queue paused successfully",
            }
        }
    )

    queue_name: str = Field(..., description="Queue name")
    action: str = Field(..., description="Action performed")
    success: bool = Field(..., description="Whether action was successful")
    message: str = Field(..., description="Status message")


class DeadLetterClearResponse(BaseModel):
    """Schema for dead letter queue clear response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queue_name": "default:dlq",
                "cleared_count": 5,
                "message": "Dead letter queue cleared",
            }
        }
    )

    queue_name: str = Field(..., description="Dead letter queue name")
    cleared_count: int = Field(..., description="Number of tasks cleared")
    message: str = Field(..., description="Status message")


# =============================================================================
# Worker Schemas
# =============================================================================


class WorkerResponse(BaseModel):
    """Schema for worker information."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "worker_id": "worker-abc123",
                "status": "busy",
                "current_task": "550e8400-e29b-41d4-a716-446655440000",
                "current_task_name": "send_email",
                "last_heartbeat": "2024-01-15T10:30:00Z",
                "tasks_completed": 150,
                "tasks_failed": 3,
                "started_at": "2024-01-15T08:00:00Z",
                "queues": ["default", "high-priority"],
            }
        }
    )

    worker_id: str = Field(..., description="Unique worker identifier")
    status: WorkerStatusEnum = Field(..., description="Current worker status")
    current_task: Optional[str] = Field(None, description="ID of current task")
    current_task_name: Optional[str] = Field(None, description="Name of current task")
    last_heartbeat: datetime = Field(..., description="Last heartbeat timestamp")
    tasks_completed: int = Field(..., description="Total tasks completed")
    tasks_failed: int = Field(..., description="Total tasks failed")
    started_at: datetime = Field(..., description="Worker start time")
    queues: list[str] = Field(..., description="Queues this worker processes")


class WorkerListResponse(BaseModel):
    """Schema for list of workers."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workers": [],
                "total_workers": 3,
                "active_workers": 2,
                "idle_workers": 1,
                "busy_workers": 1,
            }
        }
    )

    workers: list[WorkerResponse] = Field(..., description="List of workers")
    total_workers: int = Field(..., description="Total registered workers")
    active_workers: int = Field(..., description="Workers with recent heartbeat")
    idle_workers: int = Field(..., description="Workers waiting for tasks")
    busy_workers: int = Field(..., description="Workers processing tasks")


class WorkerStatsResponse(BaseModel):
    """Schema for detailed worker statistics."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "worker_id": "worker-abc123",
                "tasks_completed": 150,
                "tasks_failed": 3,
                "success_rate": 98.04,
                "uptime_seconds": 7200,
                "avg_task_duration_ms": 1500,
            }
        }
    )

    worker_id: str = Field(..., description="Worker identifier")
    tasks_completed: int = Field(..., description="Total tasks completed")
    tasks_failed: int = Field(..., description="Total tasks failed")
    success_rate: float = Field(..., description="Success rate percentage")
    uptime_seconds: float = Field(..., description="Worker uptime in seconds")
    avg_task_duration_ms: Optional[float] = Field(
        None, description="Average task duration in milliseconds"
    )


# =============================================================================
# WebSocket Schemas
# =============================================================================


class WSTaskUpdate(BaseModel):
    """Schema for WebSocket task status update."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event": "task_update",
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "result": {"success": True},
                "timestamp": "2024-01-15T10:30:07Z",
            }
        }
    )

    event: str = Field(default="task_update", description="Event type")
    task_id: str = Field(..., description="Task identifier")
    status: TaskStatusEnum = Field(..., description="Current task status")
    result: Optional[dict[str, Any]] = Field(None, description="Task result")
    error: Optional[str] = Field(None, description="Error message")
    timestamp: datetime = Field(..., description="Update timestamp")


class WSDashboardUpdate(BaseModel):
    """Schema for WebSocket dashboard update."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event": "dashboard_update",
                "queues": [],
                "workers": {"total": 3, "active": 2, "busy": 1},
                "timestamp": "2024-01-15T10:30:07Z",
            }
        }
    )

    event: str = Field(default="dashboard_update", description="Event type")
    queues: list[QueueStats] = Field(..., description="Queue statistics")
    workers: dict[str, int] = Field(..., description="Worker counts")
    timestamp: datetime = Field(..., description="Update timestamp")


# =============================================================================
# Common Schemas
# =============================================================================


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Task not found",
                "error_code": "TASK_NOT_FOUND",
            }
        }
    )

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for programmatic handling")


class HealthResponse(BaseModel):
    """Schema for health check response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "redis_connected": True,
                "version": "0.1.0",
            }
        }
    )

    status: str = Field(..., description="Overall health status")
    redis_connected: bool = Field(..., description="Redis connection status")
    version: str = Field(..., description="API version")
