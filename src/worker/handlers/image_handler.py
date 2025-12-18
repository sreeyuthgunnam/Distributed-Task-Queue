"""
Image handler for the distributed task queue.

This module provides a simulated image resizing handler that demonstrates
how to implement a task handler for image processing operations.
"""

import asyncio
import hashlib
from typing import Any

from src.logging_config import get_logger

# Task name constant for registration
TASK_NAME = "resize_image"

# Module logger
logger = get_logger(__name__)


async def simulate_resize_image(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Simulate resizing an image.

    This is a demonstration handler that simulates image resizing
    with a 5-second delay. In a production system, this would
    integrate with an actual image processing library (Pillow, etc.)
    and cloud storage.

    Args:
        payload: Dictionary containing image parameters:
            - url (str): Source image URL (required)
            - width (int): Target width in pixels (required)
            - height (int): Target height in pixels (required)
            - format (str, optional): Output format (default: "jpeg")
            - quality (int, optional): Output quality 1-100 (default: 85)
            - preserve_aspect_ratio (bool, optional): Maintain aspect ratio (default: True)

    Returns:
        Dictionary containing:
            - success (bool): Whether the resize was successful
            - original_url (str): The original image URL
            - resized_url (str): URL of the resized image (simulated)
            - width (int): Final width
            - height (int): Final height
            - format (str): Output format
            - file_size_kb (int): Simulated file size in KB

    Raises:
        ValueError: If required fields (url, width, height) are missing.
        ValueError: If width or height is not a positive integer.

    Example:
        >>> result = await simulate_resize_image({
        ...     "url": "https://example.com/image.jpg",
        ...     "width": 800,
        ...     "height": 600
        ... })
        >>> print(result["resized_url"])
        https://cdn.example.com/resized/abc123_800x600.jpeg
    """
    log = logger.bind(
        handler="resize_image",
        source_url=payload.get("url"),
    )

    # Validate required fields
    required_fields = ["url", "width", "height"]
    missing_fields = [f for f in required_fields if f not in payload]

    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        log.error("Validation failed", missing_fields=missing_fields)
        raise ValueError(error_msg)

    url = payload["url"]
    width = payload["width"]
    height = payload["height"]
    output_format = payload.get("format", "jpeg")
    quality = payload.get("quality", 85)
    preserve_aspect_ratio = payload.get("preserve_aspect_ratio", True)

    # Validate dimensions
    if not isinstance(width, int) or width <= 0:
        raise ValueError(f"Width must be a positive integer, got {width}")
    if not isinstance(height, int) or height <= 0:
        raise ValueError(f"Height must be a positive integer, got {height}")
    if not isinstance(quality, int) or not 1 <= quality <= 100:
        raise ValueError(f"Quality must be an integer between 1 and 100, got {quality}")

    log.info(
        "Resizing image",
        target_width=width,
        target_height=height,
        format=output_format,
        quality=quality,
        preserve_aspect_ratio=preserve_aspect_ratio,
    )

    # Simulate image processing delay
    await asyncio.sleep(5)

    # Generate a simulated resized image URL
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    resized_url = f"https://cdn.example.com/resized/{url_hash}_{width}x{height}.{output_format}"

    # Simulate file size (roughly based on dimensions and quality)
    simulated_size_kb = int((width * height * 3 * quality / 100) / 1024 / 10)

    log.info(
        "Image resized successfully",
        resized_url=resized_url,
        file_size_kb=simulated_size_kb,
    )

    return {
        "success": True,
        "original_url": url,
        "resized_url": resized_url,
        "width": width,
        "height": height,
        "format": output_format,
        "quality": quality,
        "file_size_kb": simulated_size_kb,
        "preserve_aspect_ratio": preserve_aspect_ratio,
    }
