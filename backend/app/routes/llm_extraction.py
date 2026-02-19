# /backend/app/routes/llm_extraction.py

"""
Phase 3 extraction route.

Pipeline:
  OCR text
    → LLM → canonical schema        (llm_extraction_service)
    → normalize                      (normalization)
    → map to insurer fields          (mapping_engine)
    → validate required fields       (mapping_engine)
    → persist + return
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from datetime import datetime
from app.utils.security import get_current_user
from app.database import get_database
from app.services.llm_extraction_service import llm_extraction_service
from app.services.normalization import normalize_canonical
from app.services.mapping_engine import insurer_mapper
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Extraction"])

CURRENT_MODEL = "llama3.2:3b"


@router.post("/extract/{document_id}")
async def extract_with_llm(
    document_id: str,
    insurer: str = Query(
        None,
        description="Insurer key: masm or nico. Auto-detected from document if not provided."
    ),
    current_user: dict = Depends(get_current_user)
):
    """
    Full Phase 3 extraction pipeline:
    OCR text → canonical LLM extraction → normalize → insurer mapping → validation
    """
    db = get_database()

    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")

    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "tenant_id": current_user["tenant_id"]
    })

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    ocr_text = document.get("extracted_text", "").strip()
    if not ocr_text:
        raise HTTPException(
            status_code=400,
            detail="No OCR text found. Run /ocr/process/{document_id} first."
        )

    if not llm_extraction_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama is not running. Start with: ollama serve"
        )

    # ── Step 1: LLM → canonical schema ───────────────────────────────────────
    logger.info(f"Step 1: LLM extraction | document={document_id}")
    canonical = await llm_extraction_service.extract_to_canonical(ocr_text)

    if canonical.get("error") or canonical.get("fallback"):
        raise HTTPException(
            status_code=500,
            detail=f"LLM extraction failed: {canonical.get('error')}"
        )

    # ── Step 2: Detect insurer if not provided ────────────────────────────────
    insurer_key = insurer.lower() if insurer else None

    if not insurer_key:
        insurer_key = insurer_mapper.detect_insurer(canonical)

    if not insurer_key:
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not detect insurer from document. "
                "Pass ?insurer=masm or ?insurer=nico explicitly."
            )
        )

    # Validate the insurer key exists
    available = insurer_mapper.list_available()
    if insurer_key not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown insurer '{insurer_key}'. Available: {available}"
        )

    # ── Step 3: Normalize canonical fields ───────────────────────────────────
    logger.info(f"Step 2: Normalizing | insurer={insurer_key}")
    insurer_config = insurer_mapper.load_config(insurer_key)
    date_format = insurer_config.get("date_format", "%d/%m/%Y")
    normalized = normalize_canonical(canonical, date_format=date_format)

    # ── Step 4: Map to insurer-specific fields + validate ────────────────────
    logger.info(f"Step 3: Mapping to {insurer_key} schema")
    result = insurer_mapper.process(normalized, insurer_key)

    # ── Step 5: Persist everything ───────────────────────────────────────────
    await db.documents.update_one(
        {"_id": ObjectId(document_id)},
        {
            "$set": {
                "canonical_fields":          canonical,
                "normalized_fields":         normalized,
                "mapped_fields":             result["mapped_fields"],
                "insurer_key":               insurer_key,
                "insurer_display_name":      result["insurer_display_name"],
                "missing_required_fields":   result["missing_fields"],
                "extraction_complete":       result["success"],
                "llm_model":                 CURRENT_MODEL,
                "llm_processed_at":          datetime.utcnow(),
            }
        }
    )

    return {
        "document_id":        document_id,
        "status":             "success",
        "model":              CURRENT_MODEL,
        "insurer":            result["insurer"],
        "insurer_display_name": result["insurer_display_name"],
        "config_version":     result["config_version"],
        # Step outputs for transparency
        "canonical_fields":   canonical,
        "normalized_fields":  normalized,
        "mapped_fields":      result["mapped_fields"],
        # Validation
        "extraction_complete": result["success"],
        "missing_required_fields": result["missing_fields"],
    }


@router.get("/result/{document_id}")
async def get_llm_result(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the last extraction result for a document."""
    db = get_database()

    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")

    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "tenant_id": current_user["tenant_id"]
    })

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document.get("canonical_fields"):
        raise HTTPException(
            status_code=404,
            detail="No extraction results. Run /llm/extract/{document_id} first."
        )

    return {
        "document_id":             document_id,
        "model":                   document.get("llm_model", CURRENT_MODEL),
        "processed_at":            document.get("llm_processed_at"),
        "insurer":                 document.get("insurer_key"),
        "insurer_display_name":    document.get("insurer_display_name"),
        "canonical_fields":        document.get("canonical_fields"),
        "normalized_fields":       document.get("normalized_fields"),
        "mapped_fields":           document.get("mapped_fields"),
        "extraction_complete":     document.get("extraction_complete"),
        "missing_required_fields": document.get("missing_required_fields", []),
    }


@router.get("/insurers")
async def list_insurers(current_user: dict = Depends(get_current_user)):
    """List all available insurer configs."""
    available = insurer_mapper.list_available()
    configs = {}
    for key in available:
        try:
            cfg = insurer_mapper.load_config(key)
            configs[key] = {
                "display_name":    cfg.get("display_name"),
                "version":         cfg.get("version"),
                "currency":        cfg.get("currency"),
                "required_fields": cfg.get("required_fields", []),
            }
        except Exception:
            pass

    return {
        "available_insurers": available,
        "configs": configs,
        "usage": "POST /llm/extract/{id}?insurer=masm"
    }