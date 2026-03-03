# /backend/app/routes/webhook.py

"""
n8n webhook integration routes — Phase 5.

Endpoints called BY n8n (not the Angular frontend):

  POST /webhook/process
    Called by the n8n HTTP Request node after a file upload event.
    Runs the full pipeline: OCR → LLM → normalize → map → confidence → route.
    Returns routing_decision so the n8n Switch node can branch.

  GET  /webhook/document/{id}
    n8n polls this to retrieve pipeline results and full document state.

  POST /webhook/export/excel
    n8n triggers batch Excel export with optional filters.
    Returns a download URL usable in an n8n Email node attachment.

  GET  /webhook/export/download/{filename}
    Serves a generated Excel file (called by n8n or directly by a browser).

  GET  /webhook/health
    n8n polls this on a schedule.  Returns status "healthy" or "degraded".
    n8n IF node branches to Slack alert when status != "healthy".

Security:
  All endpoints verify the X-Webhook-Secret header against
  settings.N8N_WEBHOOK_SECRET.  The secret is set in .env and in
  ecosystem.config.js — both must match the value stored in the
  n8n Header Auth credential.
"""

import logging
import os
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.database import get_database
from app.services.confidence_service import confidence_service
from app.services.excel_service import excel_service
from app.services.llm_extraction_service import llm_extraction_service
from app.services.mapping_engine import insurer_mapper
from app.services.normalization import normalize_canonical
from app.services.ocr_service import ocr_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["n8n Webhooks"])

# Export directory — created on first export if missing
_EXPORT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "exports"
)


# ── Auth helper ────────────────────────────────────────────────────────────────

def _verify_secret(header_value: Optional[str]) -> None:
    """
    Reject requests where the X-Webhook-Secret header does not match
    settings.N8N_WEBHOOK_SECRET.

    If N8N_WEBHOOK_SECRET is empty (not configured), all requests are
    allowed — acceptable during local development, never in production.
    """
    if settings.N8N_WEBHOOK_SECRET and header_value != settings.N8N_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


# ── Request / response models ──────────────────────────────────────────────────

class WebhookProcessRequest(BaseModel):
    document_id: str
    ocr_engine:  str = "tesseract"   # tesseract | easyocr | both


class WebhookProcessResponse(BaseModel):
    document_id:         str
    workflow_run_id:     Optional[str]
    status:              str            # processing | completed | failed
    routing_decision:    Optional[str]  # auto_approved | pending_review | rejected
    confidence_score:    Optional[float]
    insurer_key:         Optional[str]
    insurer_display:     Optional[str]
    extraction_complete: bool
    missing_fields:      list
    invoice_number:      Optional[str]
    message:             str


class WebhookExportRequest(BaseModel):
    document_ids: Optional[list] = None
    insurer_key:  Optional[str]  = None
    routing:      Optional[str]  = None   # auto_approved | pending_review | rejected
    date_from:    Optional[str]  = None   # ISO 8601 e.g. "2026-01-01"
    date_to:      Optional[str]  = None
    filename:     Optional[str]  = None


# ── POST /webhook/process ──────────────────────────────────────────────────────

@router.post("/process", response_model=WebhookProcessResponse)
async def webhook_process(
    body:              WebhookProcessRequest,
    x_webhook_secret:  Optional[str] = Header(default=None),
    x_workflow_run_id: Optional[str] = Header(default=None),
):
    """
    Main pipeline trigger called by the n8n HTTP Request node.

    n8n node configuration:
      Method:  POST
      URL:     http://localhost:8000/api/v1/webhook/process
      Headers:
        X-Webhook-Secret:  (value from Header Auth credential)
        X-Workflow-Run-Id: {{ $execution.id }}
      Body (JSON):
        {
          "document_id": "{{ $json.body.document_id }}",
          "ocr_engine": "tesseract"
        }

    Returns routing_decision for the n8n Switch node:
      "auto_approved"  → pipeline complete, no action needed
      "pending_review" → send reviewer notification
      "rejected"       → notify uploader to re-scan
    """
    _verify_secret(x_webhook_secret)

    document_id  = body.document_id
    workflow_run = x_workflow_run_id

    db = get_database()

    # ── 1. Validate document exists ───────────────────────────────────
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")

    doc = await db.documents.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    tenant_id = doc["tenant_id"]
    file_path = doc.get("original_path")

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=422,
            detail=f"Document file not found on disk: {file_path}"
        )

    # ── 2. Mark as processing ─────────────────────────────────────────
    await db.documents.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"status": "processing", "workflow_run_id": workflow_run}},
    )

    try:
        # ── 3. OCR ───────────────────────────────────────────────────
        logger.info(f"[{document_id}] OCR start | engine={body.ocr_engine}")
        ocr_result = ocr_service.extract_text_multipage(
            file_path, engine=body.ocr_engine
        )

        if not ocr_result["success"] or not ocr_result["text"].strip():
            await _mark_failed(db, document_id, "OCR produced no text", workflow_run)
            return _failed_response(document_id, workflow_run, "OCR produced no text")

        raw_text       = ocr_result["text"]
        ocr_confidence = ocr_result["confidence"]   # 0–100 float

        # ── 4. Build insurer aliases map ──────────────────────────────
        aliases_map: dict = {}
        for key in insurer_mapper.list_available():
            try:
                cfg = insurer_mapper.load_config(key)
                aliases_map[key] = cfg.get("aliases", [])
            except Exception:
                pass

        # ── 5. LLM extraction ─────────────────────────────────────────
        logger.info(f"[{document_id}] LLM extraction start")
        canonical = await llm_extraction_service.extract_to_canonical(
            raw_text=raw_text,
            insurer_aliases_map=aliases_map,
        )

        # ── 6. Detect insurer + normalize ─────────────────────────────
        insurer_key = insurer_mapper.detect_insurer(canonical)
        date_format = "%d/%m/%Y"
        if insurer_key:
            try:
                cfg         = insurer_mapper.load_config(insurer_key)
                date_format = cfg.get("date_format", "%d/%m/%Y")
            except Exception:
                pass

        normalized = normalize_canonical(canonical, date_format=date_format)

        # ── 7. Map to insurer schema ──────────────────────────────────
        if insurer_key:
            mapping_result = insurer_mapper.process(normalized, insurer_key)
        else:
            mapping_result = {
                "insurer":              None,
                "insurer_display_name": None,
                "mapped_fields":        normalized,
                "success":              False,
                "missing_fields":       [],
                "config_version":       None,
            }

        mapped_fields       = mapping_result.get("mapped_fields", {})
        insurer_display     = mapping_result.get("insurer_display_name")
        extraction_complete = mapping_result.get("success", False)
        missing_fields      = mapping_result.get("missing_fields", [])

        # ── 8. Confidence scoring ──────────────────────────────────────
        table_validation = canonical.get("_table_validation", {})

        score_result = await confidence_service.score(
            document_id      = document_id,
            tenant_id        = tenant_id,
            ocr_confidence   = ocr_confidence,
            canonical        = canonical,
            table_validation = table_validation,
            mapped_fields    = mapped_fields,
            insurer_key      = insurer_key,
            db               = db,
        )

        routing_decision = score_result["routing_decision"]
        review_status    = score_result["review_status"]
        invoice_number   = (
            normalized.get("invoice_number") or
            canonical.get("invoice_number")
        )

        # ── 9. Persist all results to MongoDB ─────────────────────────
        await db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {
                "status":               "completed",
                "processed_at":         datetime.utcnow(),
                "extracted_text":       raw_text,
                "ocr_engine":           body.ocr_engine,
                "ocr_confidence_raw":   ocr_confidence,
                "canonical_fields":     canonical,
                "normalized_fields":    normalized,
                "mapped_fields":        mapped_fields,
                "insurer_key":          insurer_key,
                "insurer_display_name": insurer_display,
                "invoice_number":       invoice_number,
                "extraction_complete":  extraction_complete,
                "missing_fields":       missing_fields,
                "confidence_score":     score_result["confidence_score"],
                "confidence_breakdown": score_result["confidence_breakdown"],
                "routing_decision":     routing_decision,
                "review_status":        review_status,
                "workflow_run_id":      workflow_run,
            }},
        )

        # ── 10. Log to workflow_logs collection ────────────────────────
        await db.workflow_logs.insert_one({
            "document_id":      document_id,
            "tenant_id":        tenant_id,
            "workflow_run_id":  workflow_run,
            "event":            "pipeline_complete",
            "routing_decision": routing_decision,
            "confidence_score": score_result["confidence_score"],
            "ocr_engine":       body.ocr_engine,
            "timestamp":        datetime.utcnow(),
            "status":           "success",
        })

        logger.info(
            f"[{document_id}] Pipeline complete | "
            f"routing={routing_decision} | "
            f"confidence={score_result['confidence_score']:.3f}"
        )

        return WebhookProcessResponse(
            document_id=document_id,
            workflow_run_id=workflow_run,
            status="completed",
            routing_decision=routing_decision,
            confidence_score=score_result["confidence_score"],
            insurer_key=insurer_key,
            insurer_display=insurer_display,
            extraction_complete=extraction_complete,
            missing_fields=missing_fields,
            invoice_number=invoice_number,
            message=f"Pipeline complete → {routing_decision}",
        )

    except Exception as exc:
        logger.exception(f"[{document_id}] Pipeline error: {exc}")
        await _mark_failed(db, document_id, str(exc), workflow_run)
        await db.workflow_logs.insert_one({
            "document_id":     document_id,
            "tenant_id":       tenant_id,
            "workflow_run_id": workflow_run,
            "event":           "pipeline_error",
            "error":           str(exc),
            "timestamp":       datetime.utcnow(),
            "status":          "error",
        })
        return _failed_response(document_id, workflow_run, str(exc))


# ── GET /webhook/document/{id} ─────────────────────────────────────────────────

@router.get("/document/{document_id}")
async def webhook_get_document(
    document_id:      str,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """
    Return full document state including confidence, routing, extracted fields.

    n8n node configuration:
      Method: GET
      URL:    http://localhost:8000/api/v1/webhook/document/{{ $json.document_id }}
      Headers: X-Webhook-Secret: (value from Header Auth credential)
    """
    _verify_secret(x_webhook_secret)

    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")

    db  = get_database()
    doc = await db.documents.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    canonical = doc.get("canonical_fields") or {}
    table_val = canonical.get("_table_validation") or {}

    return {
        "document_id":          str(doc["_id"]),
        "filename":             doc.get("filename"),
        "status":               doc.get("status"),
        "routing_decision":     doc.get("routing_decision"),
        "review_status":        doc.get("review_status"),
        "confidence_score":     doc.get("confidence_score"),
        "confidence_breakdown": doc.get("confidence_breakdown"),
        "insurer_key":          doc.get("insurer_key"),
        "insurer_display_name": doc.get("insurer_display_name"),
        "invoice_number":       doc.get("invoice_number"),
        "extraction_complete":  doc.get("extraction_complete"),
        "missing_fields":       doc.get("missing_fields", []),
        "workflow_run_id":      doc.get("workflow_run_id"),
        "processed_at":         doc.get("processed_at"),
        "table_validation":     table_val,
        "canonical_fields": {
            k: v for k, v in canonical.items() if not k.startswith("_")
        },
        "mapped_fields": doc.get("mapped_fields"),
    }


# ── POST /webhook/export/excel ─────────────────────────────────────────────────

@router.post("/export/excel")
async def webhook_export_excel(
    body:             WebhookExportRequest,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """
    Batch Excel export triggered by n8n (e.g. on a Cron schedule).

    n8n node configuration:
      Method: POST
      URL:    http://localhost:8000/api/v1/webhook/export/excel
      Headers: X-Webhook-Secret: (value from Header Auth credential)
      Body (JSON):
        {
          "routing": "auto_approved",
          "insurer_key": "masm"
        }

    The returned download_url can be passed to an n8n Email node as
    a link, or fetched by a subsequent HTTP Request node to attach
    the file to an email.
    """
    _verify_secret(x_webhook_secret)

    db    = get_database()
    query: dict = {"status": "completed"}

    if body.document_ids:
        valid_ids = [
            ObjectId(i) for i in body.document_ids if ObjectId.is_valid(i)
        ]
        query["_id"] = {"$in": valid_ids}

    if body.insurer_key:
        query["insurer_key"] = body.insurer_key.lower()

    if body.routing:
        query["routing_decision"] = body.routing

    if body.date_from or body.date_to:
        date_filter: dict = {}
        if body.date_from:
            try:
                date_filter["$gte"] = datetime.fromisoformat(body.date_from)
            except ValueError:
                pass
        if body.date_to:
            try:
                date_filter["$lte"] = datetime.fromisoformat(body.date_to)
            except ValueError:
                pass
        if date_filter:
            query["uploaded_at"] = date_filter

    documents = await db.documents.find(query).to_list(length=1000)

    if not documents:
        raise HTTPException(
            status_code=404,
            detail="No completed documents matched the export filter",
        )

    file_path = await excel_service.export_invoices(
        documents=documents,
        filename=body.filename,
    )
    filename = os.path.basename(file_path)

    await db.workflow_logs.insert_one({
        "event":       "excel_export",
        "filename":    filename,
        "doc_count":   len(documents),
        "filter":      {
            "insurer_key": body.insurer_key,
            "routing":     body.routing,
            "date_from":   body.date_from,
            "date_to":     body.date_to,
        },
        "timestamp":   datetime.utcnow(),
        "status":      "success",
    })

    return {
        "filename":       filename,
        "document_count": len(documents),
        "download_url":   f"http://localhost:8000/api/v1/webhook/export/download/{filename}",
        "message":        f"Export complete — {len(documents)} invoices",
    }


# ── GET /webhook/export/download/{filename} ────────────────────────────────────

@router.get("/export/download/{filename}")
async def webhook_download_export(
    filename:         str,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """
    Serve a generated Excel file.
    The URL is returned by /webhook/export/excel and can be used
    directly in an n8n Email node or browser redirect.
    """
    _verify_secret(x_webhook_secret)

    file_path = os.path.join(_EXPORT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
    )


# ── GET /webhook/health ────────────────────────────────────────────────────────

@router.get("/health")
async def webhook_health(
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """
    Detailed health check polled by an n8n Cron workflow.

    n8n node configuration:
      Method: GET
      URL:    http://localhost:8000/api/v1/webhook/health
      Headers: X-Webhook-Secret: (value from Header Auth credential)

    n8n IF node after this:
      Branch TRUE  (healthy):  No Operation
      Branch FALSE (degraded): Slack / Email alert node
      Condition:  {{ $json.status === 'healthy' }}
    """
    _verify_secret(x_webhook_secret)

    checks: dict = {}
    overall       = "healthy"

    # MongoDB
    try:
        db = get_database()
        await db.command("ping")
        checks["mongodb"] = {"status": "ok"}
    except Exception as e:
        checks["mongodb"] = {"status": "error", "detail": str(e)}
        overall = "degraded"

    # LLM (Ollama)
    try:
        llm_ok = llm_extraction_service.is_available()
        checks["llm"] = {"status": "ok" if llm_ok else "unavailable"}
        if not llm_ok:
            overall = "degraded"
    except Exception as e:
        checks["llm"] = {"status": "error", "detail": str(e)}
        overall = "degraded"

    # Upload directory
    from app.config import settings as cfg
    upload_dir = cfg.UPLOAD_DIR
    checks["uploads_dir"] = {
        "status": "ok" if os.path.exists(upload_dir) else "missing"
    }

    # Export directory
    try:
        os.makedirs(_EXPORT_DIR, exist_ok=True)
        checks["exports_dir"] = {"status": "ok"}
    except Exception as e:
        checks["exports_dir"] = {"status": "error", "detail": str(e)}
        overall = "degraded"

    return {
        "status":    overall,
        "timestamp": datetime.utcnow().isoformat(),
        "checks":    checks,
    }


# ── Private helpers ────────────────────────────────────────────────────────────

async def _mark_failed(
    db,
    document_id:     str,
    reason:          str,
    workflow_run_id: Optional[str] = None,
) -> None:
    update: dict = {
        "status":           "failed",
        "processed_at":     datetime.utcnow(),
        "routing_decision": "rejected",
        "review_status":    "not_required",
    }
    if workflow_run_id:
        update["workflow_run_id"] = workflow_run_id
    await db.documents.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": update},
    )
    logger.warning(f"[{document_id}] Marked as failed: {reason}")


def _failed_response(
    document_id:     str,
    workflow_run_id: Optional[str],
    reason:          str,
) -> WebhookProcessResponse:
    return WebhookProcessResponse(
        document_id=document_id,
        workflow_run_id=workflow_run_id,
        status="failed",
        routing_decision="rejected",
        confidence_score=0.0,
        insurer_key=None,
        insurer_display=None,
        extraction_complete=False,
        missing_fields=[],
        invoice_number=None,
        message=f"Pipeline failed: {reason}",
    )