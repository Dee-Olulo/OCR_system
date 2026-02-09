from typing import Dict, List
import asyncio
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class BackgroundTask:
    """Represents a background processing task"""
    
    def __init__(self, task_id: str, task_type: str, data: dict):
        self.task_id = task_id
        self.task_type = task_type
        self.data = data
        self.status = TaskStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.error = None
        self.result = None

class BackgroundTaskService:
    """Service to manage background tasks"""
    
    def __init__(self):
        self.tasks: Dict[str, BackgroundTask] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.worker_task = None
    
    def add_task(self, task_id: str, task_type: str, data: dict) -> BackgroundTask:
        """Add a task to the queue"""
        task = BackgroundTask(task_id, task_type, data)
        self.tasks[task_id] = task
        self.queue.put_nowait(task)
        return task
    
    def get_task(self, task_id: str) -> BackgroundTask:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[BackgroundTask]:
        """Get all tasks"""
        return list(self.tasks.values())
    
    def get_pending_tasks(self) -> List[BackgroundTask]:
        """Get pending tasks"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
    
    async def start_worker(self, process_func):
        """Start background worker"""
        self.worker_task = asyncio.create_task(self._worker(process_func))
    
    async def _worker(self, process_func):
        """Background worker loop"""
        while True:
            try:
                task = await self.queue.get()
                
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.utcnow()
                
                try:
                    result = await process_func(task)
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                
                task.completed_at = datetime.utcnow()
                
            except Exception as e:
                print(f"Worker error: {e}")

# Global instance
background_task_service = BackgroundTaskService()