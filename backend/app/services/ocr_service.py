# /backend/app/services/ocr_service.py

import time
import pytesseract
import easyocr
import numpy as np
from typing import Tuple, Optional
from app.services.image_processing import ImageProcessor


class OCRService:
    """OCR service supporting multiple engines"""
    
    def __init__(self):
        self.image_processor = ImageProcessor()
        self.easyocr_reader = None
    
    def _get_easyocr_reader(self):
        """Lazy load EasyOCR reader"""
        if self.easyocr_reader is None:
            print("📚 Loading EasyOCR reader...")
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
        return self.easyocr_reader
    
    def extract_text_tesseract(self, image_path: str) -> Tuple[str, float, float]:
        """
        Extract text using Pytesseract
        Returns: (text, confidence, processing_time)
        """
        start_time = time.time()
        
        # Preprocess image
        processed_img = self.image_processor.preprocess_image(image_path)
        processed_img = self.image_processor.deskew_image(processed_img)
        processed_img = self.image_processor.resize_if_needed(processed_img)
        
        # Extract text with confidence
        data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
        
        # Calculate average confidence
        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Extract text
        text = pytesseract.image_to_string(processed_img)
        
        processing_time = time.time() - start_time
        
        return text.strip(), avg_confidence, processing_time
    
    def extract_text_easyocr(self, image_path: str) -> Tuple[str, float, float]:
        """
        Extract text using EasyOCR
        Returns: (text, confidence, processing_time)
        """
        start_time = time.time()
        
        # Get reader
        reader = self._get_easyocr_reader()
        
        # Preprocess image
        processed_img = self.image_processor.preprocess_image(image_path)
        
        # Extract text
        results = reader.readtext(processed_img)
        
        # Combine results
        texts = []
        confidences = []
        
        for (bbox, text, conf) in results:
            texts.append(text)
            confidences.append(conf)
        
        combined_text = '\n'.join(texts)
        avg_confidence = (sum(confidences) / len(confidences) * 100) if confidences else 0.0
        
        processing_time = time.time() - start_time
        
        return combined_text.strip(), avg_confidence, processing_time
    
    def extract_text(
        self, 
        image_path: str, 
        engine: str = "tesseract"
    ) -> dict:
        """
        Extract text using specified engine
        
        Args:
            image_path: Path to image file
            engine: OCR engine to use ('tesseract' or 'easyocr')
        
        Returns:
            dict with text, confidence, engine, processing_time
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
                "error": None
            }
        
        except Exception as e:
            return {
                "text": "",
                "confidence": 0.0,
                "ocr_engine": engine,
                "processing_time": 0.0,
                "success": False,
                "error": str(e)
            }
    
    def extract_text_both(self, image_path: str) -> dict:
        """
        Extract text using both engines and return best result
        
        Returns:
            dict with results from both engines
        """
        tesseract_result = self.extract_text(image_path, "tesseract")
        easyocr_result = self.extract_text(image_path, "easyocr")
        
        # Choose best result based on confidence
        if tesseract_result["confidence"] >= easyocr_result["confidence"]:
            best_result = tesseract_result
        else:
            best_result = easyocr_result
        
        return {
            "best_result": best_result,
            "tesseract": tesseract_result,
            "easyocr": easyocr_result
        }

# Global OCR service instance
ocr_service = OCRService()