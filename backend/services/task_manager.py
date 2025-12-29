"""
Task manager for tracking long-running operations and streaming logs
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import AsyncGenerator, Callable
import uuid


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LogEntry:
    timestamp: datetime
    message: str
    level: str = "info"  # info, warning, error, progress

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "level": self.level,
        }


@dataclass
class Task:
    id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0  # 0-100
    logs: list[LogEntry] = field(default_factory=list)
    result: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def log(self, message: str, level: str = "info"):
        entry = LogEntry(timestamp=datetime.now(), message=message, level=level)
        self.logs.append(entry)
        return entry

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "logs": [log.to_dict() for log in self.logs],
            "result": self.result,
            "created_at": self.created_at.isoformat(),
        }


class TaskManager:
    """Singleton task manager for tracking operations"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.tasks: dict[str, Task] = {}
        self.subscribers: list[asyncio.Queue] = []
        self._max_tasks = 50  # Keep last 50 tasks

    def create_task(self, name: str) -> Task:
        """Create a new task and return it"""
        task_id = str(uuid.uuid4())[:8]
        task = Task(id=task_id, name=name)
        self.tasks[task_id] = task

        # Cleanup old tasks if needed
        if len(self.tasks) > self._max_tasks:
            oldest = sorted(self.tasks.values(), key=lambda t: t.created_at)[0]
            del self.tasks[oldest.id]

        self._notify({"type": "task_created", "task": task.to_dict()})
        return task

    def log(self, task: Task, message: str, level: str = "info"):
        """Add a log entry to a task and notify subscribers"""
        entry = task.log(message, level)
        self._notify({
            "type": "log",
            "task_id": task.id,
            "entry": entry.to_dict(),
        })

    def update_progress(self, task: Task, progress: int, message: str = None):
        """Update task progress"""
        task.progress = min(100, max(0, progress))
        if message:
            self.log(task, message, "progress")
        self._notify({
            "type": "progress",
            "task_id": task.id,
            "progress": task.progress,
        })

    def complete_task(self, task: Task, result: dict = None):
        """Mark task as completed"""
        task.status = TaskStatus.COMPLETED
        task.progress = 100
        task.result = result or {}
        self.log(task, "Task completed", "info")
        self._notify({"type": "task_completed", "task": task.to_dict()})

    def fail_task(self, task: Task, error: str):
        """Mark task as failed"""
        task.status = TaskStatus.FAILED
        task.result = {"error": error}
        self.log(task, f"Task failed: {error}", "error")
        self._notify({"type": "task_failed", "task": task.to_dict()})

    def start_task(self, task: Task):
        """Mark task as running"""
        task.status = TaskStatus.RUNNING
        self._notify({"type": "task_started", "task": task.to_dict()})

    def _notify(self, event: dict):
        """Notify all subscribers of an event"""
        for queue in self.subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Skip if queue is full

    async def subscribe(self) -> AsyncGenerator[dict, None]:
        """Subscribe to task events"""
        queue = asyncio.Queue(maxsize=100)
        self.subscribers.append(queue)
        try:
            # Send current tasks on connect
            for task in list(self.tasks.values())[-10:]:
                yield {"type": "task_state", "task": task.to_dict()}

            while True:
                event = await queue.get()
                yield event
        finally:
            self.subscribers.remove(queue)

    def get_recent_tasks(self, limit: int = 10) -> list[dict]:
        """Get recent tasks"""
        tasks = sorted(self.tasks.values(), key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in tasks[:limit]]


# Global instance
task_manager = TaskManager()
