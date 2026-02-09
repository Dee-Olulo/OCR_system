# # /backend/app/services/ocr_service.py

# import time
# import pytesseract
# import easyocr
# import numpy as np
# from typing import Tuple, Optional, Dict, Any
# from app.services.image_processing import ImageProcessor

# class OCRService:
#     """OCR service supporting multiple engines"""
    
#     def __init__(self):
#         self.image_processor = ImageProcessor()
#         self.easyocr_reader = None
    
#     def _get_easyocr_reader(self):
#         """Lazy load EasyOCR reader"""
#         if self.easyocr_reader is None:
#             print("📚 Loading EasyOCR reader...")
#             try:
#                 self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
#                 print("✓ EasyOCR reader loaded successfully")
#             except Exception as e:
#                 print(f"✗ Failed to load EasyOCR reader: {e}")
#                 raise
#         return self.easyocr_reader
    
#     def extract_text_tesseract(self, image_path: str) -> Tuple[str, float, float]:
#         """
#         Extract text using Pytesseract
#         Returns: (text, confidence, processing_time)
#         """
#         start_time = time.time()
        
#         try:
#             # Preprocess image
#             processed_img = self.image_processor.preprocess_image(image_path)
#             processed_img = self.image_processor.deskew_image(processed_img)
#             processed_img = self.image_processor.resize_if_needed(processed_img)
            
#             # Extract text with confidence
#             data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
            
#             # Calculate average confidence
#             confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
#             avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
#             # Extract text
#             text = pytesseract.image_to_string(processed_img)
            
#             processing_time = time.time() - start_time
            
#             print(f"✓ Tesseract extracted {len(text)} characters (confidence: {avg_confidence:.1f}%)")
            
#             return text.strip(), avg_confidence, processing_time
            
#         except Exception as e:
#             print(f"✗ Tesseract extraction error: {e}")
#             processing_time = time.time() - start_time
#             return "", 0.0, processing_time
    
#     def extract_text_easyocr(self, image_path: str) -> Tuple[str, float, float]:
#         """
#         Extract text using EasyOCR
#         Returns: (text, confidence, processing_time)
#         """
#         start_time = time.time()
        
#         try:
#             # Get reader
#             reader = self._get_easyocr_reader()
            
#             # Preprocess image
#             processed_img = self.image_processor.preprocess_image(image_path)
            
#             # Extract text
#             results = reader.readtext(processed_img)
            
#             # Combine results
#             texts = []
#             confidences = []
            
#             for (bbox, text, conf) in results:
#                 texts.append(text)
#                 confidences.append(conf)
            
#             combined_text = '\n'.join(texts)
#             avg_confidence = (sum(confidences) / len(confidences) * 100) if confidences else 0.0
            
#             processing_time = time.time() - start_time
            
#             print(f"✓ EasyOCR extracted {len(combined_text)} characters (confidence: {avg_confidence:.1f}%)")
            
#             return combined_text.strip(), avg_confidence, processing_time
            
#         except Exception as e:
#             print(f"✗ EasyOCR extraction error: {e}")
#             processing_time = time.time() - start_time
#             return "", 0.0, processing_time
    
#     def extract_text(
#         self, 
#         image_path: str, 
#         engine: str = "tesseract"
#     ) -> Dict[str, Any]:
#         """
#         Extract text using specified engine
        
#         Args:
#             image_path: Path to image file
#             engine: OCR engine to use ('tesseract', 'easyocr', or 'both')
        
#         Returns:
#             dict with text, confidence, engine, processing_time, success, error
#         """
#         try:
#             print(f"Starting OCR with engine: {engine}")
            
#             if engine.lower() == "easyocr":
#                 text, confidence, proc_time = self.extract_text_easyocr(image_path)
#             elif engine.lower() == "both":
#                 # Use both engines and return best result
#                 result = self.extract_text_both(image_path)
#                 return result["best_result"]
#             else:
#                 # Default to tesseract
#                 text, confidence, proc_time = self.extract_text_tesseract(image_path)
            
#             return {
#                 "text": text,
#                 "confidence": round(confidence, 2),
#                 "ocr_engine": engine,
#                 "processing_time": round(proc_time, 2),
#                 "success": True,
#                 "error": None
#             }
        
#         except Exception as e:
#             import traceback
#             error_trace = traceback.format_exc()
#             print(f"✗ OCR extraction failed: {e}")
#             print(error_trace)
            
#             return {
#                 "text": "",
#                 "confidence": 0.0,
#                 "ocr_engine": engine,
#                 "processing_time": 0.0,
#                 "success": False,
#                 "error": str(e)
#             }
    
#     def extract_text_both(self, image_path: str) -> Dict[str, Any]:
#         """
#         Extract text using both engines and return best result
        
#         Returns:
#             dict with results from both engines and best result
#         """
#         print("Using both OCR engines for comparison...")
        
#         tesseract_result = self.extract_text(image_path, "tesseract")
#         easyocr_result = self.extract_text(image_path, "easyocr")
        
#         # Choose best result based on confidence
#         if tesseract_result["confidence"] >= easyocr_result["confidence"]:
#             best_result = tesseract_result
#             print(f"✓ Best result: Tesseract ({tesseract_result['confidence']}% vs {easyocr_result['confidence']}%)")
#         else:
#             best_result = easyocr_result
#             print(f"✓ Best result: EasyOCR ({easyocr_result['confidence']}% vs {tesseract_result['confidence']}%)")
        
#         # Mark the best result
#         best_result["ocr_engine"] = "both"
        
#         return {
#             "best_result": best_result,
#             "tesseract": tesseract_result,
#             "easyocr": easyocr_result
#         }

# # Global OCR service instance
# ocr_service = OCRService()

# /backend/app/services/ocr_service.py

import time
import pytesseract
import easyocr
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
from app.services.image_processing import ImageProcessor
from app.services.language_detection_service import language_detection_service

class OCRService:
    """OCR service supporting multiple engines and languages"""
    
    def __init__(self):
        self.image_processor = ImageProcessor()
        self.easyocr_readers = {}  # Cache readers by language
    
    def _get_easyocr_reader(self, lang_codes: List[str]):
        """
        Lazy load EasyOCR reader for specific languages
        
        Args:
            lang_codes: List of language codes for EasyOCR
        """
        # Create cache key from sorted lang codes
        cache_key = ','.join(sorted(lang_codes))
        
        if cache_key not in self.easyocr_readers:
            print(f"📚 Loading EasyOCR reader for languages: {lang_codes}...")
            try:
                self.easyocr_readers[cache_key] = easyocr.Reader(lang_codes, gpu=False)
                print(f"✓ EasyOCR reader loaded successfully for {lang_codes}")
            except Exception as e:
                print(f"✗ Failed to load EasyOCR reader: {e}")
                # Fallback to English
                if 'en' not in lang_codes:
                    print(f"⚠️  Falling back to English reader")
                    return self._get_easyocr_reader(['en'])
                raise
        
        return self.easyocr_readers[cache_key]
    
    def extract_text_tesseract(
        self, 
        image_path: str, 
        lang_code: str = 'en'
    ) -> Tuple[str, float, float, str]:
        """
        Extract text using Pytesseract with language support
        
        Args:
            image_path: Path to image
            lang_code: ISO language code (e.g., 'en', 'de', 'fr')
        
        Returns: (text, confidence, processing_time, detected_language)
        """
        start_time = time.time()
        
        try:
            # Get Tesseract language code
            tesseract_lang = language_detection_service.get_tesseract_lang_code(lang_code)
            lang_name = language_detection_service.get_language_name(lang_code)
            
            print(f"🔤 Using Tesseract with language: {lang_name} ({tesseract_lang})")
            
            # Preprocess image
            processed_img = self.image_processor.preprocess_image(image_path)
            processed_img = self.image_processor.deskew_image(processed_img)
            processed_img = self.image_processor.resize_if_needed(processed_img)
            
            # Extract text with confidence
            data = pytesseract.image_to_data(
                processed_img, 
                lang=tesseract_lang,
                output_type=pytesseract.Output.DICT
            )
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Extract text
            text = pytesseract.image_to_string(processed_img, lang=tesseract_lang)
            
            processing_time = time.time() - start_time
            
            print(f"✓ Tesseract extracted {len(text)} characters (confidence: {avg_confidence:.1f}%)")
            
            return text.strip(), avg_confidence, processing_time, lang_code
            
        except Exception as e:
            print(f"✗ Tesseract extraction error: {e}")
            processing_time = time.time() - start_time
            return "", 0.0, processing_time, lang_code
    
    def extract_text_easyocr(
        self, 
        image_path: str, 
        lang_codes: List[str] = None
    ) -> Tuple[str, float, float, str]:
        """
        Extract text using EasyOCR with multi-language support
        
        Args:
            image_path: Path to image
            lang_codes: List of language codes (e.g., ['en', 'de'])
        
        Returns: (text, confidence, processing_time, detected_language)
        """
        start_time = time.time()
        
        if lang_codes is None:
            lang_codes = ['en']
        
        try:
            # Convert to EasyOCR language codes
            easyocr_langs = [
                language_detection_service.get_easyocr_lang_code(lang) 
                for lang in lang_codes
            ]
            
            print(f"🔤 Using EasyOCR with languages: {easyocr_langs}")
            
            # Get reader
            reader = self._get_easyocr_reader(easyocr_langs)
            
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
            
            # Detect primary language from extracted text
            detected_lang = lang_codes[0]  # Default to first specified language
            if combined_text:
                detected_lang, _ = language_detection_service.detect_language(combined_text)
            
            print(f"✓ EasyOCR extracted {len(combined_text)} characters (confidence: {avg_confidence:.1f}%)")
            
            return combined_text.strip(), avg_confidence, processing_time, detected_lang
            
        except Exception as e:
            print(f"✗ EasyOCR extraction error: {e}")
            processing_time = time.time() - start_time
            return "", 0.0, processing_time, lang_codes[0] if lang_codes else 'en'
    
    def extract_text_with_auto_detection(
        self,
        image_path: str,
        engine: str = "tesseract",
        hint_lang: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract text with automatic language detection
        
        Args:
            image_path: Path to image
            engine: OCR engine ('tesseract', 'easyocr', 'both')
            hint_lang: Optional language hint from filename or metadata
        
        Returns:
            dict with text, confidence, detected language, etc.
        """
        try:
            print(f"🚀 Starting OCR with auto language detection")
            
            # Step 1: Try to get initial text with English (fast baseline)
            if engine.lower() == "easyocr":
                initial_text, _, _, _ = self.extract_text_easyocr(image_path, ['en'])
            else:
                initial_text, _, _, _ = self.extract_text_tesseract(image_path, 'en')
            
            # Step 2: Detect language from initial extraction
            if initial_text and len(initial_text.strip()) > 20:
                detected_lang, lang_confidence = language_detection_service.detect_language(initial_text)
                print(f"🌍 Auto-detected language: {language_detection_service.get_language_name(detected_lang)} (confidence: {lang_confidence:.2%})")
            else:
                # Use hint if available, otherwise default to English
                detected_lang = hint_lang if hint_lang else 'en'
                lang_confidence = 0.5 if hint_lang else 0.0
                print(f"⚠️  Using fallback language: {language_detection_service.get_language_name(detected_lang)}")
            
            # Step 3: Re-extract with detected language if different from English
            if detected_lang != 'en' and lang_confidence > 0.6:
                print(f"🔄 Re-extracting with detected language: {detected_lang}")
                
                if engine.lower() == "easyocr":
                    # EasyOCR can handle multiple languages
                    text, confidence, proc_time, final_lang = self.extract_text_easyocr(
                        image_path, 
                        ['en', detected_lang]  # Include both English and detected language
                    )
                else:
                    # Tesseract with detected language
                    text, confidence, proc_time, final_lang = self.extract_text_tesseract(
                        image_path,
                        detected_lang
                    )
            else:
                # Use initial English extraction
                text = initial_text
                confidence = lang_confidence * 100
                proc_time = 0
                final_lang = 'en'
            
            return {
                "text": text,
                "confidence": round(confidence, 2),
                "detected_language": final_lang,
                "language_name": language_detection_service.get_language_name(final_lang),
                "language_confidence": round(lang_confidence * 100, 2),
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
                "detected_language": "en",
                "language_name": "English",
                "language_confidence": 0.0,
                "ocr_engine": engine,
                "processing_time": 0.0,
                "success": False,
                "error": str(e)
            }
    
    def extract_text(
        self, 
        image_path: str, 
        engine: str = "tesseract",
        lang_code: Optional[str] = None,
        auto_detect: bool = True
    ) -> Dict[str, Any]:
        """
        Extract text using specified engine
        
        Args:
            image_path: Path to image file
            engine: OCR engine to use ('tesseract', 'easyocr', or 'both')
            lang_code: Specific language code (if None, will auto-detect)
            auto_detect: Whether to auto-detect language
        
        Returns:
            dict with text, confidence, language, engine, processing_time, success, error
        """
        try:
            # Auto-detection mode
            if auto_detect and lang_code is None:
                return self.extract_text_with_auto_detection(image_path, engine)
            
            # Manual language specification
            if lang_code is None:
                lang_code = 'en'
            
            print(f"🔤 Starting OCR with engine: {engine}, language: {lang_code}")
            
            if engine.lower() == "easyocr":
                text, confidence, proc_time, detected_lang = self.extract_text_easyocr(
                    image_path, 
                    [lang_code]
                )
            elif engine.lower() == "both":
                # Use both engines and return best result
                result = self.extract_text_both(image_path, lang_code)
                return result["best_result"]
            else:
                # Default to tesseract
                text, confidence, proc_time, detected_lang = self.extract_text_tesseract(
                    image_path,
                    lang_code
                )
            
            return {
                "text": text,
                "confidence": round(confidence, 2),
                "detected_language": detected_lang,
                "language_name": language_detection_service.get_language_name(detected_lang),
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
                "detected_language": lang_code or "en",
                "language_name": language_detection_service.get_language_name(lang_code or "en"),
                "ocr_engine": engine,
                "processing_time": 0.0,
                "success": False,
                "error": str(e)
            }
    
    def extract_text_both(self, image_path: str, lang_code: str = 'en') -> Dict[str, Any]:
        """
        Extract text using both engines and return best result
        
        Args:
            image_path: Path to image
            lang_code: Language code
        
        Returns:
            dict with results from both engines and best result
        """
        print("🔄 Using both OCR engines for comparison...")
        
        tesseract_result = self.extract_text(image_path, "tesseract", lang_code, auto_detect=False)
        easyocr_result = self.extract_text(image_path, "easyocr", lang_code, auto_detect=False)
        
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