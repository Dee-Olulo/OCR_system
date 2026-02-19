# /backend/app/routes/llm_extraction.py

from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime
from app.utils.security import get_current_user
from app.database import get_database
from app.services.llm_extraction_service import llm_extraction_service
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Extraction"])


@router.post("/extract/{document_id}")
async def extract_with_llm(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Phase 2: Takes already-extracted OCR text and sends it to
    Llama3.2 via Ollama to extract structured invoice fields.
    """
    db = get_database()

    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")

    # Get document
    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "tenant_id": current_user["tenant_id"]
    })

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Must have OCR text first
    ocr_text = document.get("extracted_text", "").strip()
    if not ocr_text:
        raise HTTPException(
            status_code=400,
            detail="No extracted text found. Run OCR first via /ocr/process/{document_id}"
        )

    # Check Ollama is running
    if not llm_extraction_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama is not running. Start it with: ollama serve"
        )

    logger.info(f"Running LLM extraction for document: {document_id}")

    # Extract structured fields
    extracted_fields = await llm_extraction_service.extract_invoice_fields(ocr_text)

    # Save results back to the document
    await db.documents.update_one(
        {"_id": ObjectId(document_id)},
        {
            "$set": {
                "llm_extracted_fields": extracted_fields,
                "llm_processed_at": datetime.utcnow(),
                "llm_model": "llama3.2:3b"
            }
        }
    )

    return {
        "document_id": document_id,
        "status": "success",
        "model": "llama3.2:3b",
        "extracted_fields": extracted_fields
    }


@router.get("/result/{document_id}")
async def get_llm_result(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get previously extracted LLM fields for a document"""
    db = get_database()

    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")

    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "tenant_id": current_user["tenant_id"]
    })

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    llm_fields = document.get("llm_extracted_fields")
    if not llm_fields:
        raise HTTPException(
            status_code=404,
            detail="No LLM results found. Run /llm/extract/{document_id} first"
        )

    return {
        "document_id": document_id,
        "model": document.get("llm_model", "llama3.2:3b"),
        "processed_at": document.get("llm_processed_at"),
        "extracted_fields": llm_fields
    }