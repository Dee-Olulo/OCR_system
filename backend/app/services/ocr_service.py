
# /backend/app/services/ocr_service.py
import os
import time
import tempfile
import pytesseract
import easyocr
import numpy as np
from typing import Tuple, Optional
from PIL import Image

from app.services.image_processing import ImageProcessor


# Tesseract configuration:
#   --oem 3   : Use both LSTM and legacy engine (best accuracy)
#   --psm 6   : Assume a uniform block of text — good for structured forms
#   preserve_interword_spaces=1 : Prevents words from being merged across columns
TESSERACT_CONFIG = r"--oem 3 --psm 6 -c preserve_interword_spaces=1"


class OCRService:
    """OCR service supporting multiple engines with multi-page TIFF support"""

    def __init__(self):
        self.image_processor = ImageProcessor()
        self.easyocr_reader = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_easyocr_reader(self):
        """Lazy-load EasyOCR reader (expensive first call)"""
        if self.easyocr_reader is None:
            print("📚 Loading EasyOCR reader...")
            self.easyocr_reader = easyocr.Reader(["en"], gpu=False)
        return self.easyocr_reader

    def _preprocess_to_array(self, image_path: str) -> np.ndarray:
        """Full preprocessing pipeline → numpy array ready for OCR"""
        processed = self.image_processor.preprocess_image(image_path)
        processed = self.image_processor.deskew_image(processed)
        processed = self.image_processor.resize_if_needed(processed)
        return processed

    # ------------------------------------------------------------------
    # Single-image extraction
    # ------------------------------------------------------------------

    def extract_text_tesseract(self, image_path: str) -> Tuple[str, float, float]:
        """
        Extract text using Pytesseract.
        Returns: (text, confidence, processing_time)
        """
        start_time = time.time()

        processed_img = self._preprocess_to_array(image_path)

        # Confidence data
        data = pytesseract.image_to_data(
            processed_img,
            output_type=pytesseract.Output.DICT,
            config=TESSERACT_CONFIG,
        )
        confidences = [int(c) for c in data["conf"] if int(c) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Full text
        text = pytesseract.image_to_string(processed_img, config=TESSERACT_CONFIG)

        return text.strip(), avg_confidence, time.time() - start_time

    def extract_text_easyocr(self, image_path: str) -> Tuple[str, float, float]:
        """
        Extract text using EasyOCR.
        Returns: (text, confidence, processing_time)
        """
        start_time = time.time()

        reader = self._get_easyocr_reader()

        # EasyOCR works on the preprocessed numpy array directly
        processed_img = self._preprocess_to_array(image_path)

        results = reader.readtext(processed_img)

        texts = []
        confidences = []
        for (_bbox, text, conf) in results:
            texts.append(text)
            confidences.append(conf)

        combined_text = "\n".join(texts)
        avg_confidence = (
            sum(confidences) / len(confidences) * 100 if confidences else 0.0
        )

        return combined_text.strip(), avg_confidence, time.time() - start_time

    def extract_text(
        self,
        image_path: str,
        engine: str = "easyocr",
    ) -> dict:
        """
        Extract text from a single image using the specified engine.

        Args:
            image_path: Path to image file (TIFF, PNG, JPEG, …)
            engine: 'tesseract' or 'easyocr' (default: 'easyocr')

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

        Prefers EasyOCR unless Tesseract's confidence exceeds it by more than
        10 points — Tesseract's self-reported confidence tends to be inflated,
        so a simple ≥ comparison would incorrectly favour it too often.

        Returns:
            dict with keys: best_result, tesseract, easyocr
        """
        tesseract_result = self.extract_text(image_path, "tesseract")
        easyocr_result = self.extract_text(image_path, "easyocr")

        # Only prefer Tesseract when it's clearly ahead
        if (
            tesseract_result["success"]
            and tesseract_result["confidence"]
            > easyocr_result["confidence"] + 10
        ):
            best_result = tesseract_result
        else:
            best_result = easyocr_result if easyocr_result["success"] else tesseract_result

        return {
            "best_result": best_result,
            "tesseract": tesseract_result,
            "easyocr": easyocr_result,
        }

    # ------------------------------------------------------------------
    # Multi-page TIFF support
    # ------------------------------------------------------------------

    def extract_text_multipage(
        self,
        image_path: str,
        engine: str = "easyocr",
    ) -> dict:
        """
        Extract text from every page of a multi-page TIFF.

        Single-page images are handled transparently — this method is safe to
        call for any image format.

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
            # Write each page to a temporary PNG so existing extract_text()
            # methods can consume it without modification
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
                    errors.append(
                        f"Page {page_index + 1}: {page_result['error']}"
                    )
                    page_texts.append("")

            finally:
                os.unlink(tmp_path)

        combined_text = "\n\n--- PAGE BREAK ---\n\n".join(page_texts).strip()
        avg_confidence = (
            sum(page_confidences) / len(page_confidences)
            if page_confidences
            else 0.0
        )
        processing_time = time.time() - start_time

        return {
            "text": combined_text,
            "pages": len(pages),
            "confidence": round(avg_confidence, 2),
            "ocr_engine": engine,
            "processing_time": round(processing_time, 2),
            "success": len(page_texts) > 0 and any(t for t in page_texts),
            "error": "; ".join(errors) if errors else None,
        }


# Global OCR service instance
ocr_service = OCRService()

# import os
# import time
# import tempfile
# import pytesseract
# import easyocr
# import numpy as np
# from typing import Tuple
# from PIL import Image

# from app.services.image_processing import ImageProcessor


# # Tesseract configuration:
# #   --oem 3   : Use both LSTM and legacy engine (best accuracy)
# #   --psm 6   : Assume a uniform block of text — good for structured forms
# #   preserve_interword_spaces=1 : Prevents words from being merged across columns
# TESSERACT_CONFIG = r"--oem 3 --psm 6 -c preserve_interword_spaces=1"


# class OCRService:
#     """OCR service supporting multiple engines with multi-page TIFF support"""

#     def __init__(self):
#         self.image_processor = ImageProcessor()
#         self.easyocr_reader = None

#     # ------------------------------------------------------------------
#     # Internal helpers
#     # ------------------------------------------------------------------

#     def _get_easyocr_reader(self):
#         """Lazy-load EasyOCR reader (expensive first call)"""
#         if self.easyocr_reader is None:
#             print("📚 Loading EasyOCR reader...")
#             self.easyocr_reader = easyocr.Reader(["en"], gpu=False)
#         return self.easyocr_reader

#     def _preprocess_for_tesseract(self, image_path: str) -> np.ndarray:
#         """
#         Preprocessing pipeline for Tesseract → binary image.
#         Tesseract is a classical CV engine that works best on clean binary.
#         """
#         processed = self.image_processor.preprocess_image(image_path)
#         processed = self.image_processor.deskew_image(processed)
#         processed = self.image_processor.resize_if_needed(processed)
#         return processed

#     def _preprocess_for_easyocr(self, image_path: str) -> np.ndarray:
#         """
#         Preprocessing pipeline for EasyOCR → grayscale image.

#         EasyOCR is a deep learning model (CRAFT detector + recognition CNN).
#         It needs grayscale with good local contrast — NOT binary.
#         Binary images destroy the gradient information that CRAFT uses
#         to detect and score text regions, which is why EasyOCR was
#         underperforming: it was receiving the same binary output as Tesseract.
#         """
#         processed = self.image_processor.preprocess_image_for_easyocr(image_path)
#         processed = self.image_processor.deskew_image(processed)
#         processed = self.image_processor.resize_if_needed(processed)
#         return processed

#     # ------------------------------------------------------------------
#     # Single-image extraction
#     # ------------------------------------------------------------------

#     def extract_text_tesseract(self, image_path: str) -> Tuple[str, float, float]:
#         """
#         Extract text using Pytesseract.
#         Returns: (text, confidence, processing_time)
#         """
#         start_time = time.time()

#         processed_img = self._preprocess_for_tesseract(image_path)

#         data = pytesseract.image_to_data(
#             processed_img,
#             output_type=pytesseract.Output.DICT,
#             config=TESSERACT_CONFIG,
#         )
#         confidences = [int(c) for c in data["conf"] if int(c) > 0]
#         avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

#         text = pytesseract.image_to_string(processed_img, config=TESSERACT_CONFIG)

#         return text.strip(), avg_confidence, time.time() - start_time

#     def extract_text_easyocr(self, image_path: str) -> Tuple[str, float, float]:
#         """
#         Extract text using EasyOCR.
#         Returns: (text, confidence, processing_time)
#         """
#         start_time = time.time()

#         reader = self._get_easyocr_reader()

#         # EasyOCR receives grayscale (not binary) — preserves gradients
#         # needed by the CRAFT text detector and recognition CNN
#         processed_img = self._preprocess_for_easyocr(image_path)

#         results = reader.readtext(processed_img)

#         texts = []
#         confidences = []
#         for (_bbox, text, conf) in results:
#             texts.append(text)
#             confidences.append(conf)

#         combined_text = "\n".join(texts)
#         avg_confidence = (
#             sum(confidences) / len(confidences) * 100 if confidences else 0.0
#         )

#         return combined_text.strip(), avg_confidence, time.time() - start_time

#     def extract_text(
#         self,
#         image_path: str,
#         engine: str = "easyocr",
#     ) -> dict:
#         """
#         Extract text from a single image using the specified engine.

#         Args:
#             image_path: Path to image file (TIFF, PNG, JPEG, …)
#             engine: 'tesseract' or 'easyocr' (default: 'easyocr')

#         Returns:
#             dict with keys: text, confidence, ocr_engine, processing_time,
#                             success, error
#         """
#         try:
#             if engine.lower() == "easyocr":
#                 text, confidence, proc_time = self.extract_text_easyocr(image_path)
#             else:
#                 text, confidence, proc_time = self.extract_text_tesseract(image_path)

#             return {
#                 "text": text,
#                 "confidence": round(confidence, 2),
#                 "ocr_engine": engine,
#                 "processing_time": round(proc_time, 2),
#                 "success": True,
#                 "error": None,
#             }

#         except Exception as e:
#             return {
#                 "text": "",
#                 "confidence": 0.0,
#                 "ocr_engine": engine,
#                 "processing_time": 0.0,
#                 "success": False,
#                 "error": str(e),
#             }

#     def extract_text_both(self, image_path: str) -> dict:
#         """
#         Extract text using both engines and return the best result.

#         Prefers EasyOCR unless Tesseract's confidence exceeds it by more than
#         10 points — Tesseract's self-reported confidence tends to be inflated,
#         so a simple ≥ comparison would incorrectly favour it too often.

#         Returns:
#             dict with keys: best_result, tesseract, easyocr
#         """
#         tesseract_result = self.extract_text(image_path, "tesseract")
#         easyocr_result = self.extract_text(image_path, "easyocr")

#         if (
#             tesseract_result["success"]
#             and tesseract_result["confidence"] > easyocr_result["confidence"] + 10
#         ):
#             best_result = tesseract_result
#         else:
#             best_result = easyocr_result if easyocr_result["success"] else tesseract_result

#         return {
#             "best_result": best_result,
#             "tesseract": tesseract_result,
#             "easyocr": easyocr_result,
#         }

#     # ------------------------------------------------------------------
#     # Multi-page TIFF support
#     # ------------------------------------------------------------------

#     def extract_text_multipage(
#         self,
#         image_path: str,
#         engine: str = "easyocr",
#     ) -> dict:
#         """
#         Extract text from every page of a multi-page TIFF.

#         Single-page images are handled transparently — this method is safe to
#         call for any image format.

#         Args:
#             image_path: Path to (possibly multi-page) TIFF or other image
#             engine: 'tesseract', 'easyocr', or 'both'

#         Returns:
#             dict with keys: text, pages, confidence, ocr_engine,
#                             processing_time, success, error
#         """
#         start_time = time.time()

#         try:
#             pages = self.image_processor.load_all_pages(image_path)
#         except Exception as e:
#             return {
#                 "text": "",
#                 "pages": 0,
#                 "confidence": 0.0,
#                 "ocr_engine": engine,
#                 "processing_time": 0.0,
#                 "success": False,
#                 "error": f"Failed to load image pages: {e}",
#             }

#         page_texts = []
#         page_confidences = []
#         errors = []

#         for page_index, pil_page in enumerate(pages):
#             with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
#                 tmp_path = tmp.name
#                 pil_page.save(tmp_path, format="PNG")

#             try:
#                 if engine == "both":
#                     result = self.extract_text_both(tmp_path)
#                     page_result = result["best_result"]
#                 else:
#                     page_result = self.extract_text(tmp_path, engine)

#                 if page_result["success"]:
#                     page_texts.append(page_result["text"])
#                     page_confidences.append(page_result["confidence"])
#                 else:
#                     errors.append(f"Page {page_index + 1}: {page_result['error']}")
#                     page_texts.append("")

#             finally:
#                 os.unlink(tmp_path)

#         combined_text = "\n\n--- PAGE BREAK ---\n\n".join(page_texts).strip()
#         avg_confidence = (
#             sum(page_confidences) / len(page_confidences) if page_confidences else 0.0
#         )
#         processing_time = time.time() - start_time

#         return {
#             "text": combined_text,
#             "pages": len(pages),
#             "confidence": round(avg_confidence, 2),
#             "ocr_engine": engine,
#             "processing_time": round(processing_time, 2),
#             "success": len(page_texts) > 0 and any(t for t in page_texts),
#             "error": "; ".join(errors) if errors else None,
#         }


# # Global OCR service instance
# ocr_service = OCRService()