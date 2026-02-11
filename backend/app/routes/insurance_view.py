# /backend/app/routes/insurance_view.py

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from typing import Optional
from app.utils.security import get_current_user
from app.database import get_database
from app.services.insurance_fields_extractor import insurance_fields_extractor

router = APIRouter(prefix="/insurance", tags=["Insurance View"])

@router.get("/view/{document_id}")
async def get_insurance_view(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get standardized insurance claim view from any hospital invoice.
    Extracts only the critical fields needed for insurance processing.
    """
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
    
    # Check if document has been processed
    if document.get("status") != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Document not yet processed. Current status: {document.get('status', 'unknown')}"
        )
    
    # Get JSON output
    json_output = document.get("json_output")
    
    if not json_output:
        raise HTTPException(
            status_code=404, 
            detail="No OCR output found for this document"
        )
    
    # Extract insurance fields
    insurance_data = insurance_fields_extractor.extract_insurance_fields(json_output)
    
    # Add document metadata
    insurance_data["document_info"] = {
        "document_id": str(document["_id"]),
        "filename": document.get("filename"),
        "upload_date": document.get("uploaded_at"),
        "processed_date": document.get("processed_at"),
        "ocr_engine": document.get("ocr_engine", "unknown")
    }
    
    return insurance_data


@router.get("/batch-view")
async def get_batch_insurance_view(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get insurance view for multiple documents (batch processing).
    Useful for reviewing multiple claims at once.
    """
    db = get_database()
    
    # Count total completed documents with JSON output
    total_count = await db.documents.count_documents({
        "tenant_id": current_user["tenant_id"],
        "status": "completed",
        "json_output": {"$exists": True}
    })
    
    # Get completed documents with pagination
    cursor = db.documents.find({
        "tenant_id": current_user["tenant_id"],
        "status": "completed",
        "json_output": {"$exists": True}
    }).sort("processed_at", -1).skip(skip).limit(limit)
    
    documents = await cursor.to_list(length=limit)
    
    batch_results = []
    
    for document in documents:
        try:
            json_output = document.get("json_output", {})
            insurance_data = insurance_fields_extractor.extract_insurance_fields(json_output)
            
            # Add document info
            insurance_data["document_info"] = {
                "document_id": str(document["_id"]),
                "filename": document.get("filename"),
                "upload_date": document.get("uploaded_at"),
                "processed_date": document.get("processed_at"),
                "ocr_engine": document.get("ocr_engine", "unknown")
            }
            
            batch_results.append(insurance_data)
        except Exception as e:
            # Log error but continue processing other documents
            print(f"Error processing document {document['_id']}: {e}")
            continue
    
    return {
        "claims": batch_results,
        "total": total_count,  # Total number of documents available
        "skip": skip,
        "limit": limit,
        "count": len(batch_results)  # Number of documents in current page
    }