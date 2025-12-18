"""
Task handlers for the distributed task queue worker.

This package contains example task handlers that demonstrate how to
implement handlers for different task types. Each handler module
exports a handler function and its associated task name.

Available Handlers:
    - email_handler: Handles email sending tasks
    - image_handler: Handles image processing tasks
    - data_handler: Handles data processing tasks

Example:
    >>> from src.worker.handlers import HANDLERS
    >>> for task_name, handler in HANDLERS.items():
    ...     worker.add_handler(task_name, handler)
"""

from src.worker.handlers.email_handler import (
    simulate_send_email,
    TASK_NAME as EMAIL_TASK_NAME,
)
from src.worker.handlers.image_handler import (
    simulate_resize_image,
    TASK_NAME as IMAGE_TASK_NAME,
)
from src.worker.handlers.data_handler import (
    simulate_data_processing,
    TASK_NAME as DATA_TASK_NAME,
)

# Registry of all available handlers
HANDLERS: dict = {
    EMAIL_TASK_NAME: simulate_send_email,
    IMAGE_TASK_NAME: simulate_resize_image,
    DATA_TASK_NAME: simulate_data_processing,
}

__all__ = [
    "HANDLERS",
    "simulate_send_email",
    "EMAIL_TASK_NAME",
    "simulate_resize_image",
    "IMAGE_TASK_NAME",
    "simulate_data_processing",
    "DATA_TASK_NAME",
]
