# /backend/app/services/entity_extraction_service.py

import spacy
import re
from typing import Dict, List
from datetime import datetime

class EntityExtractionService:
    """Service for extracting entities from text using NLP"""
    
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            print("⚠️  SpaCy model not loaded. Run: python -m spacy download en_core_web_sm")
            self.nlp = None
    
    def extract_entities(self, text: str) -> Dict:
        """
        Extract named entities and key information from text
        Returns dictionary with extracted entities
        """
        entities = {
            "persons": [],
            "organizations": [],
            "locations": [],
            "dates": [],
            "money": [],
            "emails": [],
            "phone_numbers": [],
            "invoice_numbers": [],
            "amounts": [],
            "key_value_pairs": {}
        }
        
        # Extract using SpaCy NER
        if self.nlp and text:
            doc = self.nlp(text)
            
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    entities["persons"].append(ent.text)
                elif ent.label_ == "ORG":
                    # Filter out single letters and very short orgs
                    if len(ent.text) > 2 and not ent.text.isdigit():
                        entities["organizations"].append(ent.text)
                elif ent.label_ in ["GPE", "LOC"]:
                    entities["locations"].append(ent.text)
                elif ent.label_ == "DATE":
                    # Only add if it looks like a real date
                    if self._is_valid_date_format(ent.text):
                        entities["dates"].append(ent.text)
                elif ent.label_ == "MONEY":
                    entities["money"].append(ent.text)
        
        # Extract using regex patterns (more accurate)
        entities["emails"] = self._extract_emails(text)
        entities["phone_numbers"] = self._extract_phone_numbers(text)  # Improved!
        entities["invoice_numbers"] = self._extract_invoice_numbers(text)
        entities["amounts"] = self._extract_amounts(text)
        entities["key_value_pairs"] = self._extract_key_value_pairs_dynamic(text)  # New dynamic extraction!
        
        # Remove duplicates
        for key in entities:
            if isinstance(entities[key], list):
                entities[key] = list(set(entities[key]))
        
        return entities
    
    def _is_valid_date_format(self, text: str) -> bool:
        """Strict date validation to avoid postal codes & random numbers"""

        text = text.strip()

        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',      # 19/07/2022
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',        # 2022-07-19
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
        ]

        if not any(re.search(p, text, re.IGNORECASE) for p in date_patterns):
            return False

        # Reject postal codes & region codes
        if re.search(r'\b[A-Z]{2,}\s+\d{4}\b', text):

        
            return False
            
        return False
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses"""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(pattern, text)
    
    def _extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers - IMPROVED to reduce false positives"""
        phone_numbers = []
        
        patterns = [
                # International format +254 712 345 678
                r'\+\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b',

                # (123) 456-7890
                r'\(\d{3}\)\s*\d{3}[\s.-]?\d{4}\b',

                # 123-456-7890 or 123 456 7890
                r'\b\d{3}[\s.-]\d{3}[\s.-]\d{4}\b',

                # Local mobile formats: 0712 345 678
                r'\b0\d{2}[\s.-]\d{3}[\s.-]\d{3}\b',
            ]

        for pattern in patterns:
                for match in re.findall(pattern, text):
                    digits = re.sub(r'\D', '', match)

                    # E.164 standard
                    if 9 <= len(digits) <= 15:
                        if not self._is_monetary_context(match, text):
                            phone_numbers.append(match.strip())
        return phone_numbers
    
    def _is_monetary_context(self, match: str, text: str) -> bool:
        """Check if number appears in monetary context"""
        # Find position of match in text
        pos = text.find(match)
        if pos == -1:
            return False
        
        # Check surrounding context (20 chars before and after)
        start = max(0, pos - 20)
        end = min(len(text), pos + len(match) + 20)
        context = text[start:end]
        
        # Look for money indicators
        money_indicators = ['$', 'AUD', 'USD', 'EUR', 'price', 'amount', 'total', '.00', ',']
        return any(ind in context for ind in money_indicators)
    
    def _extract_invoice_numbers(self, text: str) -> List[str]:
        """Extract invoice/PO numbers"""
        patterns = [
            r'(?:Invoice|INV|PO|Order)\s*#?\s*:?\s*([A-Z0-9-]+)',
            r'(?:Invoice|INV|PO)\s*(?:Number|No\.?|#)\s*:?\s*([A-Z0-9-]+)',
            r'Reference\s*:?\s*([A-Z0-9-]+)',
        ]
        
        numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            numbers.extend(matches)
        return numbers
    
    def _extract_amounts(self, text: str) -> List[str]:
        """Extract monetary amounts"""
        patterns = [
            r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})',  # $2,510.00
            r'AUD\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
            r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:AUD|USD|EUR|GBP)',
        ]
        
        amounts = []
        for pattern in patterns:
            amounts.extend(re.findall(pattern, text))
        return amounts
    
    def _extract_key_value_pairs_dynamic(self, text: str) -> Dict[str, str]:
        kv_pairs = {}
        lines = text.split('\n')

        for line in lines:
            # Strategy 1: Key: Value
            if ':' in line:
                key, value = line.split(':', 1)
            # Strategy 2: Key    Value (tables / bank statements)
            elif re.search(r'\s{2,}', line):
                parts = re.split(r'\s{2,}', line, 1)
                if len(parts) == 2:
                    key, value = parts
                else:
                    continue
            else:
                continue

            key_clean = self._clean_key(key)
            value = value.strip()

            if self._is_meaningful_key(key_clean) and value:
                kv_pairs[key_clean] = value

        
        return kv_pairs
    
    def _extract_table_fields(self, text: str) -> Dict[str, str]:
        """Extract multiple line items from tables"""
        table_fields = {}

        lines = [l.strip() for l in text.split('\n') if l.strip()]

        headers = None
        items = []

        for i, line in enumerate(lines):
            if re.search(r'description.*quantity.*price.*amount', line, re.IGNORECASE):
                headers = i
                continue

            if headers is not None and i > headers:
                row = re.split(r'\s{2,}', line)
                if len(row) >= 3 and any(char.isdigit() for char in row[-1]):
                    items.append(row)

        for idx, row in enumerate(items, 1):
            table_fields[f'item_{idx}'] = " | ".join(row)
        
        return table_fields
    
    def _clean_key(self, key: str) -> str:
        """Clean and normalize key names"""
        # Convert to lowercase
        key = key.lower()
        
        # Replace spaces with underscores
        key = re.sub(r'\s+', '_', key)
        
        # Remove special characters except underscore
        key = re.sub(r'[^\w_]', '', key)
        
        # Remove trailing/leading underscores
        key = key.strip('_')
        
        return key
    
    def _is_meaningful_key(self, key: str) -> bool:
        """Check if key is meaningful enough to include"""
        # Skip very short keys
        if len(key) < 2:
            return False
        
        # Skip purely numeric keys
        if key.isdigit():
            return False
        
        # Skip common noise words as standalone keys
        noise_words = ['a', 'an', 'the', 'and', 'or', 'by', 'to', 'of', 'in', 'on']
        if key in noise_words:
            return False
        
        return True

entity_extraction_service = EntityExtractionService()