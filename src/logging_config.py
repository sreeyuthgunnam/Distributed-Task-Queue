"""
Logging configuration module using structlog.

This module configures structured logging for the distributed task queue,
providing consistent log formatting, context propagation, and JSON output
for production environments.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from src.config import get_settings


def configure_logging() -> None:
    """
    Configure structlog for the application.

    Sets up structured logging with:
    - Timestamp in ISO format
    - Log level filtering based on settings
    - Pretty printing for development (console)
    - JSON formatting for production

    This function should be called once at application startup.

    Example:
        >>> configure_logging()
        >>> logger = get_logger("my_module")
        >>> logger.info("Application started", version="1.0.0")
    """
    settings = get_settings()

    # Shared processors for all log entries
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Development: Pretty console output
    # Production: JSON output
    if settings.log_level == "DEBUG":
        # Development configuration with colored output
        processors: list[Processor] = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production configuration with JSON output
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, **initial_context: Any) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance with optional initial context.

    Creates a structlog bound logger that includes the module name
    and any additional context provided.

    Args:
        name: The name of the logger, typically __name__ of the calling module.
        **initial_context: Optional key-value pairs to bind to the logger.

    Returns:
        A configured structlog BoundLogger instance.

    Example:
        >>> logger = get_logger(__name__, service="task-queue")
        >>> logger.info("Processing task", task_id="abc-123")
        {"event": "Processing task", "task_id": "abc-123", "service": "task-queue", ...}
    """
    logger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger
