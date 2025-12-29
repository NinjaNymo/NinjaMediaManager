"""
Task streaming API endpoints
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

from backend.services.task_manager import task_manager

router = APIRouter()


@router.get("/stream")
async def stream_tasks():
    """
    Server-Sent Events endpoint for real-time task updates.
    Connect to this endpoint to receive live task logs and progress.
    """
    async def event_generator():
        async for event in task_manager.subscribe():
            data = json.dumps(event)
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/recent")
async def get_recent_tasks(limit: int = 10):
    """Get recent tasks and their logs"""
    return {"tasks": task_manager.get_recent_tasks(limit)}
