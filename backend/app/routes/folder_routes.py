from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.utils.security import get_current_user
from app.database import get_database
from app.services.folder_monitor_service import folder_monitor_service
from datetime import datetime
import uuid

router = APIRouter(prefix="/folders", tags=["Folder Monitoring"])

class FolderCreate(BaseModel):
    name: str
    path: str
    auto_process: bool = True

@router.post("/")
async def create_folder(
    folder_data: FolderCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a monitored folder"""
    db = get_database()
    
    folder_id = str(uuid.uuid4())
    
    folder_doc = {
        "_id": folder_id,
        "user_id": current_user["_id"],
        "tenant_id": current_user["tenant_id"],
        "name": folder_data.name,
        "path": folder_data.path,
        "auto_process": folder_data.auto_process,
        "is_monitoring": False,
        "created_at": datetime.utcnow()
    }
    
    await db.folders.insert_one(folder_doc)
    
    return {"folder_id": folder_id, "message": "Folder created"}

@router.get("/")
async def list_folders(current_user: dict = Depends(get_current_user)):
    """List all monitored folders"""
    db = get_database()
    
    folders = await db.folders.find({
        "tenant_id": current_user["tenant_id"]
    }).to_list(100)
    
    return {"folders": folders}

@router.post("/{folder_id}/start")
async def start_monitoring(
    folder_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Start monitoring a folder"""
    db = get_database()
    
    folder = await db.folders.find_one({"_id": folder_id})
    if not folder:
        raise HTTPException(404, "Folder not found")
    
    # Callback function for new files
    async def on_new_file(folder_id: str, file_path: str):
        # Auto-upload and process logic here
        print(f"New file detected: {file_path}")
        # You would implement auto-upload logic here
    
    await folder_monitor_service.start_monitoring(
        folder_id, 
        folder["path"],
        on_new_file
    )
    
    await db.folders.update_one(
        {"_id": folder_id},
        {"$set": {"is_monitoring": True}}
    )
    
    return {"message": "Monitoring started"}

@router.post("/{folder_id}/stop")
async def stop_monitoring(
    folder_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Stop monitoring a folder"""
    db = get_database()
    
    await folder_monitor_service.stop_monitoring(folder_id)
    
    await db.folders.update_one(
        {"_id": folder_id},
        {"$set": {"is_monitoring": False}}
    )
    
    return {"message": "Monitoring stopped"}