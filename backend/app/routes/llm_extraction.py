# /backend/app/routes/llm_extraction.py

"""
Phase 3 + 4 extraction route.

Pipeline:
  OCR text
    → structural hints          (member no, invoice no)
    → TableExtractor            → line items, claimed_total
    → LLM (table stripped)      → header fields
    → 3-pass JSON repair
    → backfill hints + total + insurer-from-text
    → normalize
    → insurer mapping + validation
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


def _build_aliases_map() -> dict:
    """
    Build {insurer_key: [aliases]} from all loaded insurer configs.
    Passed to the extraction service for raw-text insurer fallback detection.
    """
    aliases_map = {}
    for key in insurer_mapper.list_available():
        try:
            cfg = insurer_mapper.load_config(key)
            aliases_map[key] = cfg.get("aliases", [])
        except Exception:
            pass
    return aliases_map


@router.post("/extract/{document_id}")
async def extract_with_llm(
    document_id: str,
    insurer: str = Query(
        None,
        description="Insurer key (e.g. masm, nico). Auto-detected if omitted."
    ),
    current_user: dict = Depends(get_current_user)
):
    """
    Full extraction pipeline (Phase 3 + 4).

    Steps:
    1. Structural pre-extraction  → member number, invoice number
    2. TableExtractor             → line items with arithmetic validation
    3. LLM (table rows stripped)  → header fields, lean token budget
    4. 3-pass JSON repair         → handles truncation, preamble, fences
    5. Backfill                   → hints, total_amount, insurer from text
    6. Normalize                  → dates, amounts, policy numbers
    7. Insurer mapping            → insurer-specific field names
    8. Validation                 → required fields check
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

    # ── Step 1–5: Extract → canonical ────────────────────────────────────────
    logger.info(f"Extraction pipeline | document={document_id}")

    # Build aliases map for raw-text insurer fallback
    aliases_map = _build_aliases_map()

    canonical = await llm_extraction_service.extract_to_canonical(
        ocr_text,
        insurer_aliases_map=aliases_map,
    )

    # extract_to_canonical never raises — check for hard failure
    if canonical.get("error") and not canonical.get("insurer") and not insurer:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {canonical.get('error')}"
        )

    # Pull out table validation metadata before further processing
    table_validation = canonical.pop("_table_validation", {})

    # ── Step 6: Detect insurer ────────────────────────────────────────────────
    insurer_key = insurer.lower() if insurer else None

    if not insurer_key:
        # Try canonical['insurer'] field first
        insurer_key = insurer_mapper.detect_insurer(canonical)

    if not insurer_key:
        available = insurer_mapper.list_available()
        raise HTTPException(
            status_code=422,
            detail=(
                f"Could not detect insurer from document or extracted fields. "
                f"Pass ?insurer=<key> explicitly. Available: {available}"
            )
        )

    available = insurer_mapper.list_available()
    if insurer_key not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown insurer '{insurer_key}'. Available: {available}"
        )

    # ── Step 7: Normalize ─────────────────────────────────────────────────────
    logger.info(f"Normalizing | insurer={insurer_key}")
    insurer_config = insurer_mapper.load_config(insurer_key)
    date_format = insurer_config.get("date_format", "%d/%m/%Y")
    normalized = normalize_canonical(canonical, date_format=date_format)

    # ── Step 8: Map + validate ────────────────────────────────────────────────
    logger.info(f"Mapping to {insurer_key} schema")
    result = insurer_mapper.process(normalized, insurer_key)

    # ── Persist ───────────────────────────────────────────────────────────────
    await db.documents.update_one(
        {"_id": ObjectId(document_id)},
        {
            "$set": {
                "canonical_fields":        canonical,
                "normalized_fields":       normalized,
                "mapped_fields":           result["mapped_fields"],
                "insurer_key":             insurer_key,
                "insurer_display_name":    result["insurer_display_name"],
                "missing_required_fields": result["missing_fields"],
                "extraction_complete":     result["success"],
                "table_validation":        table_validation,
                "llm_model":               CURRENT_MODEL,
                "llm_processed_at":        datetime.utcnow(),
            }
        }
    )

    return {
        "document_id":           document_id,
        "status":                "success",
        "model":                 CURRENT_MODEL,
        "insurer":               result["insurer"],
        "insurer_display_name":  result["insurer_display_name"],
        "config_version":        result["config_version"],
        "canonical_fields":      canonical,
        "normalized_fields":     normalized,
        "mapped_fields":         result["mapped_fields"],
        "extraction_complete":        result["success"],
        "missing_required_fields":    result["missing_fields"],
        "table_validation": {
            "claimed_total":    table_validation.get("claimed_total"),
            "computed_total":   table_validation.get("computed_total"),
            "total_match":      table_validation.get("total_match"),
            "discrepancies":    table_validation.get("discrepancies", []),
            "table_confidence": table_validation.get("table_confidence", 0.0),
            "llm_parse_ok":     table_validation.get("llm_parse_ok", False),
        },
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
        "table_validation":        document.get("table_validation", {}),
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