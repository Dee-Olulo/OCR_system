# /backend/app/routes/documents.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.models.document import DocumentResponse
from app.utils.security import get_current_user
from app.utils.file_handler import save_upload_file, delete_file
from app.database import get_database
from app.services.ocr_service import ocr_service

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a document (image)
    
    - Supported formats: JPG, JPEG, PNG, TIFF
    - Max file size: 10MB
    """
    db = get_database()
    
    # Save file
    file_path, original_filename = await save_upload_file(file, current_user["tenant_id"])
    
    # Create document record
    document_dict = {
        "tenant_id": current_user["tenant_id"],
        "user_id": str(current_user["_id"]),
        "filename": original_filename,
        "original_path": file_path,
        "file_type": file.content_type or "image/jpeg",
        "file_size": len(await file.read()),
        "status": "pending",
        "uploaded_at": datetime.utcnow()
    }
    
    # Reset file pointer
    await file.seek(0)
    
    result = await db.documents.insert_one(document_dict)
    document_dict["_id"] = result.inserted_id
    
    return DocumentResponse(
        id=str(result.inserted_id),
        filename=original_filename,
        file_type=document_dict["file_type"],
        file_size=document_dict["file_size"],
        status="pending",
        uploaded_at=document_dict["uploaded_at"]
    )

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List user's documents with pagination
    
    - **skip**: Number of documents to skip
    - **limit**: Number of documents to return (max 100)
    - **status**: Filter by status (pending, processing, completed, failed)
    """
    db = get_database()
    
    # Build query
    query = {"tenant_id": current_user["tenant_id"]}
    if status:
        query["status"] = status
    
    # Get documents
    cursor = db.documents.find(query).sort("uploaded_at", -1).skip(skip).limit(limit)
    documents = await cursor.to_list(length=limit)
    
    return [
        DocumentResponse(
            id=str(doc["_id"]),
            filename=doc["filename"],
            file_type=doc["file_type"],
            file_size=doc["file_size"],
            status=doc["status"],
            uploaded_at=doc["uploaded_at"],
            extracted_text=doc.get("extracted_text")
        )
        for doc in documents
    ]

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get document details by ID"""
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    # Get document
    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "tenant_id": current_user["tenant_id"]
    })
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=str(document["_id"]),
        filename=document["filename"],
        file_type=document["file_type"],
        file_size=document["file_size"],
        status=document["status"],
        uploaded_at=document["uploaded_at"],
        extracted_text=document.get("extracted_text")
    )

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Download original document file"""
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    # Get document
    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "tenant_id": current_user["tenant_id"]
    })
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = document["original_path"]
    
    return FileResponse(
        path=file_path,
        filename=document["filename"],
        media_type=document["file_type"]
    )

@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a document"""
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    # Get document
    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "tenant_id": current_user["tenant_id"]
    })
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file
    delete_file(document["original_path"])
    
    # Delete document record
    await db.documents.delete_one({"_id": ObjectId(document_id)})
    
    return None

@router.get("/{document_id}/stats")
async def get_document_stats(current_user: dict = Depends(get_current_user)):
    """Get document statistics for current user"""
    db = get_database()
    
    # Count documents by status
    pipeline = [
        {"$match": {"tenant_id": current_user["tenant_id"]}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    result = await db.documents.aggregate(pipeline).to_list(None)
    
    stats = {
        "total": 0,
        "pending": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0
    }
    
    for item in result:
        stats[item["_id"]] = item["count"]
        stats["total"] += item["count"]
    
    return stats