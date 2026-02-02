# /backend/app/utils/file_handler.py

import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.config import settings

def ensure_upload_dir():
    """Create upload directory if it doesn't exist"""
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path

def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        return False, f"File type {file_ext} not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
    
    return True, "Valid"

async def save_upload_file(file: UploadFile, tenant_id: str) -> tuple[str, str]:
    """Save uploaded file and return file path and filename"""
    # Validate file
    is_valid, message = validate_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    # Create upload directory
    upload_dir = ensure_upload_dir()
    
    # Create tenant-specific subdirectory
    tenant_dir = upload_dir / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = tenant_dir / unique_filename
    
    # Save file
    contents = await file.read()
    
    # Check file size
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE / (1024*1024)}MB"
        )
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    return str(file_path), file.filename

def delete_file(file_path: str):
    """Delete a file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        print(f"Error deleting file: {e}")
    return False

def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    return os.path.getsize(file_path)