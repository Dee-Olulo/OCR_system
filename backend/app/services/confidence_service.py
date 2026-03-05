# /backend/app/services/confidence_service.py

"""
Composite confidence scoring for extracted invoice documents.

Score = weighted sum of 5 signals:

  Signal 1 — OCR engine confidence (30%)
    Source: ocr_service.extract_text() → result["confidence"]
    Already computed as a 0–100 float by RegionDetector.document_confidence().
    Normalised to 0.0–1.0 here.

  Signal 2 — LLM field completeness (25%)
    Ratio of required canonical fields that are non-null after extraction.
    Required fields: patient_name, invoice_number, invoice_date, insurer,
                     policy_number, total_amount.

  Signal 3 — Arithmetic validation (20%)
    Boolean from table_extractor: computed sum of line item amounts == claimed_total.
    Already stored in canonical["_table_validation"]["total_match"].

  Signal 4 — Schema compliance (15%)
    Mapping engine validation: all insurer-required fields present and non-null.
    If no insurer was detected, schema score defaults to 0.5 (neutral).

  Signal 5 — Duplicate detection (10%)
    Invoice number not already present in MongoDB for the same tenant.

Routing thresholds:
  0.90 – 1.00  → auto_approved
  0.70 – 0.89  → pending_review
  0.00 – 0.69  → rejected

Usage:
    from app.services.confidence_service import confidence_service

    score_result = await confidence_service.score(
        document_id      = str(doc["_id"]),
        tenant_id        = doc["tenant_id"],
        ocr_confidence   = doc["confidence_score"],      # 0–100 float
        canonical        = doc["canonical_fields"],
        table_validation = doc["canonical_fields"].get("_table_validation", {}),
        mapped_fields    = doc.get("mapped_fields"),
        insurer_key      = doc.get("insurer_key"),
        db               = db,
    )
"""

import logging
from typing import Optional
from app.database import get_database

logger = logging.getLogger(__name__)

# ── Weights ───────────────────────────────────────────────────────────────────
WEIGHT_OCR        = 0.30
WEIGHT_FIELDS     = 0.25
WEIGHT_ARITHMETIC = 0.20
WEIGHT_SCHEMA     = 0.15
WEIGHT_DUPLICATE  = 0.10

# Required canonical fields for field-completeness scoring
REQUIRED_CANONICAL_FIELDS = [
    "patient_name",
    "invoice_number",
    "invoice_date",
    "insurer",
    "policy_number",
    "total_amount",
]

# Routing thresholds
THRESHOLD_AUTO_APPROVE   = 0.80
THRESHOLD_PENDING_REVIEW = 0.65


class ConfidenceService:

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def score(
        self,
        document_id:      str,
        tenant_id:        str,
        ocr_confidence:   float,          # 0–100 from OCR engine
        canonical:        dict,           # full canonical dict incl. _table_validation
        table_validation: dict,           # canonical["_table_validation"]
        mapped_fields:    Optional[dict], # insurer-mapped output or None
        insurer_key:      Optional[str],  # e.g. 'masm', 'nico' or None
        db=None,                          # AsyncIOMotorDatabase (injected)
    ) -> dict:
        """
        Compute composite confidence score.

        Returns a dict with:
          confidence_score       : float 0.0–1.0
          confidence_breakdown   : per-signal scores
          routing_decision       : 'auto_approved' | 'pending_review' | 'rejected'
          review_status          : 'not_required' | 'awaiting' | None
        """
        if db is None:
            db = get_database()

        # ── Signal 1: OCR confidence (0–100 → 0.0–1.0) ───────────────
        ocr_score = min(max(float(ocr_confidence or 0) / 100.0, 0.0), 1.0)

        # ── Signal 2: LLM field completeness ─────────────────────────
        field_score = self._score_field_completeness(canonical)

        # ── Signal 3: Arithmetic validation ──────────────────────────
        total_match   = bool(table_validation.get("total_match", False))
        arithmetic_score = 1.0 if total_match else 0.0

        # ── Signal 4: Schema compliance ───────────────────────────────
        schema_score = self._score_schema_compliance(mapped_fields, insurer_key)

        # ── Signal 5: Duplicate detection ─────────────────────────────
        invoice_number  = canonical.get("invoice_number")
        is_duplicate    = await self._is_duplicate(invoice_number, tenant_id, document_id, db)
        duplicate_score = 0.0 if is_duplicate else 1.0

        # ── Composite score ───────────────────────────────────────────
        composite = round(
            ocr_score        * WEIGHT_OCR        +
            field_score      * WEIGHT_FIELDS     +
            arithmetic_score * WEIGHT_ARITHMETIC +
            schema_score     * WEIGHT_SCHEMA     +
            duplicate_score  * WEIGHT_DUPLICATE,
            4,
        )

        routing, review_status = self._route(composite)

        logger.info(
            f"[{document_id}] confidence={composite:.3f} → {routing} | "
            f"ocr={ocr_score:.2f} fields={field_score:.2f} "
            f"arith={arithmetic_score:.2f} schema={schema_score:.2f} "
            f"dup={duplicate_score:.2f}"
        )

        return {
            "confidence_score": composite,
            "confidence_breakdown": {
                "ocr_confidence":    round(ocr_score, 4),
                "field_completeness": round(field_score, 4),
                "arithmetic_match":  total_match,
                "schema_valid":      schema_score == 1.0,
                "is_duplicate":      is_duplicate,
            },
            "routing_decision": routing,
            "review_status":    review_status,
        }

    # ------------------------------------------------------------------
    # Signal helpers
    # ------------------------------------------------------------------

    def _score_field_completeness(self, canonical: dict) -> float:
        """Ratio of required canonical fields that are non-null and non-empty."""
        if not canonical:
            return 0.0
        populated = sum(
            1 for f in REQUIRED_CANONICAL_FIELDS
            if canonical.get(f) not in (None, "", [])
        )
        return round(populated / len(REQUIRED_CANONICAL_FIELDS), 4)

    def _score_schema_compliance(
        self,
        mapped_fields: Optional[dict],
        insurer_key:   Optional[str],
    ) -> float:
        """
        1.0  if mapped_fields contains all insurer-required non-null fields.
        0.5  if no insurer was detected (neutral — we can't validate).
        0.0  if insurer detected but required fields are missing.
        """
        if not insurer_key:
            return 0.5   # Neutral — no insurer to validate against

        if not mapped_fields:
            return 0.0

        try:
            from app.services.mapping_engine import insurer_mapper
            config   = insurer_mapper.load_config(insurer_key)
            required = config.get("required_fields", [])
            if not required:
                return 1.0
            missing  = [f for f in required if not mapped_fields.get(f)]
            return round(1.0 - len(missing) / len(required), 4)
        except Exception as e:
            logger.warning(f"Schema compliance check failed: {e}")
            return 0.5

    async def _is_duplicate(
        self,
        invoice_number: Optional[str],
        tenant_id:      str,
        document_id:    str,
        db,
    ) -> bool:
        """
        True if another document with the same invoice_number already
        exists in MongoDB for this tenant (excluding current document).
        """
        if not invoice_number:
            return False
        try:
            from bson import ObjectId
            existing = await db.documents.find_one({
                "invoice_number": invoice_number,
                "tenant_id":      tenant_id,
                "_id":            {"$ne": ObjectId(document_id)},
            })
            return existing is not None
        except Exception as e:
            logger.warning(f"Duplicate check failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _route(self, score: float) -> tuple[str, str]:
        """
        Returns (routing_decision, review_status).
        """
        if score >= THRESHOLD_AUTO_APPROVE:
            return "auto_approved", "not_required"
        elif score >= THRESHOLD_PENDING_REVIEW:
            return "pending_review", "awaiting"
        else:
            return "rejected", "not_required"


# Global singleton
confidence_service = ConfidenceService()