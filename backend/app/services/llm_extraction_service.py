# /backend/app/services/llm_extraction_service.py

"""
LLM extraction service — extracts to the CANONICAL schema only.

The LLM knows nothing about insurers. It always outputs the same
internal format. Insurer mapping happens downstream in mapping_engine.py.
"""

import httpx
import json
import re
import logging
from typing import Dict, Any, Optional

from app.services.canonical_schema import build_canonical_prompt_schema, empty_canonical

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"

# Fixed prompt schema shown to the LLM — built from canonical schema
_PROMPT_SCHEMA = json.dumps(build_canonical_prompt_schema(), indent=2)


class LLMExtractionService:

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Text cleaning
    # ------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        lines = text.splitlines()
        cleaned = []
        seen = set()
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped in seen:
                continue
            seen.add(stripped)
            cleaned.append(stripped)
        return "\n".join(cleaned)

    # ------------------------------------------------------------------
    # Prompt — generic, no insurer-specific logic
    # ------------------------------------------------------------------

    def _build_prompt(self, clean_text: str) -> str:
        return f"""You are a medical invoice data extraction system.

Extract the following fields from the OCR text below.
Return ONLY valid JSON matching the schema exactly.
No explanation. No markdown. No code blocks. Raw JSON only.

Field guide:
- patient_name:   Full name of the patient
- invoice_number: Invoice, claim, or reference number
- invoice_date:   Date of service or invoice (as written in the document)
- hospital_name:  Name of the hospital, clinic, or provider
- doctor_name:    Name of the attending doctor or practitioner
- icd_code:       ICD diagnosis code (e.g. J06.9, Z01.7)
- insurer:        Name of the medical aid, insurer, or fund
- policy_number:  Member number, policy number, or scheme number
- total_amount:   Total amount charged — numbers only, no symbols
- currency:       Currency code (e.g. MWK, USD, KES)
- line_items:     Array of individual service charges

Rules:
- Use null for any field not found
- total_amount and all line item amounts must be numbers only
- Always return the complete schema even if all values are null
- Never add extra fields not in the schema

Schema:
{_PROMPT_SCHEMA}

OCR TEXT:
\"\"\"
{clean_text}
\"\"\"
"""

    # ------------------------------------------------------------------
    # Ollama call with retry
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
                                "num_ctx": 2048,
                                "num_predict": 512,
                                "temperature": 0.1,
                            },
                        },
                    )
                    response.raise_for_status()
                    raw = response.json().get("response", "")
                    logger.info(f"Ollama response: {raw[:200]}")
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
    # JSON parsing
    # ------------------------------------------------------------------

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        try:
            clean = re.sub(r"```json|```", "", raw).strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
            logger.warning("Could not parse JSON from LLM response")
            return {"parse_error": True, "raw_response": raw[:500]}

    # ------------------------------------------------------------------
    # Canonical schema enforcement
    # ------------------------------------------------------------------

    def _enforce_canonical(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure the parsed response strictly matches the canonical schema.
        Drops any extra fields the LLM may have added.
        Fills missing fields with None.
        """
        canonical = empty_canonical()

        for key in canonical:
            if key == "line_items":
                items = data.get("line_items", [])
                if not isinstance(items, list):
                    items = []
                canonical["line_items"] = [
                    self._enforce_line_item(item)
                    for item in items
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
    # Public entry point
    # ------------------------------------------------------------------

    async def extract_to_canonical(self, raw_text: str) -> Dict[str, Any]:
        """
        Extract structured fields from OCR text → canonical schema dict.

        This is the only public method. It knows nothing about insurers.
        The caller (route) passes the result to normalization then mapping.

        Returns:
            Canonical schema dict, or error dict on failure.
        """
        if not raw_text or not raw_text.strip():
            return {"error": "No text provided"}

        clean_text = self._clean_text(raw_text)
        logger.info(f"Extracting canonical fields from {len(clean_text)} chars")

        prompt = self._build_prompt(clean_text)
        raw_response = await self._call_ollama(prompt)

        if raw_response is None:
            return {
                "error": "LLM unavailable or timed out",
                "fallback": True,
                "raw_text_preview": raw_text[:300],
            }

        parsed = self._parse_response(raw_response)

        if "parse_error" in parsed:
            return parsed

        return self._enforce_canonical(parsed)


# Global singleton
llm_extraction_service = LLMExtractionService()