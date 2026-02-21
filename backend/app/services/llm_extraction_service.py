# /backend/app/services/llm_extraction_service.py

"""
LLM extraction service — extracts to the CANONICAL schema only.

Robustness fixes applied in this version:

  FIX 1 — JSON repair pipeline (3 passes):
    Small LLMs truncate responses and prefix them with preamble text.
    _parse_response() now runs three escalating recovery passes:
      Pass 1: strip markdown fences, skip any prose prefix, direct parse
      Pass 2: repair truncated JSON (close unclosed braces/brackets)
      Pass 3: regex-extract the largest valid JSON object in the response

  FIX 2 — Graceful parse failure:
    When all parse passes fail, we no longer return {parse_error: True}
    into enforce_canonical(). Instead we build an empty canonical dict,
    populate it from structural hints, and continue the pipeline so that
    insurer detection and total backfill can still succeed.

  FIX 3 — Raw-text insurer detection:
    If the LLM fails to extract the insurer field, we scan the raw OCR
    text directly for known insurer aliases as a final fallback. This
    prevents 422 Unprocessable Entity errors when JSON parsing degrades.

  FIX 4 — Table section stripped from LLM input:
    The billing table rows are handled entirely by TableExtractor. Sending
    them to the LLM wastes ~36% of the token budget and causes the model
    to confuse table numbers with header field values. We strip table rows
    before building the prompt and add them back from TableExtractor output.

  FIX 5 — Increased token limits:
    num_predict: 512 → 1024   (prevents JSON truncation mid-object)
    num_ctx:    2048 → 4096   (handles longer OCR documents)

  FIX 6 — Leaner prompt schema:
    Removed the example line_item block from the prompt schema. The LLM
    is instructed to leave line_items as [] anyway, so the example was
    consuming ~60 tokens for nothing.

  CARRY-OVER — Structural pre-extraction + backfill:
    policy_number  — extracted from garbled MEMBER's No grid cells
    invoice_number — extracted from year-based reference pattern
    total_amount   — backfilled from TableExtractor claimed_total
"""

import re
import httpx
import json
import logging
from typing import Dict, Any, Optional, List

from app.services.canonical_schema import build_canonical_prompt_schema, empty_canonical
from app.services.table_extractor import table_extractor, LineItem

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"

# Lean schema for prompt — no example line_item
_LEAN_SCHEMA = json.dumps(
    {k: ([] if k == "line_items" else None)
     for k in build_canonical_prompt_schema()},
    indent=2
)

# Header keyword pattern — used to detect table section in OCR
_HEADER_KEYWORDS = re.compile(
    r"\b(LINE|TARIFF|DESCRIPTION|QTY|QUANTITY|UNIT|PRICE|AMOUNT|DATE|TOOTH|SERVICE)\b",
    re.IGNORECASE,
)


class LLMExtractionService:

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Structural pre-extraction
    # ------------------------------------------------------------------

    def _extract_structural_hints(self, ocr_text: str) -> dict:
        """
        Extract fields that OCR garbles and the LLM cannot reliably recover.

        Fields:
          policy_number   — from grid-box MEMBER's No cells (digit noise stripped)
          invoice_number  — from year-based reference pattern on data row
        """
        hints: dict = {}

        for line in ocr_text.splitlines():
            line_s = line.strip()

            # Member / Policy number
            if re.search(r"MEMBER'?S?\s*N[Oo]\b", line_s, re.IGNORECASE):
                after = re.sub(
                    r"MEMBER'?S?\s*N[Oo]\.?\s*", "", line_s, flags=re.IGNORECASE
                )
                digits = "".join(re.findall(r"\d+", after))
                if 6 <= len(digits) <= 20:
                    hints["policy_number"] = digits
                    logger.info(f"Structural: policy_number={digits}")

            # Invoice number
            if "invoice_number" not in hints:
                inv = re.search(
                    r"\b(\d{4}[_\-]\d{1,2}[_\-]\d{1,2}[_\-\s]?\d+)\b", line_s
                )
                if inv:
                    inv_clean = re.sub(r"\s+", "_", inv.group(1).strip())
                    hints["invoice_number"] = inv_clean
                    logger.info(f"Structural: invoice_number={inv_clean}")

        return hints

    # ------------------------------------------------------------------
    # Text cleaning and table stripping
    # ------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """Deduplicate lines."""
        lines, seen = [], set()
        for line in text.splitlines():
            s = line.strip()
            if s and s not in seen:
                seen.add(s)
                lines.append(s)
        return "\n".join(lines)

    def _strip_table_section(self, ocr_text: str) -> str:
        """
        Remove billing table rows before sending to LLM.

        TableExtractor handles all line items. Sending table rows to the
        LLM wastes ~36% of the token budget and causes the model to
        confuse numeric table values with header field values.

        ICD code lines are preserved because they contain icd_code.
        """
        lines = ocr_text.splitlines()
        result = []
        in_table = False

        for line in lines:
            stripped = line.strip()

            # Detect table header: 2+ keyword hits
            if len(_HEADER_KEYWORDS.findall(stripped)) >= 2:
                in_table = True
                continue

            if in_table:
                # Re-emerge for ICD / diagnosis lines
                if re.match(r"^(ICD|Z\d|J\d|DIAGNOSIS)", stripped, re.IGNORECASE):
                    in_table = False
                    result.append(line)
                # Skip all other table content
                continue

            result.append(line)

        return "\n".join(result)

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def _build_prompt(self, clean_text: str, hints: dict) -> str:
        hint_block = ""
        if hints:
            hint_block = "\nPre-extracted fields (use these if uncertain):\n"
            for field, value in hints.items():
                hint_block += f"  {field}: {value}\n"

        return f"""You are a medical invoice data extraction system.

Extract header fields from the OCR text.
Return ONLY valid JSON. No explanation. No markdown. Raw JSON only.

Fields:
patient_name, invoice_number, invoice_date, hospital_name, doctor_name,
icd_code, insurer, policy_number, total_amount (number only), currency,
line_items (always leave as []).

Use null for missing fields. Never add extra fields.
{hint_block}
Schema:
{_LEAN_SCHEMA}

OCR TEXT:
\"\"\"
{clean_text}
\"\"\"
"""

    # ------------------------------------------------------------------
    # Ollama call
    # ------------------------------------------------------------------

    async def _call_ollama(self, prompt: str, retries: int = 2) -> Optional[str]:
        for attempt in range(retries + 1):
            try:
                logger.info(f"Ollama attempt {attempt + 1}/{retries + 1}")
                async with httpx.AsyncClient(timeout=600) as client:
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "num_ctx": 4096,
                                "num_predict": 1024,
                                "temperature": 0.1,
                            },
                        },
                    )
                    response.raise_for_status()
                    raw = response.json().get("response", "")
                    logger.info(f"Ollama raw ({len(raw)} chars): {raw[:300]}")
                    return raw

            except httpx.ConnectError:
                logger.error("Ollama not running. Start with: ollama serve")
                return None
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt == retries:
                    return None
            except Exception as e:
                logger.error(f"Ollama error: {e}")
                return None

        return None

    # ------------------------------------------------------------------
    # JSON parsing — 3-pass recovery pipeline
    # ------------------------------------------------------------------

    def _repair_json(self, raw: str) -> str:
        """
        Close unclosed braces/brackets from a truncated LLM response.
        Also strips markdown fences and any prose prefix before the JSON.
        """
        s = re.sub(r"```json|```", "", raw).strip()

        # Skip any prose prefix — find the opening brace
        start = s.find("{")
        if start > 0:
            s = s[start:]
        if start == -1:
            return s

        # Remove trailing comma before we close
        s = re.sub(r",\s*$", "", s.rstrip())

        # Close unclosed structures
        open_brackets = s.count("[") - s.count("]")
        open_braces   = s.count("{") - s.count("}")
        s += "]" * max(open_brackets, 0)
        s += "}" * max(open_braces,   0)

        return s

    def _parse_response(self, raw: str) -> tuple[Optional[dict], bool]:
        """
        Three-pass JSON extraction.

        Returns: (parsed_dict_or_None, parse_succeeded)
        """
        # Pass 1 — strip fences, skip prose prefix, direct parse
        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            start = clean.find("{")
            if start > 0:
                clean = clean[start:]
            if start != -1:
                return json.loads(clean), True
        except (json.JSONDecodeError, ValueError):
            pass

        # Pass 2 — repair truncation (close unclosed braces/brackets)
        try:
            repaired = self._repair_json(raw)
            return json.loads(repaired), True
        except (json.JSONDecodeError, ValueError):
            pass

        # Pass 3 — regex-extract the largest JSON object
        matches = list(re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw, re.DOTALL))
        if matches:
            largest = max(matches, key=lambda m: len(m.group()))
            try:
                return json.loads(largest.group()), True
            except (json.JSONDecodeError, ValueError):
                pass

        logger.warning(f"All JSON parse passes failed. Raw preview: {raw[:300]}")
        return None, False

    # ------------------------------------------------------------------
    # Schema enforcement
    # ------------------------------------------------------------------

    def _enforce_canonical(self, data: Dict[str, Any]) -> Dict[str, Any]:
        canonical = empty_canonical()
        for key in canonical:
            if key == "line_items":
                items = data.get("line_items", [])
                canonical["line_items"] = [
                    self._enforce_line_item(item)
                    for item in (items if isinstance(items, list) else [])
                    if isinstance(item, dict)
                ]
            else:
                canonical[key] = data.get(key)
        return canonical

    def _enforce_line_item(self, item: dict) -> dict:
        return {
            "description": item.get("description"),
            "tariff_code":  item.get("tariff_code"),
            "quantity":     item.get("quantity"),
            "unit_price":   item.get("unit_price"),
            "amount":       item.get("amount"),
            "date":         item.get("date"),
        }

    # ------------------------------------------------------------------
    # Backfill helpers
    # ------------------------------------------------------------------

    def _backfill_from_hints(self, canonical: dict, hints: dict) -> dict:
        """Fill LLM nulls with structurally-extracted values."""
        for field, value in hints.items():
            if not canonical.get(field):
                canonical[field] = value
                logger.info(f"Backfilled {field} from structural hints")
        return canonical

    def _backfill_total(self, canonical: dict, claimed_total: Optional[float]) -> dict:
        """Backfill total_amount from the table extractor grand total."""
        if not canonical.get("total_amount") and claimed_total is not None:
            canonical["total_amount"] = claimed_total
            logger.info(f"Backfilled total_amount from table: {claimed_total}")
        return canonical

    def _backfill_insurer_from_text(
        self, canonical: dict, ocr_text: str, aliases_map: dict
    ) -> dict:
        """
        Last-resort insurer detection by scanning raw OCR for known aliases.

        Called only when the LLM failed to populate canonical['insurer'].
        aliases_map shape: {insurer_key: [alias1, alias2, ...]}
        This is built from insurer configs by the caller.
        """
        if canonical.get("insurer"):
            return canonical

        text_upper = ocr_text.upper()
        for key, aliases in aliases_map.items():
            for alias in aliases:
                if alias.upper() in text_upper:
                    canonical["insurer"] = alias
                    logger.info(f"Insurer detected from raw text: {key} ({alias})")
                    return canonical

        return canonical

    # ------------------------------------------------------------------
    # Line item merging
    # ------------------------------------------------------------------

    def _merge_line_items(
        self,
        table_items: List[LineItem],
        llm_items: List[dict],
    ) -> List[dict]:
        """Table extractor wins on amounts; LLM fills description gaps."""
        if not table_items:
            return llm_items

        merged = []
        for i, t_item in enumerate(table_items):
            base = t_item.to_dict()
            if i < len(llm_items):
                llm = llm_items[i]
                if not base.get("description") and llm.get("description"):
                    base["description"] = llm["description"]
                if not base.get("tariff_code") and llm.get("tariff_code"):
                    base["tariff_code"] = llm["tariff_code"]
            merged.append(base)
        return merged

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def extract_to_canonical(
        self,
        raw_text: str,
        insurer_aliases_map: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Full extraction pipeline:

        1. Structural pre-extraction  → policy_number, invoice_number
        2. TableExtractor             → line items, claimed_total
        3. Strip table from OCR       → lean LLM input
        4. LLM call                   → header fields
        5. 3-pass JSON parse + repair
        6. Backfill: hints, total, insurer (from raw text if needed)
        7. Merge line items

        Args:
            raw_text:            Full OCR text.
            insurer_aliases_map: Optional {key: [aliases]} for raw-text
                                 insurer detection fallback. Loaded by the
                                 route from insurer_mapper.

        Returns:
            Canonical schema dict (never raises on LLM failure).
        """
        if not raw_text or not raw_text.strip():
            return {"error": "No text provided"}

        # ── 1. Structural hints ───────────────────────────────────────
        hints = self._extract_structural_hints(raw_text)
        logger.info(f"Structural hints: {hints}")

        # ── 2. Table extraction ───────────────────────────────────────
        table_result = table_extractor.extract(raw_text)
        logger.info(
            f"Table: {len(table_result.line_items)} items | "
            f"claimed_total={table_result.claimed_total} | "
            f"match={table_result.total_match}"
        )

        # ── 3. Build lean LLM input (table rows stripped) ─────────────
        stripped_ocr = self._strip_table_section(raw_text)
        clean_text = self._clean_text(stripped_ocr)
        logger.info(f"LLM input: {len(clean_text)} chars (from {len(raw_text)} raw)")

        # ── 4. LLM call ───────────────────────────────────────────────
        prompt = self._build_prompt(clean_text, hints)
        raw_response = await self._call_ollama(prompt)

        # ── 5. Parse + enforce ────────────────────────────────────────
        if raw_response is not None:
            parsed, ok = self._parse_response(raw_response)
        else:
            parsed, ok = None, False

        if ok and parsed:
            canonical = self._enforce_canonical(parsed)
        else:
            # Parse completely failed — start from empty canonical
            # Pipeline continues; structural hints + table data save the response
            logger.warning("LLM parse failed — continuing with structural data only")
            canonical = empty_canonical()

        # ── 6. Backfills ──────────────────────────────────────────────
        canonical = self._backfill_from_hints(canonical, hints)
        canonical = self._backfill_total(canonical, table_result.claimed_total)

        if insurer_aliases_map and not canonical.get("insurer"):
            canonical = self._backfill_insurer_from_text(
                canonical, raw_text, insurer_aliases_map
            )

        # ── 7. Merge line items ───────────────────────────────────────
        canonical["line_items"] = self._merge_line_items(
            table_result.line_items,
            canonical.get("line_items", []),
        )

        # ── Attach table validation metadata ─────────────────────────
        canonical["_table_validation"] = {
            "claimed_total":    table_result.claimed_total,
            "computed_total":   table_result.computed_total,
            "total_match":      table_result.total_match,
            "discrepancies":    table_result.discrepancies,
            "table_confidence": table_result.confidence,
            "llm_parse_ok":     ok,
        }

        return canonical


# Global singleton
llm_extraction_service = LLMExtractionService()