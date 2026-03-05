# /backend/app/services/sheets_service.py

"""
Google Sheets export service — Phase 6.

Responsibilities:
  - Authenticate with Google using a Service Account JSON key file
  - Ensure the master spreadsheet has the required tabs with correct headers
  - Append one invoice summary row to the "Invoice Summary" tab
  - Append one row per line item to the "Line Items" tab
  - Return the sheet URL on success

Design decisions:
  - Idempotent tab setup: headers are only written once (when the tab is empty)
  - Uses gspread (high-level wrapper around Google Sheets API v4)
  - All Google API calls are wrapped in try/except — errors propagate as
    SheetsExportError so the route can return a clean 500 response
  - Service Account credentials are loaded once at import time from the
    path specified in settings.GOOGLE_SERVICE_ACCOUNT_KEY_PATH
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from app.config import settings

logger = logging.getLogger(__name__)

# Google API scopes required for reading and writing Sheets + Drive metadata
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

# Tab names inside the master spreadsheet
TAB_SUMMARY    = "Invoice Summary"
TAB_LINE_ITEMS = "Line Items"

# Column headers for each tab
SUMMARY_HEADERS = [
    "Export Timestamp (UTC)",
    "Invoice No.",
    "Patient Name",
    "Date of Service",
    "Insurer",
    "Policy No.",
    "Hospital",
    "Doctor",
    "ICD Code",
    "Currency",
    "Total Amount",
    "Confidence Score",
    "Routing Decision",
    "Missing Fields",
    "MongoDB ID",
]

LINE_ITEM_HEADERS = [
    "Invoice No.",
    "Line #",
    "Tariff Code",
    "Description",
    "Date",
    "Qty",
    "Unit Price",
    "Amount",
]


class SheetsExportError(Exception):
    """Raised when a Google Sheets API operation fails."""
    pass


class SheetsService:

    def __init__(self):
        self._client: Optional[gspread.Client] = None

    # ── Authentication ─────────────────────────────────────────────────────

    def _get_client(self) -> gspread.Client:
        """
        Return an authenticated gspread client.
        Re-authenticates if the token has expired (gspread handles refresh).
        """
        if self._client is None:
            try:
                creds = Credentials.from_service_account_file(
                    settings.GOOGLE_SERVICE_ACCOUNT_KEY_PATH,
                    scopes=_SCOPES,
                )
                self._client = gspread.authorize(creds)
                logger.info("Google Sheets: authenticated via service account")
            except FileNotFoundError:
                raise SheetsExportError(
                    f"Service account key file not found at: "
                    f"{settings.GOOGLE_SERVICE_ACCOUNT_KEY_PATH}. "
                    f"Follow Phase 6 SETUP.md Steps 1–4 to create and download it."
                )
            except Exception as e:
                raise SheetsExportError(f"Google Sheets authentication failed: {e}")
        return self._client

    # ── Tab setup ──────────────────────────────────────────────────────────

    def _get_or_create_tab(
        self,
        spreadsheet: gspread.Spreadsheet,
        tab_name: str,
        headers: list[str],
    ) -> gspread.Worksheet:
        """
        Return the worksheet with tab_name, creating it if it does not exist.
        If the tab is empty (no rows), write the header row.
        If the tab already has rows, assume headers are already present.
        """
        try:
            worksheet = spreadsheet.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=tab_name, rows=1000, cols=len(headers)
            )
            logger.info(f"Google Sheets: created tab '{tab_name}'")

        # Write headers only if the sheet is empty
        if worksheet.row_count == 0 or not worksheet.row_values(1):
            worksheet.append_row(headers, value_input_option="RAW")
            logger.info(f"Google Sheets: wrote headers to tab '{tab_name}'")

        return worksheet

    # ── Public export method ───────────────────────────────────────────────

    def export_invoice(self, document: dict) -> dict:
        """
        Append one invoice to the master Google Sheet.

        Args:
            document: Raw MongoDB document dict (full document, not a subset).

        Returns:
            dict with keys: spreadsheet_id, sheet_url, summary_row, line_item_count

        Raises:
            SheetsExportError on any Google API failure.
        """
        client      = self._get_client()
        spreadsheet_id = settings.MASTER_SPREADSHEET_ID

        try:
            spreadsheet = client.open_by_key(spreadsheet_id)
        except gspread.SpreadsheetNotFound:
            raise SheetsExportError(
                f"Spreadsheet not found: {spreadsheet_id}. "
                f"Check MASTER_SPREADSHEET_ID in your .env file."
            )
        except gspread.exceptions.APIError as e:
            raise SheetsExportError(
                f"Cannot open spreadsheet — likely a permissions error. "
                f"Share the sheet with your service account email (Editor access). "
                f"API error: {e}"
            )

        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

        # ── Extract fields ───────────────────────────────────────────────
        canonical  = document.get("canonical_fields")  or {}
        normalized = document.get("normalized_fields") or {}
        mapped     = document.get("mapped_fields")     or {}

        # Prefer mapped → normalized → canonical for each field
        def get_field(field: str):
            return (
                mapped.get(field) or
                normalized.get(field) or
                canonical.get(field)
            )

        invoice_number    = document.get("invoice_number") or get_field("invoice_number") or "—"
        patient_name      = get_field("patient_name")      or get_field("insured_name")   or get_field("beneficiary_name") or "—"
        invoice_date      = get_field("invoice_date")      or get_field("treatment_date") or get_field("date_of_service")  or "—"
        insurer           = get_field("insurer")           or document.get("insurer_display_name") or "—"
        policy_number     = get_field("policy_number")     or get_field("policy_no")      or get_field("member_number")    or "—"
        hospital_name     = get_field("hospital_name")     or get_field("facility_name")  or get_field("provider_name")    or "—"
        doctor_name       = get_field("doctor_name")       or get_field("attending_doctor") or "—"
        icd_code          = get_field("icd_code")          or get_field("diagnosis_code") or "—"
        currency          = get_field("currency")          or "MWK"
        total_amount      = get_field("total_amount")      or get_field("billed_amount")  or get_field("total_claimed_amount") or 0
        confidence_score  = document.get("confidence_score") or 0
        routing_decision  = document.get("routing_decision") or "—"
        missing_fields    = ", ".join(document.get("missing_fields") or []) or "None"
        mongo_id          = str(document.get("_id", "—"))
        export_timestamp  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        line_items = (
            mapped.get("line_items") or
            normalized.get("line_items") or
            canonical.get("line_items") or
            []
        )

        # ── Write to Invoice Summary tab ─────────────────────────────────
        summary_ws = self._get_or_create_tab(spreadsheet, TAB_SUMMARY, SUMMARY_HEADERS)

        summary_row = [
            export_timestamp,
            invoice_number,
            patient_name,
            str(invoice_date),
            insurer,
            str(policy_number),
            hospital_name,
            doctor_name,
            icd_code,
            currency,
            float(total_amount) if total_amount else 0,
            f"{round(float(confidence_score) * 100, 1)}%",
            routing_decision,
            missing_fields,
            mongo_id,
        ]

        try:
            summary_ws.append_row(summary_row, value_input_option="USER_ENTERED")
        except Exception as e:
            raise SheetsExportError(f"Failed to append summary row: {e}")

        logger.info(f"Sheets: appended summary row for invoice {invoice_number}")

        # ── Write to Line Items tab ──────────────────────────────────────
        line_items_ws    = self._get_or_create_tab(spreadsheet, TAB_LINE_ITEMS, LINE_ITEM_HEADERS)
        line_item_count  = 0

        for item in line_items:
            if not isinstance(item, dict):
                continue
            row = [
                invoice_number,
                item.get("line_number") or (line_item_count + 1),
                item.get("tariff_code") or "—",
                item.get("description") or "—",
                str(item.get("date") or "—"),
                item.get("quantity")   or 1,
                float(item.get("unit_price") or 0),
                float(item.get("amount")     or 0),
            ]
            try:
                line_items_ws.append_row(row, value_input_option="USER_ENTERED")
                line_item_count += 1
            except Exception as e:
                logger.warning(f"Sheets: failed to append line item row: {e}")

        logger.info(
            f"Sheets: appended {line_item_count} line item row(s) "
            f"for invoice {invoice_number}"
        )

        return {
            "spreadsheet_id":  spreadsheet_id,
            "sheet_url":       sheet_url,
            "summary_row":     summary_row,
            "line_item_count": line_item_count,
        }


# Global singleton
sheets_service = SheetsService()