# /backend/app/services/pdf_service.py

import fitz  # pymupdf
import os
from typing import Tuple, List

class PDFService:

    def extract_text_from_pdf(self, file_path: str) -> Tuple[str, bool, int]:
        """
        Try direct text extraction first.
        Returns: (text, is_scanned, page_count)
        """
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)
            full_text = ""

            for page in doc:
                full_text += page.get_text()

            doc.close()

            is_scanned = len(full_text.strip()) < 50
            return full_text, is_scanned, page_count

        except Exception as e:
            print(f"PDF extraction error: {e}")
            return "", True, 0

    def convert_pdf_to_images(self, file_path: str) -> List[str]:
        """
        Convert each PDF page to a temporary image file.
        Used when PDF is scanned (no text layer).
        Returns list of image file paths.
        """
        image_paths = []
        try:
            doc = fitz.open(file_path)
            base_path = file_path.replace(".pdf", "")

            for i, page in enumerate(doc):
                # Render page at 300 DPI for good OCR accuracy
                mat = fitz.Matrix(300 / 72, 300 / 72)
                pix = page.get_pixmap(matrix=mat)
                img_path = f"{base_path}_page_{i+1}.png"
                pix.save(img_path)
                image_paths.append(img_path)

            doc.close()

        except Exception as e:
            print(f"PDF to image conversion error: {e}")

        return image_paths

    def cleanup_images(self, image_paths: List[str]):
        """Delete temporary page images after OCR"""
        for path in image_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

pdf_service = PDFService()