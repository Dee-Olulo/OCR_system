# /backend/app/routes/ocr.py

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from datetime import datetime
from app.models.document import OCRResult
from app.utils.security import get_current_user
from app.database import get_database
from app.services.ocr_service import ocr_service

router = APIRouter(prefix="/ocr", tags=["OCR Processing"])

@router.post("/process/{document_id}", response_model=OCRResult)
async def process_document(
    document_id: str,
    engine: str = Query("tesseract", regex="^(tesseract|easyocr|both)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Process document with OCR
    
    - **document_id**: Document ID to process
    - **engine**: OCR engine to use (tesseract, easyocr, or both)
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
    
    # Update status to processing
    await db.documents.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"status": "processing"}}
    )
    
    try:
        # Process with OCR
        if engine == "both":
            result = ocr_service.extract_text_both(document["original_path"])
            ocr_result = result["best_result"]
        else:
            ocr_result = ocr_service.extract_text(document["original_path"], engine)
        
        if not ocr_result["success"]:
            # Update status to failed
            await db.documents.update_one(
                {"_id": ObjectId(document_id)},
                {
                    "$set": {
                        "status": "failed",
                        "processed_at": datetime.utcnow()
                    }
                }
            )
            raise HTTPException(
                status_code=500,
                detail=f"OCR processing failed: {ocr_result['error']}"
            )
        
        # Update document with results
        await db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "status": "completed",
                    "extracted_text": ocr_result["text"],
                    "ocr_engine": ocr_result["ocr_engine"],
                    "language": "en",
                    "confidence_score": ocr_result["confidence"],
                    "processed_at": datetime.utcnow()
                }
            }
        )
        
        return OCRResult(
            document_id=document_id,
            extracted_text=ocr_result["text"],
            language="en",
            confidence_score=ocr_result["confidence"],
            ocr_engine=ocr_result["ocr_engine"],
            processing_time=ocr_result["processing_time"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        # Update status to failed
        await db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "status": "failed",
                    "processed_at": datetime.utcnow()
                }
            }
        )
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@router.get("/result/{document_id}")
async def get_ocr_result(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get OCR result for a processed document"""
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
    
    if document["status"] != "completed":
        return {
            "document_id": document_id,
            "status": document["status"],
            "message": f"Document is {document['status']}"
        }
    
    return {
        "document_id": document_id,
        "status": "completed",
        "extracted_text": document.get("extracted_text", ""),
        "language": document.get("language", "en"),
        "confidence_score": document.get("confidence_score", 0.0),
        "ocr_engine": document.get("ocr_engine", "unknown"),
        "processed_at": document.get("processed_at")
    }