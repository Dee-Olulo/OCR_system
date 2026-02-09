# /backend/app/routes/task_routes.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from app.utils.security import get_current_user
from app.database import get_database
from app.services.background_task_service import background_task_service, TaskStatus
from bson import ObjectId

router = APIRouter(prefix="/tasks", tags=["Background Tasks"])

@router.get("/")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=100),
    current_user: dict = Depends(get_current_user)
):
    """List all background tasks for the current user"""
    db = get_database()
    
    # Build query
    query = {"tenant_id": current_user["tenant_id"]}
    if status:
        query["status"] = status
    
    # Get tasks from database
    tasks = await db.tasks.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "tasks": tasks,
        "total": len(tasks)
    }

@router.get("/{task_id}")
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific task by ID"""
    db = get_database()
    
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    task = await db.tasks.find_one({
        "_id": ObjectId(task_id),
        "tenant_id": current_user["tenant_id"]
    })
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task

@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a task"""
    db = get_database()
    
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    result = await db.tasks.delete_one({
        "_id": ObjectId(task_id),
        "tenant_id": current_user["tenant_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted successfully"}

@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Retry a failed task"""
    db = get_database()
    
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")
    
    task = await db.tasks.find_one({
        "_id": ObjectId(task_id),
        "tenant_id": current_user["tenant_id"]
    })
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] != "failed":
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")
    
    # Reset task status
    await db.tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {
            "status": "pending",
            "error": None,
            "retry_count": task.get("retry_count", 0) + 1,
            "retried_at": datetime.utcnow()
        }}
    )
    
    # Add back to queue (you would implement this based on your task type)
    # For example, if it's a document processing task:
    if task["task_type"] == "document_processing":
        background_task_service.add_task(
            str(task["_id"]),
            task["task_type"],
            task["data"]
        )
    
    return {"message": "Task queued for retry"}

@router.get("/stats/summary")
async def get_task_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get task statistics"""
    db = get_database()
    
    # Count tasks by status
    pipeline = [
        {"$match": {"tenant_id": current_user["tenant_id"]}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    results = await db.tasks.aggregate(pipeline).to_list(10)
    
    stats = {
        "total": 0,
        "pending": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0
    }
    
    for result in results:
        status = result["_id"]
        count = result["count"]
        stats[status] = count
        stats["total"] += count
    
    return stats

@router.post("/batch/cancel")
async def cancel_pending_tasks(
    current_user: dict = Depends(get_current_user)
):
    """Cancel all pending tasks"""
    db = get_database()
    
    result = await db.tasks.update_many(
        {
            "tenant_id": current_user["tenant_id"],
            "status": "pending"
        },
        {"$set": {
            "status": "cancelled",
            "cancelled_at": datetime.utcnow()
        }}
    )
    
    return {
        "message": f"Cancelled {result.modified_count} pending tasks",
        "count": result.modified_count
    }

@router.delete("/batch/cleanup")
async def cleanup_old_tasks(
    days: int = Query(30, description="Delete tasks older than N days"),
    current_user: dict = Depends(get_current_user)
):
    """Delete old completed/failed tasks"""
    from datetime import timedelta
    
    db = get_database()
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.tasks.delete_many({
        "tenant_id": current_user["tenant_id"],
        "status": {"$in": ["completed", "failed"]},
        "created_at": {"$lt": cutoff_date}
    })
    
    return {
        "message": f"Deleted {result.deleted_count} old tasks",
        "count": result.deleted_count
    }