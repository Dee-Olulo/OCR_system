# backend/app/services/language_detection_service.py

from typing import Tuple, List, Optional
import re
from langdetect import detect, detect_langs, LangDetectException
from collections import Counter

class LanguageDetectionService:
    """Service for detecting document language"""
    
    # Language code mapping (ISO 639-1 to full names and OCR codes)
    LANGUAGE_MAP = {
        'en': {'name': 'English', 'tesseract': 'eng', 'easyocr': 'en'},
        'de': {'name': 'German', 'tesseract': 'deu', 'easyocr': 'de'},
        'fr': {'name': 'French', 'tesseract': 'fra', 'easyocr': 'fr'},
        'es': {'name': 'Spanish', 'tesseract': 'spa', 'easyocr': 'es'},
        'it': {'name': 'Italian', 'tesseract': 'ita', 'easyocr': 'it'},
        'pt': {'name': 'Portuguese', 'tesseract': 'por', 'easyocr': 'pt'},
        'nl': {'name': 'Dutch', 'tesseract': 'nld', 'easyocr': 'nl'},
        'pl': {'name': 'Polish', 'tesseract': 'pol', 'easyocr': 'pl'},
        'ru': {'name': 'Russian', 'tesseract': 'rus', 'easyocr': 'ru'},
        'ja': {'name': 'Japanese', 'tesseract': 'jpn', 'easyocr': 'ja'},
        'zh-cn': {'name': 'Chinese (Simplified)', 'tesseract': 'chi_sim', 'easyocr': 'ch_sim'},
        'zh-tw': {'name': 'Chinese (Traditional)', 'tesseract': 'chi_tra', 'easyocr': 'ch_tra'},
        'ko': {'name': 'Korean', 'tesseract': 'kor', 'easyocr': 'ko'},
        'ar': {'name': 'Arabic', 'tesseract': 'ara', 'easyocr': 'ar'},
        'hi': {'name': 'Hindi', 'tesseract': 'hin', 'easyocr': 'hi'},
        'tr': {'name': 'Turkish', 'tesseract': 'tur', 'easyocr': 'tr'},
        'sv': {'name': 'Swedish', 'tesseract': 'swe', 'easyocr': 'sv'},
        'da': {'name': 'Danish', 'tesseract': 'dan', 'easyocr': 'da'},
        'no': {'name': 'Norwegian', 'tesseract': 'nor', 'easyocr': 'no'},
        'fi': {'name': 'Finnish', 'tesseract': 'fin', 'easyocr': 'fi'},
        'cs': {'name': 'Czech', 'tesseract': 'ces', 'easyocr': 'cs'},
        'el': {'name': 'Greek', 'tesseract': 'ell', 'easyocr': 'el'},
        'he': {'name': 'Hebrew', 'tesseract': 'heb', 'easyocr': 'he'},
        'th': {'name': 'Thai', 'tesseract': 'tha', 'easyocr': 'th'},
        'vi': {'name': 'Vietnamese', 'tesseract': 'vie', 'easyocr': 'vi'},
    }
    
    def __init__(self):
        self.supported_languages = list(self.LANGUAGE_MAP.keys())
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect language from text
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (language_code, confidence)
        """
        if not text or len(text.strip()) < 10:
            return 'en', 0.0
        
        try:
            # Detect with probabilities
            lang_probs = detect_langs(text)
            
            # Get top detection
            top_lang = lang_probs[0]
            lang_code = top_lang.lang
            confidence = top_lang.prob
            
            # Normalize language code
            if lang_code.startswith('zh'):
                # Detect simplified vs traditional Chinese
                lang_code = self._detect_chinese_variant(text)
            
            # Validate language is in our map
            if lang_code not in self.LANGUAGE_MAP:
                # Try to map common variants
                lang_code = self._normalize_language_code(lang_code)
            
            print(f"🌍 Detected language: {self.get_language_name(lang_code)} ({lang_code}) - Confidence: {confidence:.2%}")
            
            return lang_code, confidence
            
        except LangDetectException as e:
            print(f"⚠️  Language detection failed: {e}. Defaulting to English.")
            return 'en', 0.0
    
    def detect_multiple_languages(self, text: str, threshold: float = 0.1) -> List[Tuple[str, float]]:
        """
        Detect multiple languages in text
        
        Args:
            text: Text to analyze
            threshold: Minimum probability threshold
            
        Returns:
            List of (language_code, confidence) tuples
        """
        if not text or len(text.strip()) < 10:
            return [('en', 0.0)]
        
        try:
            lang_probs = detect_langs(text)
            
            # Filter by threshold and normalize
            detected_langs = []
            for lang_prob in lang_probs:
                if lang_prob.prob >= threshold:
                    lang_code = lang_prob.lang
                    
                    # Normalize
                    if lang_code.startswith('zh'):
                        lang_code = self._detect_chinese_variant(text)
                    
                    if lang_code not in self.LANGUAGE_MAP:
                        lang_code = self._normalize_language_code(lang_code)
                    
                    detected_langs.append((lang_code, lang_prob.prob))
            
            return detected_langs if detected_langs else [('en', 0.0)]
            
        except LangDetectException:
            return [('en', 0.0)]
    
    def _detect_chinese_variant(self, text: str) -> str:
        """Detect if Chinese text is simplified or traditional"""
        # Count simplified vs traditional characters
        simplified_chars = re.findall(r'[\u4e00-\u9fff]', text)
        traditional_chars = re.findall(r'[\u3400-\u4dbf\u20000-\u2a6df]', text)
        
        if len(traditional_chars) > len(simplified_chars):
            return 'zh-tw'
        return 'zh-cn'
    
    def _normalize_language_code(self, lang_code: str) -> str:
        """Normalize language code to supported format"""
        # Common mappings
        mappings = {
            'zh': 'zh-cn',
            'nb': 'no',  # Norwegian Bokmål
            'nn': 'no',  # Norwegian Nynorsk
            'sr': 'hr',  # Serbian to Croatian (similar)
            'uk': 'ru',  # Ukrainian to Russian (similar alphabet)
            'be': 'ru',  # Belarusian to Russian (similar alphabet)
        }
        
        return mappings.get(lang_code, 'en')
    
    def get_tesseract_lang_code(self, lang_code: str) -> str:
        """Get Tesseract language code"""
        return self.LANGUAGE_MAP.get(lang_code, self.LANGUAGE_MAP['en'])['tesseract']
    
    def get_easyocr_lang_code(self, lang_code: str) -> str:
        """Get EasyOCR language code"""
        return self.LANGUAGE_MAP.get(lang_code, self.LANGUAGE_MAP['en'])['easyocr']
    
    def get_language_name(self, lang_code: str) -> str:
        """Get full language name"""
        return self.LANGUAGE_MAP.get(lang_code, self.LANGUAGE_MAP['en'])['name']
    
    def get_supported_languages(self) -> List[dict]:
        """Get list of all supported languages"""
        return [
            {
                'code': code,
                'name': info['name'],
                'tesseract': info['tesseract'],
                'easyocr': info['easyocr']
            }
            for code, info in self.LANGUAGE_MAP.items()
        ]
    
    def is_rtl_language(self, lang_code: str) -> bool:
        """Check if language is right-to-left"""
        rtl_languages = ['ar', 'he', 'fa', 'ur']
        return lang_code in rtl_languages
    
    def detect_from_filename(self, filename: str) -> Optional[str]:
        """Try to detect language from filename patterns"""
        filename_lower = filename.lower()
        
        # Common filename patterns
        patterns = {
            r'_de\.|_german\.|_deutsch\.': 'de',
            r'_fr\.|_french\.|_français\.': 'fr',
            r'_es\.|_spanish\.|_español\.': 'es',
            r'_it\.|_italian\.|_italiano\.': 'it',
            r'_pt\.|_portuguese\.|_português\.': 'pt',
            r'_ru\.|_russian\.|_русский\.': 'ru',
            r'_ja\.|_japanese\.|_日本語\.': 'ja',
            r'_zh\.|_chinese\.|_中文\.': 'zh-cn',
            r'_ko\.|_korean\.|_한국어\.': 'ko',
            r'_ar\.|_arabic\.|_العربية\.': 'ar',
        }
        
        for pattern, lang_code in patterns.items():
            if re.search(pattern, filename_lower):
                print(f"🏷️  Detected language from filename: {self.get_language_name(lang_code)}")
                return lang_code
        
        return None

# Global instance
language_detection_service = LanguageDetectionService()