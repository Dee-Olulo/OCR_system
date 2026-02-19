# /backend/app/services/normalization.py

"""
Normalization utilities applied to canonical schema fields
BEFORE they are passed to the mapping engine.

These are pure functions — no side effects, no I/O.
"""

import re
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# All input date formats the OCR/LLM might produce
INPUT_DATE_FORMATS = [
    "%d/%m/%Y",   # 26/01/2026
    "%d-%m-%Y",   # 26-01-2026
    "%Y-%m-%d",   # 2026-01-26
    "%d/%m/%y",   # 26/01/26
    "%d %b %Y",   # 26 Jan 2026
    "%d %B %Y",   # 26 January 2026
    "%Y/%m/%d",   # 2026/01/26
    "%m/%d/%Y",   # 01/26/2026
]


def normalize_date(date_str: Any, target_format: str = "%d/%m/%Y") -> Optional[str]:
    """
    Parse a date string from any common format and reformat to target_format.
    Returns the original string unchanged if parsing fails (never silently drops data).
    """
    if date_str is None:
        return None

    value = str(date_str).strip()
    if not value:
        return None

    for fmt in INPUT_DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime(target_format)
        except ValueError:
            continue

    # Could not parse — return as-is and let validation flag it
    logger.warning(f"Could not normalize date: '{value}'")
    return value


def normalize_amount(value: Any) -> Optional[float]:
    """
    Strip currency symbols, commas, and whitespace then return a float.
    Returns None if value is empty or unparseable.
    """
    if value is None:
        return None

    cleaned = re.sub(r"[^\d.]", "", str(value))

    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        logger.warning(f"Could not normalize amount: '{value}'")
        return None


def normalize_policy_number(value: Any) -> Optional[str]:
    """
    Uppercase, strip whitespace and internal spaces from policy/member numbers.
    """
    if value is None:
        return None

    normalized = re.sub(r"\s+", "", str(value).strip().upper())
    return normalized if normalized else None


def normalize_string(value: Any) -> Optional[str]:
    """Strip and title-case a plain string field."""
    if value is None:
        return None

    normalized = str(value).strip()
    return normalized if normalized else None


def normalize_canonical(data: dict, date_format: str = "%d/%m/%Y") -> dict:
    """
    Apply all normalizations to a canonical schema dict in one pass.

    Called AFTER LLM extraction and BEFORE mapping engine.

    Args:
        data:        Canonical schema dict from LLM
        date_format: Target date format from the insurer config

    Returns:
        New dict with all fields normalized.
    """
    normalized = {}

    # String fields
    for field in ("patient_name", "hospital_name", "doctor_name",
                  "icd_code", "insurer", "currency"):
        normalized[field] = normalize_string(data.get(field))

    # Date fields
    normalized["invoice_date"] = normalize_date(
        data.get("invoice_date"), target_format=date_format
    )

    # Amount fields
    normalized["total_amount"] = normalize_amount(data.get("total_amount"))

    # Policy / member number
    normalized["policy_number"] = normalize_policy_number(data.get("policy_number"))

    # Invoice number — keep as string, just strip whitespace
    normalized["invoice_number"] = normalize_string(data.get("invoice_number"))

    # Line items — normalize each item
    raw_items = data.get("line_items", [])
    if not isinstance(raw_items, list):
        raw_items = []

    normalized["line_items"] = [
        _normalize_line_item(item, date_format) for item in raw_items
        if isinstance(item, dict)
    ]

    return normalized


def _normalize_line_item(item: dict, date_format: str) -> dict:
    return {
        "description": normalize_string(item.get("description")),
        "tariff_code":  normalize_string(item.get("tariff_code")),
        "quantity":     normalize_amount(item.get("quantity")),
        "unit_price":   normalize_amount(item.get("unit_price")),
        "amount":       normalize_amount(item.get("amount")),
        "date":         normalize_date(item.get("date"), target_format=date_format),
    }