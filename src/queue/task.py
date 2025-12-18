"""
Task data model for the distributed task queue.

This module defines the Task dataclass that represents a unit of work
in the distributed task queue system, along with the TaskStatus enumeration.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4
import json


class TaskStatus(str, Enum):
    """
    Enumeration of possible task states in the queue.

    Attributes:
        PENDING: Task has been created and is waiting in the queue.
        PROCESSING: Task has been picked up by a worker and is being processed.
        COMPLETED: Task has finished successfully.
        FAILED: Task has failed after exhausting all retry attempts.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    def __str__(self) -> str:
        """Return the string value of the status."""
        return self.value


@dataclass
class Task:
    """
    Represents a task in the distributed task queue.

    A Task encapsulates all information needed to execute and track
    a unit of work, including its payload, status, timing information,
    and retry configuration.

    Attributes:
        id: Unique identifier for the task (UUID).
        name: Human-readable name/type of the task (e.g., "send_email", "process_image").
        payload: Dictionary containing task-specific data and parameters.
        status: Current state of the task (pending, processing, completed, failed).
        priority: Task priority from 1 (lowest) to 10 (highest). Higher priority
            tasks are processed first.
        created_at: Timestamp when the task was created.
        started_at: Timestamp when task processing began (None if not started).
        completed_at: Timestamp when task finished (None if not finished).
        result: Result data from successful task execution (None if not completed).
        error: Error message from failed task execution (None if no error).
        retries: Number of retry attempts that have been made.
        max_retries: Maximum number of retries allowed before marking as failed.

    Example:
        >>> task = Task.create(
        ...     name="send_email",
        ...     payload={"to": "user@example.com", "subject": "Hello"},
        ...     priority=5,
        ...     max_retries=3
        ... )
        >>> print(task.status)
        pending
        >>> task.mark_processing()
        >>> print(task.status)
        processing
    """

    id: UUID
    name: str
    payload: dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5  # 1-10, higher is more important
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3

    def __post_init__(self) -> None:
        """
        Validate task attributes after initialization.

        Raises:
            ValueError: If priority is not between 1 and 10 inclusive.
            ValueError: If max_retries is negative.
        """
        if not 1 <= self.priority <= 10:
            raise ValueError(f"Priority must be between 1 and 10, got {self.priority}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative, got {self.max_retries}")

    @classmethod
    def create(
        cls,
        name: str,
        payload: dict[str, Any],
        priority: int = 5,
        max_retries: int = 3,
    ) -> "Task":
        """
        Factory method to create a new task with a generated UUID.

        This is the preferred way to create new tasks as it ensures
        proper initialization of all fields.

        Args:
            name: The name/type of the task.
            payload: Dictionary containing task-specific data.
            priority: Task priority from 1-10 (default: 5).
            max_retries: Maximum retry attempts (default: 3).

        Returns:
            A new Task instance with a unique ID and PENDING status.

        Example:
            >>> task = Task.create(
            ...     name="process_order",
            ...     payload={"order_id": 12345},
            ...     priority=8
            ... )
        """
        return cls(
            id=uuid4(),
            name=name,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
        )

    def mark_processing(self) -> None:
        """
        Mark the task as currently being processed.

        Updates the status to PROCESSING and sets the started_at timestamp.

        Raises:
            ValueError: If task is not in PENDING status.
        """
        if self.status != TaskStatus.PENDING:
            raise ValueError(
                f"Cannot mark task as processing: current status is {self.status}"
            )
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.now(timezone.utc)

    def mark_completed(self, result: Optional[dict[str, Any]] = None) -> None:
        """
        Mark the task as successfully completed.

        Updates the status to COMPLETED, sets the completed_at timestamp,
        and optionally stores the result.

        Args:
            result: Optional dictionary containing the task result.

        Raises:
            ValueError: If task is not in PROCESSING status.
        """
        if self.status != TaskStatus.PROCESSING:
            raise ValueError(
                f"Cannot mark task as completed: current status is {self.status}"
            )
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.result = result

    def mark_failed(self, error: str) -> None:
        """
        Mark the task as failed.

        Updates the status to FAILED, sets the completed_at timestamp,
        and stores the error message.

        Args:
            error: Error message describing why the task failed.

        Raises:
            ValueError: If task is not in PROCESSING status.
        """
        if self.status != TaskStatus.PROCESSING:
            raise ValueError(
                f"Cannot mark task as failed: current status is {self.status}"
            )
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error

    def can_retry(self) -> bool:
        """
        Check if the task can be retried.

        Returns:
            True if the number of retries is less than max_retries.
        """
        return self.retries < self.max_retries

    def prepare_retry(self) -> None:
        """
        Prepare the task for a retry attempt.

        Increments the retry counter and resets the status to PENDING.
        Clears the started_at and completed_at timestamps.

        Raises:
            ValueError: If task cannot be retried (max retries exceeded).
        """
        if not self.can_retry():
            raise ValueError(
                f"Cannot retry task: max retries ({self.max_retries}) exceeded"
            )
        self.retries += 1
        self.status = TaskStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.error = None

    @property
    def duration(self) -> Optional[float]:
        """
        Calculate the task execution duration in seconds.

        Returns:
            Duration in seconds if task has started and completed,
            None otherwise.
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the task to a dictionary for serialization.

        Returns:
            Dictionary representation of the task suitable for JSON serialization.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "payload": self.payload,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "retries": self.retries,
            "max_retries": self.max_retries,
        }

    def to_json(self) -> str:
        """
        Serialize the task to a JSON string.

        Returns:
            JSON string representation of the task.
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """
        Create a Task instance from a dictionary.

        Args:
            data: Dictionary containing task data, typically from deserialization.

        Returns:
            Task instance reconstructed from the dictionary.

        Example:
            >>> data = {"id": "...", "name": "test", "payload": {}, ...}
            >>> task = Task.from_dict(data)
        """
        return cls(
            id=UUID(data["id"]),
            name=data["name"],
            payload=data["payload"],
            status=TaskStatus(data["status"]),
            priority=data["priority"],
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            result=data.get("result"),
            error=data.get("error"),
            retries=data.get("retries", 0),
            max_retries=data.get("max_retries", 3),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Task":
        """
        Create a Task instance from a JSON string.

        Args:
            json_str: JSON string containing task data.

        Returns:
            Task instance reconstructed from the JSON.

        Example:
            >>> json_data = '{"id": "...", "name": "test", ...}'
            >>> task = Task.from_json(json_data)
        """
        return cls.from_dict(json.loads(json_str))

    def __repr__(self) -> str:
        """Return a detailed string representation of the task."""
        return (
            f"Task(id={self.id}, name={self.name!r}, status={self.status.value}, "
            f"priority={self.priority}, retries={self.retries}/{self.max_retries})"
        )
