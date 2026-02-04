# /backend/app/services/ocr_service.py

import time
import pytesseract
import easyocr
import numpy as np
from typing import Tuple, Optional, Dict, Any
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
            try:
                self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
                print("✓ EasyOCR reader loaded successfully")
            except Exception as e:
                print(f"✗ Failed to load EasyOCR reader: {e}")
                raise
        return self.easyocr_reader
    
    def extract_text_tesseract(self, image_path: str) -> Tuple[str, float, float]:
        """
        Extract text using Pytesseract
        Returns: (text, confidence, processing_time)
        """
        start_time = time.time()
        
        try:
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
            
            print(f"✓ Tesseract extracted {len(text)} characters (confidence: {avg_confidence:.1f}%)")
            
            return text.strip(), avg_confidence, processing_time
            
        except Exception as e:
            print(f"✗ Tesseract extraction error: {e}")
            processing_time = time.time() - start_time
            return "", 0.0, processing_time
    
    def extract_text_easyocr(self, image_path: str) -> Tuple[str, float, float]:
        """
        Extract text using EasyOCR
        Returns: (text, confidence, processing_time)
        """
        start_time = time.time()
        
        try:
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
            
            print(f"✓ EasyOCR extracted {len(combined_text)} characters (confidence: {avg_confidence:.1f}%)")
            
            return combined_text.strip(), avg_confidence, processing_time
            
        except Exception as e:
            print(f"✗ EasyOCR extraction error: {e}")
            processing_time = time.time() - start_time
            return "", 0.0, processing_time
    
    def extract_text(
        self, 
        image_path: str, 
        engine: str = "tesseract"
    ) -> Dict[str, Any]:
        """
        Extract text using specified engine
        
        Args:
            image_path: Path to image file
            engine: OCR engine to use ('tesseract', 'easyocr', or 'both')
        
        Returns:
            dict with text, confidence, engine, processing_time, success, error
        """
        try:
            print(f"Starting OCR with engine: {engine}")
            
            if engine.lower() == "easyocr":
                text, confidence, proc_time = self.extract_text_easyocr(image_path)
            elif engine.lower() == "both":
                # Use both engines and return best result
                result = self.extract_text_both(image_path)
                return result["best_result"]
            else:
                # Default to tesseract
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
            import traceback
            error_trace = traceback.format_exc()
            print(f"✗ OCR extraction failed: {e}")
            print(error_trace)
            
            return {
                "text": "",
                "confidence": 0.0,
                "ocr_engine": engine,
                "processing_time": 0.0,
                "success": False,
                "error": str(e)
            }
    
    def extract_text_both(self, image_path: str) -> Dict[str, Any]:
        """
        Extract text using both engines and return best result
        
        Returns:
            dict with results from both engines and best result
        """
        print("Using both OCR engines for comparison...")
        
        tesseract_result = self.extract_text(image_path, "tesseract")
        easyocr_result = self.extract_text(image_path, "easyocr")
        
        # Choose best result based on confidence
        if tesseract_result["confidence"] >= easyocr_result["confidence"]:
            best_result = tesseract_result
            print(f"✓ Best result: Tesseract ({tesseract_result['confidence']}% vs {easyocr_result['confidence']}%)")
        else:
            best_result = easyocr_result
            print(f"✓ Best result: EasyOCR ({easyocr_result['confidence']}% vs {tesseract_result['confidence']}%)")
        
        # Mark the best result
        best_result["ocr_engine"] = "both"
        
        return {
            "best_result": best_result,
            "tesseract": tesseract_result,
            "easyocr": easyocr_result
        }

# Global OCR service instance
ocr_service = OCRService()