"""
Worker entrypoint for the distributed task queue.

This module provides the CLI interface for starting worker instances,
handling signal interrupts for graceful shutdown, and auto-discovering
task handlers from the handlers directory.

Usage:
    python -m src.worker.main --worker-id worker-1 --queues default,high-priority --concurrency 2

Arguments:
    --worker-id: Unique identifier for this worker instance
    --queues: Comma-separated list of queues to process (in priority order)
    --concurrency: Number of concurrent tasks to process (default: 1)
    --log-level: Logging level (DEBUG, INFO, WARNING, ERROR)
"""

import argparse
import asyncio
import importlib
import inspect
import os
import pkgutil
import signal
import sys
from typing import Any, Callable, Coroutine
from uuid import uuid4

from src.config import get_settings
from src.logging_config import configure_logging, get_logger
from src.queue import RedisBroker
from src.worker import Worker

# Type alias for task handler functions
TaskHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed argument namespace containing:
            - worker_id: Worker identifier
            - queues: List of queue names
            - concurrency: Number of concurrent tasks
            - log_level: Logging level
    """
    parser = argparse.ArgumentParser(
        description="Start a distributed task queue worker",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--worker-id",
        type=str,
        default=None,
        help="Unique identifier for this worker. If not provided, a UUID will be generated.",
    )

    parser.add_argument(
        "--queues",
        type=str,
        default="default",
        help="Comma-separated list of queues to process (in priority order).",
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent tasks to process.",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level.",
    )

    return parser.parse_args()


def discover_handlers() -> dict[str, TaskHandler]:
    """
    Auto-discover task handlers from the handlers directory.

    Scans the src.worker.handlers package for modules containing
    TASK_NAME constant and a corresponding handler function.

    Convention:
        - Each handler module should define a TASK_NAME constant
        - Handler function should be the primary async function in the module
        - Handler function should accept a dict payload and return a dict result

    Returns:
        Dictionary mapping task names to handler functions.

    Example:
        >>> handlers = discover_handlers()
        >>> print(handlers.keys())
        dict_keys(['send_email', 'resize_image', 'process_data'])
    """
    handlers: dict[str, TaskHandler] = {}

    # Import the handlers package
    try:
        import src.worker.handlers as handlers_package
    except ImportError:
        return handlers

    # Get the package path
    package_path = os.path.dirname(handlers_package.__file__)

    # Iterate through modules in the handlers package
    for _, module_name, is_pkg in pkgutil.iter_modules([package_path]):
        if is_pkg:
            continue  # Skip sub-packages

        if module_name.startswith("_"):
            continue  # Skip private modules

        try:
            # Import the module
            module = importlib.import_module(f"src.worker.handlers.{module_name}")

            # Check for TASK_NAME constant
            task_name = getattr(module, "TASK_NAME", None)
            if task_name is None:
                continue

            # Find the handler function
            # Convention: look for async functions that aren't private
            handler = None
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.iscoroutinefunction(obj)
                    and not name.startswith("_")
                    and name != "TASK_NAME"
                ):
                    handler = obj
                    break

            if handler:
                handlers[task_name] = handler

        except Exception as e:
            # Log but don't fail on individual module errors
            print(f"Warning: Failed to load handler from {module_name}: {e}")

    return handlers


async def run_worker(
    worker_id: str,
    queues: list[str],
    concurrency: int,
) -> None:
    """
    Initialize and run the worker.

    Sets up the broker connection, registers handlers, and starts
    the worker processing loop.

    Args:
        worker_id: Unique identifier for this worker.
        queues: List of queue names to process.
        concurrency: Number of concurrent tasks.
    """
    logger = get_logger(__name__)

    settings = get_settings()
    broker = RedisBroker(settings)

    # Connect to Redis
    logger.info("Connecting to Redis", url=settings.redis_url)
    await broker.connect()

    try:
        # Create worker
        worker = Worker(
            worker_id=worker_id,
            queues=queues,
            broker=broker,
            concurrency=concurrency,
            settings=settings,
        )

        # Auto-discover and register handlers
        handlers = discover_handlers()
        for task_name, handler in handlers.items():
            worker.add_handler(task_name, handler)

        logger.info(
            "Worker initialized",
            worker_id=worker_id,
            queues=queues,
            concurrency=concurrency,
            handlers=list(handlers.keys()),
        )

        # Setup signal handlers for graceful shutdown
        shutdown_event = asyncio.Event()

        def signal_handler(sig: signal.Signals) -> None:
            logger.info("Received shutdown signal", signal=sig.name)
            shutdown_event.set()

        # Register signal handlers
        loop = asyncio.get_running_loop()

        # Handle SIGTERM and SIGINT
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                # Use alternative approach
                signal.signal(sig, lambda s, f, sig=sig: signal_handler(sig))

        # Start worker in background task
        worker_task = asyncio.create_task(worker.start())

        # Wait for shutdown signal
        await shutdown_event.wait()

        # Initiate graceful shutdown
        logger.info("Initiating graceful shutdown")
        await worker.graceful_shutdown()

        # Wait for worker to finish
        await worker_task

    except Exception as e:
        logger.error("Worker error", error=str(e), exc_info=True)
        raise

    finally:
        # Disconnect from Redis
        await broker.disconnect()
        logger.info("Worker shutdown complete")


def main() -> None:
    """
    Main entry point for the worker CLI.

    Parses arguments, configures logging, and starts the worker
    in the asyncio event loop.
    """
    args = parse_args()

    # Override log level in settings if specified
    if args.log_level:
        os.environ["LOG_LEVEL"] = args.log_level

    # Configure logging
    configure_logging()

    logger = get_logger(__name__)

    # Generate worker ID if not provided
    worker_id = args.worker_id or f"worker-{uuid4().hex[:8]}"

    # Parse queues
    queues = [q.strip() for q in args.queues.split(",") if q.strip()]

    if not queues:
        logger.error("No queues specified")
        sys.exit(1)

    logger.info(
        "Starting worker",
        worker_id=worker_id,
        queues=queues,
        concurrency=args.concurrency,
    )

    try:
        # Run the worker
        asyncio.run(run_worker(worker_id, queues, args.concurrency))
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error("Worker failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
