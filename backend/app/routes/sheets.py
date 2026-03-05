# /backend/app/routes/sheets.py

"""
Google Sheets export routes — Phase 6.

Endpoints:
  POST /export/sheets/{document_id}
    Called by n8n after a document is auto-approved (routing_decision = auto_approved).
    Exports the invoice to the master Google Sheet and logs the result in MongoDB.

  POST /export/sheets/batch
    Called by n8n on a schedule (e.g. end of day) or manually from the Angular frontend.
    Exports multiple invoices at once. Accepts optional filters.

  GET /export/sheets/status/{document_id}
    Returns the most recent export log for a document.
    Used by n8n to check if an invoice has already been exported.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.database import get_database
from app.services.sheets_service import sheets_service, SheetsExportError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Google Sheets Export"])


# ── Auth helper ────────────────────────────────────────────────────────────────

def _verify_secret(header_value: Optional[str]) -> None:
    if settings.N8N_WEBHOOK_SECRET and header_value != settings.N8N_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


# ── Request models ─────────────────────────────────────────────────────────────

class BatchExportRequest(BaseModel):
    document_ids:    Optional[list] = None   # None = use filters below
    insurer_key:     Optional[str]  = None
    routing:         Optional[str]  = "auto_approved"
    date_from:       Optional[str]  = None   # ISO 8601
    date_to:         Optional[str]  = None
    skip_duplicates: bool           = True   # skip already-exported invoices


# ── POST /export/sheets/{document_id} ─────────────────────────────────────────

@router.post("/sheets/{document_id}")
async def export_single_to_sheets(
    document_id:      str,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """
    Export one invoice to the master Google Sheet.

    Called automatically by n8n after routing_decision = "auto_approved".

    n8n HTTP Request node configuration:
      Method:  POST
      URL:     http://localhost:8000/api/v1/export/sheets/{{ $json.document_id }}
      Headers: X-Webhook-Secret: (your credential value)
    """
    _verify_secret(x_webhook_secret)

    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")

    db  = get_database()
    doc = await db.documents.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    # Only export completed documents
    if doc.get("status") != "completed":
        raise HTTPException(
            status_code=422,
            detail=f"Document status is '{doc.get('status')}' — only 'completed' documents can be exported"
        )

    errors = []
    success = False
    sheet_url = None

    try:
        result    = sheets_service.export_invoice(doc)
        sheet_url = result["sheet_url"]
        success   = True
        logger.info(f"Sheets export success: {document_id}")
    except SheetsExportError as e:
        errors.append(str(e))
        logger.error(f"Sheets export failed for {document_id}: {e}")

    # Log to MongoDB regardless of success/failure
    await db.sheet_exports.insert_one({
        "document_id":    document_id,
        "invoice_number": doc.get("invoice_number"),
        "spreadsheet_id": settings.MASTER_SPREADSHEET_ID,
        "sheet_url":      sheet_url,
        "exported_at":    datetime.now(timezone.utc),
        "success":        success,
        "errors":         errors,
    })

    if not success:
        raise HTTPException(status_code=500, detail={
            "message": "Export to Google Sheets failed",
            "errors":  errors,
        })

    return {
        "document_id":  document_id,
        "sheet_url":    sheet_url,
        "message":      "Invoice exported successfully",
    }


# ── POST /export/sheets/batch ──────────────────────────────────────────────────

@router.post("/sheets/batch")
async def export_batch_to_sheets(
    body:             BatchExportRequest,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """
    Export multiple invoices to the master Google Sheet in one call.

    Can be triggered by:
      - n8n Cron node (e.g. every day at 17:00)
      - Angular frontend export button
      - Manual curl call

    Accepts optional filters. By default exports all auto_approved
    documents that have not yet been exported (skip_duplicates=true).
    """
    _verify_secret(x_webhook_secret)

    db    = get_database()
    query: dict = {"status": "completed"}

    # Filter by explicit document IDs
    if body.document_ids:
        valid_ids = [ObjectId(i) for i in body.document_ids if ObjectId.is_valid(i)]
        query["_id"] = {"$in": valid_ids}

    # Filter by insurer
    if body.insurer_key:
        query["insurer_key"] = body.insurer_key.lower()

    # Filter by routing decision (default: auto_approved only)
    if body.routing:
        query["routing_decision"] = body.routing

    # Filter by date range
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

    # Skip already-exported documents
    if body.skip_duplicates:
        already_exported = await db.sheet_exports.distinct(
            "document_id", {"success": True}
        )
        if already_exported:
            query["_id"] = {
                "$nin": [ObjectId(i) for i in already_exported if ObjectId.is_valid(str(i))]
            }

    documents = await db.documents.find(query).to_list(length=500)

    if not documents:
        return {
            "exported":  0,
            "failed":    0,
            "skipped":   0,
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{settings.MASTER_SPREADSHEET_ID}",
            "message":   "No documents matched the export filter",
        }

    exported = 0
    failed   = 0
    errors   = []

    for doc in documents:
        doc_id = str(doc["_id"])
        try:
            result = sheets_service.export_invoice(doc)
            await db.sheet_exports.insert_one({
                "document_id":    doc_id,
                "invoice_number": doc.get("invoice_number"),
                "spreadsheet_id": settings.MASTER_SPREADSHEET_ID,
                "sheet_url":      result["sheet_url"],
                "exported_at":    datetime.now(timezone.utc),
                "success":        True,
                "errors":         [],
            })
            exported += 1
        except SheetsExportError as e:
            await db.sheet_exports.insert_one({
                "document_id":    doc_id,
                "invoice_number": doc.get("invoice_number"),
                "spreadsheet_id": settings.MASTER_SPREADSHEET_ID,
                "sheet_url":      None,
                "exported_at":    datetime.now(timezone.utc),
                "success":        False,
                "errors":         [str(e)],
            })
            errors.append({"document_id": doc_id, "error": str(e)})
            failed += 1
            logger.error(f"Batch export failed for {doc_id}: {e}")

    sheet_url = f"https://docs.google.com/spreadsheets/d/{settings.MASTER_SPREADSHEET_ID}"

    return {
        "exported":  exported,
        "failed":    failed,
        "skipped":   len(documents) - exported - failed,
        "sheet_url": sheet_url,
        "errors":    errors,
        "message":   f"Batch export complete — {exported} exported, {failed} failed",
    }


# ── GET /export/sheets/status/{document_id} ───────────────────────────────────

@router.get("/sheets/status/{document_id}")
async def get_export_status(
    document_id:      str,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """
    Return the most recent export log for a document.
    Used by n8n to check if an invoice has already been exported.
    """
    _verify_secret(x_webhook_secret)

    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")

    db  = get_database()
    log = await db.sheet_exports.find_one(
        {"document_id": document_id},
        sort=[("exported_at", -1)],
    )

    if not log:
        return {"document_id": document_id, "exported": False}

    log["_id"] = str(log["_id"])
    log["exported"] = True
    return log