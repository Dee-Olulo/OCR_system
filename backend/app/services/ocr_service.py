# /backend/app/services/ocr_service.py

import os
import time
import tempfile
import pytesseract
import numpy as np
from typing import Tuple
from PIL import Image

from app.services.image_processing import ImageProcessor


# ── Tesseract configuration ──────────────────────────────────────────────────
#
#   --oem 3   : LSTM + legacy (best accuracy)
#   --psm 3   : Fully automatic page segmentation — handles multi-column forms
#               correctly.  PSM 6 (single block) was previously used; it fails
#               on two-column claim forms because it treats the whole page as
#               one stream and mangles column order.
#   user_defined_dpi=300 : Belt-and-suspenders DPI override.  Even though
#               image_processing.py now embeds DPI metadata in the PNG, passing
#               this flag ensures Tesseract never falls back to its own (often
#               wrong) DPI detection.
#
TESSERACT_CONFIG = r"--oem 3 --psm 3 -c preserve_interword_spaces=1 -c user_defined_dpi=300"


class OCRService:
    """OCR service supporting multiple engines with multi-page TIFF support."""

    def __init__(self):
        self.image_processor = ImageProcessor()
        self.easyocr_reader = None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_easyocr_reader(self):
        """Lazy-load EasyOCR reader (expensive first call)."""
        if self.easyocr_reader is None:
            import easyocr
            print("📚 Loading EasyOCR reader...")
            self.easyocr_reader = easyocr.Reader(["en"], gpu=False)
        return self.easyocr_reader

    def _preprocess_to_pil(self, image_path: str) -> Image.Image:
        """
        Full preprocessing pipeline → DPI-stamped PIL image ready for Tesseract.

        Returns a PIL image (not a numpy array) so that DPI metadata is
        preserved all the way into pytesseract.image_to_string / image_to_data.
        """
        pil_preprocessed = self.image_processor.preprocess_image(image_path)

        # Deskew on the numpy array, then convert back
        arr = np.array(pil_preprocessed.convert("L"))
        arr = self.image_processor.deskew_image(arr)
        arr = self.image_processor.resize_if_needed(arr)

        # Re-embed DPI after numpy round-trip
        return ImageProcessor.pil_to_tesseract_png(Image.fromarray(arr))

    # ── Single-image extraction ───────────────────────────────────────────────

    def extract_text_tesseract(self, image_path: str) -> Tuple[str, float, float]:
        """
        Extract text using Pytesseract.
        Returns: (text, confidence, processing_time)
        """
        start_time = time.time()

        # Use DPI-stamped PIL image — NOT a raw numpy array
        pil_img = self._preprocess_to_pil(image_path)

        data = pytesseract.image_to_data(
            pil_img,
            output_type=pytesseract.Output.DICT,
            config=TESSERACT_CONFIG,
        )
        confidences = [int(c) for c in data["conf"] if int(c) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        text = pytesseract.image_to_string(pil_img, config=TESSERACT_CONFIG)

        return text.strip(), avg_confidence, time.time() - start_time

    def extract_text_easyocr(self, image_path: str) -> Tuple[str, float, float]:
        """
        Extract text using EasyOCR.
        Returns: (text, confidence, processing_time)
        """
        start_time = time.time()

        reader = self._get_easyocr_reader()

        # EasyOCR accepts a numpy array; it handles DPI internally
        pil_img = self._preprocess_to_pil(image_path)
        arr = np.array(pil_img.convert("L"))

        results = reader.readtext(arr)

        texts, confidences = [], []
        for (_bbox, text, conf) in results:
            texts.append(text)
            confidences.append(conf)

        combined_text = "\n".join(texts)
        avg_confidence = (
            sum(confidences) / len(confidences) * 100 if confidences else 0.0
        )

        return combined_text.strip(), avg_confidence, time.time() - start_time

    def extract_text(self, image_path: str, engine: str = "tesseract") -> dict:
        """
        Extract text from a single image using the specified engine.

        Args:
            image_path: Path to image file (TIFF, PNG, JPEG, …)
            engine: 'tesseract' or 'easyocr' (default: 'tesseract')

        Returns:
            dict with keys: text, confidence, ocr_engine, processing_time,
                            success, error
        """
        try:
            if engine.lower() == "easyocr":
                text, confidence, proc_time = self.extract_text_easyocr(image_path)
            else:
                text, confidence, proc_time = self.extract_text_tesseract(image_path)

            return {
                "text": text,
                "confidence": round(confidence, 2),
                "ocr_engine": engine,
                "processing_time": round(proc_time, 2),
                "success": True,
                "error": None,
            }

        except Exception as e:
            return {
                "text": "",
                "confidence": 0.0,
                "ocr_engine": engine,
                "processing_time": 0.0,
                "success": False,
                "error": str(e),
            }

    def extract_text_both(self, image_path: str) -> dict:
        """
        Extract text using both engines and return the best result.

        Prefers Tesseract for structured forms (it has better layout
        reconstruction), unless EasyOCR leads by more than 10 confidence
        points.

        Returns:
            dict with keys: best_result, tesseract, easyocr
        """
        tesseract_result = self.extract_text(image_path, "tesseract")
        easyocr_result = self.extract_text(image_path, "easyocr")

        if (
            easyocr_result["success"]
            and easyocr_result["confidence"]
            > tesseract_result["confidence"] + 10
        ):
            best_result = easyocr_result
        else:
            best_result = (
                tesseract_result if tesseract_result["success"] else easyocr_result
            )

        return {
            "best_result": best_result,
            "tesseract": tesseract_result,
            "easyocr": easyocr_result,
        }

    # ── Multi-page TIFF support ───────────────────────────────────────────────

    def extract_text_multipage(self, image_path: str, engine: str = "tesseract") -> dict:
        """
        Extract text from every page of a multi-page TIFF.

        Single-page images are handled transparently.

        Args:
            image_path: Path to (possibly multi-page) TIFF or other image
            engine: 'tesseract', 'easyocr', or 'both'

        Returns:
            dict with keys: text, pages, confidence, ocr_engine,
                            processing_time, success, error
        """
        start_time = time.time()

        try:
            pages = self.image_processor.load_all_pages(image_path)
        except Exception as e:
            return {
                "text": "",
                "pages": 0,
                "confidence": 0.0,
                "ocr_engine": engine,
                "processing_time": 0.0,
                "success": False,
                "error": f"Failed to load image pages: {e}",
            }

        page_texts = []
        page_confidences = []
        errors = []

        for page_index, pil_page in enumerate(pages):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
                pil_page.save(tmp_path, format="PNG")

            try:
                if engine == "both":
                    result = self.extract_text_both(tmp_path)
                    page_result = result["best_result"]
                else:
                    page_result = self.extract_text(tmp_path, engine)

                if page_result["success"]:
                    page_texts.append(page_result["text"])
                    page_confidences.append(page_result["confidence"])
                else:
                    errors.append(f"Page {page_index + 1}: {page_result['error']}")
                    page_texts.append("")

            finally:
                os.unlink(tmp_path)

        combined_text = "\n\n--- PAGE BREAK ---\n\n".join(page_texts).strip()
        avg_confidence = (
            sum(page_confidences) / len(page_confidences) if page_confidences else 0.0
        )

        return {
            "text": combined_text,
            "pages": len(pages),
            "confidence": round(avg_confidence, 2),
            "ocr_engine": engine,
            "processing_time": round(time.time() - start_time, 2),
            "success": len(page_texts) > 0 and any(t for t in page_texts),
            "error": "; ".join(errors) if errors else None,
        }


# Global OCR service instance
ocr_service = OCRService()