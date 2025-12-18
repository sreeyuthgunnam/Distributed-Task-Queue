"""
Data processing handler for the distributed task queue.

This module provides a simulated data processing handler that demonstrates
how to implement a task handler for data transformation operations.
"""

import asyncio
from typing import Any

from src.logging_config import get_logger

# Task name constant for registration
TASK_NAME = "process_data"

# Module logger
logger = get_logger(__name__)


async def simulate_data_processing(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Simulate processing data records.

    This is a demonstration handler that simulates data processing
    with a 3-second delay. In a production system, this would
    perform actual data transformations, ETL operations, or
    analytics computations.

    Args:
        payload: Dictionary containing data processing parameters:
            - data (list | dict): Data to process (required)
            - operation (str, optional): Processing operation type
                Options: "transform", "aggregate", "filter", "validate"
                Default: "transform"
            - options (dict, optional): Operation-specific options
            - output_format (str, optional): Output format ("json", "csv", "parquet")
                Default: "json"

    Returns:
        Dictionary containing:
            - success (bool): Whether processing was successful
            - operation (str): The operation performed
            - input_count (int): Number of input records
            - output_count (int): Number of output records
            - processed_count (int): Number of records processed
            - skipped_count (int): Number of records skipped
            - error_count (int): Number of records with errors
            - output_format (str): Output format used
            - processing_time_ms (int): Simulated processing time

    Raises:
        ValueError: If required field (data) is missing.
        ValueError: If data is not a list or dict.

    Example:
        >>> result = await simulate_data_processing({
        ...     "data": [{"id": 1, "value": 100}, {"id": 2, "value": 200}],
        ...     "operation": "transform",
        ...     "options": {"multiply_by": 2}
        ... })
        >>> print(result["processed_count"])
        2
    """
    log = logger.bind(handler="process_data")

    # Validate required fields
    if "data" not in payload:
        error_msg = "Missing required field: data"
        log.error("Validation failed", error=error_msg)
        raise ValueError(error_msg)

    data = payload["data"]
    operation = payload.get("operation", "transform")
    options = payload.get("options", {})
    output_format = payload.get("output_format", "json")

    # Validate data type
    if not isinstance(data, (list, dict)):
        raise ValueError(f"Data must be a list or dict, got {type(data).__name__}")

    # Calculate input count
    if isinstance(data, list):
        input_count = len(data)
    else:
        input_count = 1  # Single record

    log.info(
        "Processing data",
        operation=operation,
        input_count=input_count,
        output_format=output_format,
        options=options,
    )

    # Simulate data processing delay
    await asyncio.sleep(3)

    # Simulate processing results
    # In a real system, this would perform actual data operations
    processed_count = input_count
    skipped_count = 0
    error_count = 0

    # Simulate some records being skipped or having errors
    if input_count > 10:
        skipped_count = input_count // 20  # ~5% skipped
        error_count = input_count // 50  # ~2% errors
        processed_count = input_count - skipped_count - error_count

    # Simulate output count (might differ for aggregate operations)
    if operation == "aggregate":
        output_count = 1  # Aggregation produces single result
    elif operation == "filter":
        output_count = int(processed_count * 0.7)  # ~70% pass filter
    else:
        output_count = processed_count

    # Simulated processing time based on data size
    processing_time_ms = input_count * 10 + 100  # 10ms per record + 100ms overhead

    log.info(
        "Data processing completed",
        processed_count=processed_count,
        output_count=output_count,
        skipped_count=skipped_count,
        error_count=error_count,
        processing_time_ms=processing_time_ms,
    )

    return {
        "success": True,
        "operation": operation,
        "input_count": input_count,
        "output_count": output_count,
        "processed_count": processed_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "output_format": output_format,
        "processing_time_ms": processing_time_ms,
        "options_applied": options,
    }
