# /backend/app/services/mapping_engine.py

"""
Config-driven mapping engine.

Loads insurer configs from app/config/insurers/{insurer}.json and maps
normalized canonical fields to insurer-specific output field names.

No if/else insurer logic. No field renaming in routes. No hardcoding.
Adding a new insurer = add a new JSON file. Zero code changes.
"""

import json
import os
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config", "insurers")


class InsurerMapper:

    def __init__(self, config_dir: str = CONFIG_DIR):
        self.config_dir = config_dir
        self._cache: dict = {}

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def load_config(self, insurer_name: str) -> dict:
        """
        Load insurer config from JSON file. Caches in memory after first load.
        Raises ValueError if config file not found.
        """
        key = insurer_name.lower()

        if key in self._cache:
            return self._cache[key]

        path = os.path.join(self.config_dir, f"{key}.json")

        if not os.path.exists(path):
            raise ValueError(
                f"No config found for insurer '{insurer_name}'. "
                f"Expected file: {path}. "
                f"Available: {self.list_available()}"
            )

        with open(path, "r") as f:
            config = json.load(f)

        self._cache[key] = config
        logger.info(f"Loaded insurer config: {key} v{config.get('version', '?')}")
        return config

    def list_available(self) -> list[str]:
        """Return list of available insurer keys (JSON filenames without extension)."""
        if not os.path.exists(self.config_dir):
            return []
        return [
            f.replace(".json", "")
            for f in os.listdir(self.config_dir)
            if f.endswith(".json")
        ]

    def detect_insurer(self, canonical_data: dict) -> Optional[str]:
        """
        Auto-detect insurer by matching the extracted insurer field against
        aliases in each config file. Returns the insurer key or None.
        """
        raw = (canonical_data.get("insurer") or "").upper().strip()
        if not raw:
            return None

        for key in self.list_available():
            try:
                config = self.load_config(key)
                aliases = [a.upper() for a in config.get("aliases", [])]
                if any(alias in raw or raw in alias for alias in aliases):
                    logger.info(f"Auto-detected insurer: {key}")
                    return key
            except Exception:
                continue

        logger.warning(f"Could not detect insurer from: '{raw}'")
        return None

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def map_fields(self, canonical_data: dict, insurer_name: str) -> dict:
        """
        Map normalized canonical fields to insurer-specific output field names.

        Args:
            canonical_data: Normalized canonical schema dict
            insurer_name:   Insurer key e.g. 'masm', 'nico'

        Returns:
            Dict with insurer-specific field names and values.
        """
        config = self.load_config(insurer_name)
        output_schema = config.get("output_schema", {})

        output = {}
        for target_field, source_field in output_schema.items():
            output[target_field] = canonical_data.get(source_field)

        return output

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, mapped_output: dict, insurer_name: str) -> dict:
        """
        Check that all required fields are present and non-null.

        Returns:
            dict with keys: success (bool), missing_fields (list)
        """
        config = self.load_config(insurer_name)
        required = config.get("required_fields", [])

        missing = [
            field for field in required
            if not mapped_output.get(field)
        ]

        return {
            "success": len(missing) == 0,
            "missing_fields": missing,
        }

    # ------------------------------------------------------------------
    # Full pipeline (map + validate in one call)
    # ------------------------------------------------------------------

    def process(self, canonical_data: dict, insurer_name: str) -> dict:
        """
        Run the full mapping + validation pipeline for one insurer.

        Args:
            canonical_data: Normalized canonical dict
            insurer_name:   Insurer key

        Returns:
            dict with keys:
              - insurer
              - insurer_display_name
              - mapped_fields
              - success
              - missing_fields
              - config_version
        """
        config = self.load_config(insurer_name)

        mapped = self.map_fields(canonical_data, insurer_name)
        validation = self.validate(mapped, insurer_name)

        return {
            "insurer": insurer_name.upper(),
            "insurer_display_name": config.get("display_name", insurer_name),
            "config_version": config.get("version", "unknown"),
            "mapped_fields": mapped,
            "success": validation["success"],
            "missing_fields": validation["missing_fields"],
        }


# Global singleton — config is cached in memory after first load
insurer_mapper = InsurerMapper()