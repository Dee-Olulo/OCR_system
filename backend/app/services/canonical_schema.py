# /backend/app/services/canonical_schema.py

"""
The canonical (internal) schema is the single source of truth that the LLM
always outputs to — regardless of which insurer the document belongs to.

All normalization happens on this schema BEFORE mapping to insurer-specific
field names. This keeps the LLM prompt generic and insurer logic out of the
extraction step entirely.
"""

CANONICAL_SCHEMA = {
    "patient_name":  None,
    "invoice_number": None,
    "invoice_date":  None,
    "hospital_name": None,
    "doctor_name":   None,
    "icd_code":      None,
    "insurer":       None,
    "policy_number": None,
    "total_amount":  None,
    "currency":      None,
    "line_items":    []
}


def empty_canonical() -> dict:
    """Return a fresh copy of the canonical schema with all nulls."""
    import copy
    return copy.deepcopy(CANONICAL_SCHEMA)


def build_canonical_prompt_schema() -> dict:
    """
    Build the JSON template shown inside the LLM prompt.
    Line items include one example item to guide the model.
    """
    return {
        "patient_name":   None,
        "invoice_number": None,
        "invoice_date":   None,
        "hospital_name":  None,
        "doctor_name":    None,
        "icd_code":       None,
        "insurer":        None,
        "policy_number":  None,
        "total_amount":   None,
        "currency":       None,
        "line_items": [
            {
                "description": None,
                "tariff_code": None,
                "quantity":    None,
                "unit_price":  None,
                "amount":      None,
                "date":        None
            }
        ]
    }