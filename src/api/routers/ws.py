"""
WebSocket API routes for real-time updates.

This module provides WebSocket endpoints for streaming task status
updates and dashboard statistics in real-time.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from src.api.dependencies import get_broker
from src.api.schemas import (
    WSTaskUpdate,
    WSDashboardUpdate,
    QueueStats,
    TaskStatusEnum,
)
from src.queue import TaskStatus
from src.worker import Worker
from src.worker.utils import get_worker_statistics
from src.logging_config import get_logger

router = APIRouter(prefix="/ws", tags=["WebSocket"])
logger = get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for broadcasting updates.
    
    Tracks active connections for task-specific and dashboard streams.
    """

    def __init__(self):
        # task_id -> list of websocket connections
        self.task_connections: dict[str, list[WebSocket]] = {}
        # list of dashboard websocket connections
        self.dashboard_connections: list[WebSocket] = []

    async def connect_task(self, websocket: WebSocket, task_id: str) -> None:
        """Accept and track a task-specific WebSocket connection."""
        await websocket.accept()
        if task_id not in self.task_connections:
            self.task_connections[task_id] = []
        self.task_connections[task_id].append(websocket)
        logger.debug("Task WebSocket connected", task_id=task_id)

    async def connect_dashboard(self, websocket: WebSocket) -> None:
        """Accept and track a dashboard WebSocket connection."""
        await websocket.accept()
        self.dashboard_connections.append(websocket)
        logger.debug("Dashboard WebSocket connected")

    def disconnect_task(self, websocket: WebSocket, task_id: str) -> None:
        """Remove a task-specific WebSocket connection."""
        if task_id in self.task_connections:
            if websocket in self.task_connections[task_id]:
                self.task_connections[task_id].remove(websocket)
            if not self.task_connections[task_id]:
                del self.task_connections[task_id]
        logger.debug("Task WebSocket disconnected", task_id=task_id)

    def disconnect_dashboard(self, websocket: WebSocket) -> None:
        """Remove a dashboard WebSocket connection."""
        if websocket in self.dashboard_connections:
            self.dashboard_connections.remove(websocket)
        logger.debug("Dashboard WebSocket disconnected")

    async def broadcast_task_update(self, task_id: str, data: dict) -> None:
        """Broadcast task update to all connections watching this task."""
        if task_id in self.task_connections:
            disconnected = []
            for websocket in self.task_connections[task_id]:
                try:
                    await websocket.send_json(data)
                except Exception:
                    disconnected.append(websocket)
            
            # Clean up disconnected sockets
            for ws in disconnected:
                self.disconnect_task(ws, task_id)

    async def broadcast_dashboard_update(self, data: dict) -> None:
        """Broadcast dashboard update to all connected clients."""
        disconnected = []
        for websocket in self.dashboard_connections:
            try:
                await websocket.send_json(data)
            except Exception:
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for ws in disconnected:
            self.disconnect_dashboard(ws)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/tasks/{task_id}")
async def websocket_task_updates(
    websocket: WebSocket,
    task_id: str,
):
    """
    WebSocket endpoint for real-time task status updates.
    
    Connects to receive updates for a specific task. The connection
    will receive JSON messages whenever the task status changes.
    
    Message format:
    ```json
    {
        "event": "task_update",
        "task_id": "uuid",
        "status": "pending|processing|completed|failed",
        "result": {...},  // if completed
        "error": "...",   // if failed
        "timestamp": "ISO8601"
    }
    ```
    
    The connection closes automatically when the task completes or fails.
    """
    # Validate task_id format
    try:
        UUID(task_id)
    except ValueError:
        await websocket.close(code=4000, reason="Invalid task ID format")
        return

    await manager.connect_task(websocket, task_id)
    
    try:
        # Get broker from app state
        broker = await get_broker(websocket)
        
        # Send initial task status
        task = await broker.get_task(UUID(task_id))
        if task:
            update = WSTaskUpdate(
                event="task_update",
                task_id=task_id,
                status=TaskStatusEnum(task.status.value),
                result=task.result,
                error=task.error,
                timestamp=datetime.now(timezone.utc),
            )
            await websocket.send_json(update.model_dump(mode="json"))
        
        # Poll for updates
        previous_status = task.status if task else None
        
        while True:
            await asyncio.sleep(0.5)  # Poll every 500ms
            
            task = await broker.get_task(UUID(task_id))
            if task is None:
                await websocket.send_json({
                    "event": "task_deleted",
                    "task_id": task_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                break
            
            # Send update if status changed
            if task.status != previous_status:
                update = WSTaskUpdate(
                    event="task_update",
                    task_id=task_id,
                    status=TaskStatusEnum(task.status.value),
                    result=task.result,
                    error=task.error,
                    timestamp=datetime.now(timezone.utc),
                )
                await websocket.send_json(update.model_dump(mode="json"))
                previous_status = task.status
            
            # Close connection if task is in terminal state
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                await asyncio.sleep(1)  # Give client time to receive final update
                break

    except WebSocketDisconnect:
        logger.debug("Task WebSocket client disconnected", task_id=task_id)
    except Exception as e:
        logger.error("Task WebSocket error", task_id=task_id, error=str(e))
    finally:
        manager.disconnect_task(websocket, task_id)


@router.websocket("/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard statistics.
    
    Streams queue and worker statistics every second.
    
    Message format:
    ```json
    {
        "event": "dashboard_update",
        "queues": [
            {
                "queue_name": "default",
                "pending": 10,
                "processing": 2,
                "completed": 100,
                "failed": 5,
                "total": 117,
                "paused": false
            }
        ],
        "workers": {
            "total": 3,
            "active": 2,
            "busy": 1
        },
        "timestamp": "ISO8601"
    }
    ```
    """
    await manager.connect_dashboard(websocket)
    
    try:
        # Get broker from app state
        broker = await get_broker(websocket)
        
        while True:
            try:
                # Gather queue statistics
                queue_names = set()
                cursor = 0
                while True:
                    cursor, keys = await broker.client.scan(
                        cursor=cursor,
                        match="queue:*:*",
                        count=100,
                    )
                    for key in keys:
                        parts = key.split(":")
                        if len(parts) >= 3:
                            queue_name = parts[1]
                            if not queue_name.endswith(":dlq"):
                                queue_names.add(queue_name)
                    if cursor == 0:
                        break
                
                queue_names.add("default")
                
                queues: list[QueueStats] = []
                for queue_name in sorted(queue_names):
                    stats = await broker.get_queue_stats(queue_name)
                    paused = await broker.client.sismember("queues:paused", queue_name)
                    queues.append(QueueStats(
                        queue_name=stats.queue_name,
                        pending=stats.pending,
                        processing=stats.processing,
                        completed=stats.completed,
                        failed=stats.failed,
                        total=stats.total,
                        paused=bool(paused),
                    ))
                
                # Gather worker statistics
                worker_stats = await get_worker_statistics(broker)
                
                # Send update
                update = WSDashboardUpdate(
                    event="dashboard_update",
                    queues=queues,
                    workers={
                        "total": worker_stats["total_workers"],
                        "active": worker_stats["active_workers"],
                        "idle": worker_stats["idle_workers"],
                        "busy": worker_stats["busy_workers"],
                    },
                    timestamp=datetime.now(timezone.utc),
                )
                
                await websocket.send_json(update.model_dump(mode="json"))
                
            except WebSocketDisconnect:
                # Client disconnected, exit gracefully
                break
            except Exception as e:
                # Only log actual errors, not disconnections
                if "close" not in str(e).lower():
                    logger.error("Error gathering dashboard data", error=str(e))
                break
            
            await asyncio.sleep(1)  # Update every second

    except WebSocketDisconnect:
        pass  # Normal disconnect, no need to log
    except Exception as e:
        logger.error("Dashboard WebSocket error", error=str(e))
    finally:
        manager.disconnect_dashboard(websocket)
