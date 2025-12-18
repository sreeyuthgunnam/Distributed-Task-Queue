"""
Email handler for the distributed task queue.

This module provides a simulated email sending handler that demonstrates
how to implement a task handler for email-related operations.
"""

import asyncio
from typing import Any

from src.logging_config import get_logger

# Task name constant for registration
TASK_NAME = "send_email"

# Module logger
logger = get_logger(__name__)


async def simulate_send_email(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Simulate sending an email.

    This is a demonstration handler that simulates email sending
    with a 2-second delay. In a production system, this would
    integrate with an actual email service (SMTP, SendGrid, etc.).

    Args:
        payload: Dictionary containing email parameters:
            - to (str): Recipient email address (required)
            - subject (str): Email subject line (required)
            - body (str): Email body content (required)
            - cc (list[str], optional): CC recipients
            - bcc (list[str], optional): BCC recipients
            - attachments (list[str], optional): Attachment URLs

    Returns:
        Dictionary containing:
            - success (bool): Whether the email was sent successfully
            - message_id (str): Simulated message ID
            - recipient (str): The recipient email address
            - subject (str): The email subject

    Raises:
        ValueError: If required fields (to, subject, body) are missing.

    Example:
        >>> result = await simulate_send_email({
        ...     "to": "user@example.com",
        ...     "subject": "Hello!",
        ...     "body": "This is a test email."
        ... })
        >>> print(result["success"])
        True
    """
    log = logger.bind(
        handler="send_email",
        recipient=payload.get("to"),
    )

    # Validate required fields
    required_fields = ["to", "subject", "body"]
    missing_fields = [f for f in required_fields if f not in payload]

    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        log.error("Validation failed", missing_fields=missing_fields)
        raise ValueError(error_msg)

    to_address = payload["to"]
    subject = payload["subject"]
    body = payload["body"]
    cc = payload.get("cc", [])
    bcc = payload.get("bcc", [])
    attachments = payload.get("attachments", [])

    log.info(
        "Sending email",
        subject=subject,
        cc_count=len(cc),
        bcc_count=len(bcc),
        attachment_count=len(attachments),
    )

    # Simulate email sending delay
    await asyncio.sleep(2)

    # Generate a simulated message ID
    import uuid
    message_id = f"msg_{uuid.uuid4().hex[:12]}"

    log.info(
        "Email sent successfully",
        message_id=message_id,
    )

    return {
        "success": True,
        "message_id": message_id,
        "recipient": to_address,
        "subject": subject,
        "cc_count": len(cc),
        "bcc_count": len(bcc),
        "attachment_count": len(attachments),
    }
