# /backend/app/services/llm_extraction_service.py

import httpx
import json
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"


class LLMExtractionService:

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL

    def is_available(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    def _clean_text(self, text: str) -> str:
        lines = text.splitlines()
        cleaned_lines = []
        seen = set()
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped in seen:
                continue
            seen.add(stripped)
            cleaned_lines.append(stripped)
        return "\n".join(cleaned_lines)

    def _build_prompt(self, clean_text: str) -> str:
        return f"""You are an expert medical invoice extraction system.

Extract the following fields if present in the document.
Return ONLY valid JSON. No explanation. No markdown. No code blocks.

Schema:
{{
  "schema_version": "1.0",
  "hospital_name": null,
  "invoice_number": null,
  "invoice_date": null,
  "patient": {{
    "name": null,
    "age": null,
    "gender": null
  }},
  "insurer": null,
  "policy_number": null,
  "total_amount": null,
  "currency": null,
  "line_items": [
    {{
      "description": null,
      "quantity": null,
      "unit_price": null,
      "amount": null
    }}
  ]
}}

Rules:
- Use null for any field not found
- total_amount must be a number only, no symbols
- Always return the full schema even if all fields are null
- Never explain anything outside the JSON

OCR TEXT:
\"\"\"
{clean_text}
\"\"\"
"""

    async def _call_ollama_with_retry(self, clean_text: str, retries: int = 2):
        prompt = self._build_prompt(clean_text)

        for attempt in range(retries + 1):
            try:
                logger.info(f"Ollama call attempt {attempt + 1}")
                async with httpx.AsyncClient(timeout=300) as client:
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False
                        }
                    )
                    response.raise_for_status()
                    raw = response.json().get("response", "")
                    logger.info(f"Ollama response preview: {raw[:300]}")
                    return raw

            except httpx.ConnectError:
                logger.error("Ollama not running. Start with: ollama serve")
                return None
            except httpx.TimeoutException:
                logger.warning(f"Ollama timeout on attempt {attempt + 1}")
                if attempt == retries:
                    return None
            except Exception as e:
                logger.error(f"Ollama error: {e}")
                return None

        return None

    async def extract_invoice_fields(self, raw_text: str) -> Dict[str, Any]:
        if not raw_text or not raw_text.strip():
            return {"error": "No text provided"}

        clean_text = self._clean_text(raw_text)
        logger.info(f"Cleaned text length: {len(clean_text)} chars")

        # ✅ properly awaited
        raw_response = await self._call_ollama_with_retry(clean_text, retries=2)

        if raw_response is None:
            logger.warning("LLM failed — returning fallback")
            return {
                "error": "LLM extraction failed",
                "fallback": True,
                "raw_text_preview": raw_text[:500]
            }

        parsed = self._parse_json_response(raw_response)
        validated = self._validate_schema(parsed)
        return validated

    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
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
            logger.warning("Could not parse JSON from Ollama response")
            return {"parse_error": True, "raw_response": raw}

    def _validate_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "parse_error" in data or "error" in data:
            return data

        return {
            "schema_version": "1.0",
            "hospital_name": data.get("hospital_name"),
            "invoice_number": data.get("invoice_number"),
            "invoice_date": data.get("invoice_date"),
            "patient": {
                "name": data.get("patient", {}).get("name"),
                "age": data.get("patient", {}).get("age"),
                "gender": data.get("patient", {}).get("gender")
            },
            "insurer": data.get("insurer"),
            "policy_number": data.get("policy_number"),
            "total_amount": self._to_float(data.get("total_amount")),
            "currency": data.get("currency"),
            "line_items": self._validate_line_items(data.get("line_items", []))
        }

    def _to_float(self, value) -> float | None:
        if value is None:
            return None
        try:
            cleaned = re.sub(r"[^\d.]", "", str(value))
            return float(cleaned) if cleaned else None
        except Exception:
            return None

    def _validate_line_items(self, items) -> list:
        if not isinstance(items, list):
            return []
        validated = []
        for item in items:
            if not isinstance(item, dict):
                continue
            validated.append({
                "description": item.get("description"),
                "quantity": item.get("quantity"),
                "unit_price": item.get("unit_price"),
                "amount": self._to_float(item.get("amount"))
            })
        return validated


llm_extraction_service = LLMExtractionService()