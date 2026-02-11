# # /backend/app/services/insurance_fields_extractor.py

# from typing import Dict, Any, Optional, List
# import re
# from datetime import datetime

# class InsuranceFieldsExtractor:
#     """
#     Extract standardized insurance-critical fields from hospital invoice OCR output.
#     Works with any hospital invoice format.
#     """
    
#     # Common field name variations across different hospitals
#     FIELD_MAPPINGS = {
#         "patient_name": [
#             "patient_name", "patient", "name of patient", "patient's name",
#             "name", "full name", "beneficiary", "insured name"
#         ],
#         "patient_id": [
#             "patient_id", "patient id", "medical record number", "mrn",
#             "patient number", "record number", "patient no", "id number"
#         ],
#         "date_of_birth": [
#             "date_of_birth", "dob", "birth date", "date of birth",
#             "birthdate", "patient dob", "age/sex"
#         ],
#         "insurance_policy": [
#             "insurance_policy", "policy number", "policy no", "insurance number",
#             "policy id", "member id", "insurance id", "plan number"
#         ],
#         "hospital_name": [
#             "hospital_name", "hospital", "facility", "facility name",
#             "provider", "institution", "medical center"
#         ],
#         "provider_npi": [
#             "npi", "provider_npi", "tax id", "provider id", "tin",
#             "federal tax id", "npi number", "provider number"
#         ],
#         "invoice_number": [
#             "invoice_number", "bill_no", "bill number", "invoice no",
#             "billing number", "claim number", "receipt number", "receipt no"
#         ],
#         "invoice_date": [
#             "invoice_date", "bill date", "billing date", "date",
#             "statement date", "invoice date"
#         ],
#         "admission_date": [
#             "admission_date", "date of admission", "admitted", "check in",
#             "admission", "date / time of admission", "admitted on"
#         ],
#         "discharge_date": [
#             "discharge_date", "date of discharge", "discharged", "check out",
#             "discharge", "discharged on", "released"
#         ],
#         "diagnosis": [
#             "diagnosis", "diagnoses", "condition", "medical condition",
#             "diagnosis code", "icd", "icd-10", "primary diagnosis"
#         ],
#         "total_amount": [
#             "total_amount", "total", "amount", "grand total",
#             "total charges", "total due", "balance", "amount due", "net payable"
#         ],
#         "department": [
#             "department", "dept", "treating department", "ward",
#             "unit", "division", "service department"
#         ],
#         "doctor_name": [
#             "doctor", "physician", "doctor name", "attending physician",
#             "treating doctor", "name of treating doctor", "consultant"
#         ]
#     }
    
#     def extract_insurance_fields(self, json_output: Dict[str, Any]) -> Dict[str, Any]:
#         """
#         Extract standardized insurance fields from OCR JSON output
        
#         Args:
#             json_output: The complete OCR JSON output from any hospital invoice
            
#         Returns:
#             Standardized dictionary with insurance-critical fields
#         """
#         # Initialize result structure
#         insurance_data = {
#             "patient_info": {},
#             "provider_info": {},
#             "financial_info": {},
#             "clinical_info": {},
#             "line_items": [],
#             "raw_confidence": {
#                 "extraction_quality": "unknown",
#                 "missing_critical_fields": []
#             }
#         }
        
#         # Extract from key-value pairs (most common location)
#         fields = json_output.get("fields", {})
#         entities = json_output.get("entities", {})
#         metadata = json_output.get("metadata", {})
#         extracted_text = json_output.get("extracted_text_preview", "")
#         tables = json_output.get("tables", [])
        
#         # 1. Extract metadata from tables FIRST (invoice no, dates, etc.)
#         table_metadata = self._extract_metadata_from_tables(tables, extracted_text)
        
#         # 2. PATIENT INFORMATION
#         insurance_data["patient_info"] = {
#             "full_name": self._find_field(fields, "patient_name", entities),
#             "patient_id": self._find_field(fields, "patient_id"),
#             "date_of_birth": self._find_field(fields, "date_of_birth"),
#             "insurance_policy_number": self._find_field(fields, "insurance_policy")
#         }
        
#         # 3. PROVIDER INFORMATION
#         insurance_data["provider_info"] = {
#             "hospital_name": self._find_field(fields, "hospital_name") or self._extract_hospital_from_text(extracted_text),
#             "provider_npi": self._find_field(fields, "provider_npi"),
#             "department": self._find_field(fields, "department"),
#             "doctor_name": self._find_field(fields, "doctor_name")
#         }
        
#         # 4. FINANCIAL INFORMATION
#         # Use table metadata as fallback if fields don't have values
#         insurance_data["financial_info"] = {
#             "invoice_number": self._find_field(fields, "invoice_number") or table_metadata.get("invoice_number"),
#             "invoice_date": self._find_field(fields, "invoice_date") or table_metadata.get("invoice_date"),
#             "total_amount": self._find_field(fields, "total_amount") or table_metadata.get("total_amount") or self._extract_total_from_text(extracted_text),
#             "currency": self._detect_currency(json_output)
#         }
        
#         # 5. CLINICAL INFORMATION
#         insurance_data["clinical_info"] = {
#             "admission_date": self._find_field(fields, "admission_date"),
#             "discharge_date": self._find_field(fields, "discharge_date"),
#             "diagnosis": self._find_field(fields, "diagnosis"),
#             "diagnosis_codes": self._extract_icd_codes(extracted_text),
#             "procedure_codes": self._extract_cpt_codes(extracted_text)
#         }
        
#         # 6. LINE ITEMS (Services) - filtered to exclude metadata rows
#         insurance_data["line_items"] = self._extract_line_items(json_output)
        
#         # 7. QUALITY ASSESSMENT
#         insurance_data["raw_confidence"] = self._assess_extraction_quality(insurance_data, metadata)
        
#         # Add metadata
#         insurance_data["extraction_timestamp"] = datetime.utcnow().isoformat()
#         insurance_data["document_type"] = json_output.get("document_type", "unknown")
#         insurance_data["language"] = metadata.get("language", "en")
        
#         return insurance_data
    
#     def _extract_metadata_from_tables(self, tables: List[Dict], text: str) -> Dict[str, str]:
#         """
#         Extract invoice metadata from table rows
#         Some invoices put Invoice No, Date, etc. in the first row of the table
#         """
#         metadata = {}
        
#         for table in tables:
#             rows = table.get("rows", [])
#             if not rows:
#                 continue
            
#             # Check first few rows for metadata patterns
#             for row in rows[:3]:  # Only check first 3 rows
#                 row_text = ' '.join([str(cell) for cell in row])
#                 row_text_lower = row_text.lower()
                
#                 # Extract Invoice Number
#                 if 'invoice no' in row_text_lower or 'receipt no' in row_text_lower:
#                     # Pattern: "Invoice No: APKHNH/2025/002347" or "Invoice No APKHNH/2025/002347"
#                     match = re.search(r'(?:invoice|receipt)\s+no[:\s]+([A-Z0-9/-]+)', row_text, re.IGNORECASE)
#                     if match:
#                         metadata['invoice_number'] = match.group(1).strip()
                
#                 # Extract Invoice Date
#                 if 'invoice date' in row_text_lower or 'bill date' in row_text_lower:
#                     # Pattern: "Invoice Date: 13th February 2025" or "13th February 2025"
#                     match = re.search(r'(?:invoice|bill)\s+date[:\s]+(.+?)(?:\s+Payment|$)', row_text, re.IGNORECASE)
#                     if match:
#                         metadata['invoice_date'] = match.group(1).strip()
                
#                 # Extract Total/Net Payable
#                 if 'net payable' in row_text_lower or 'amount due' in row_text_lower:
#                     # Pattern: "Net Payable (KES): 345,635.00"
#                     match = re.search(r'(?:net payable|amount due)[^:]*:\s*([\d,]+\.?\d*)', row_text, re.IGNORECASE)
#                     if match:
#                         amount = match.group(1).strip()
#                         metadata['total_amount'] = f"{amount}"
        
#         return metadata
    
#     def _find_field(self, fields: Dict, field_type: str, entities: Dict = None) -> Optional[str]:
#         """Find field value using multiple possible field names"""
#         possible_names = self.FIELD_MAPPINGS.get(field_type, [])
        
#         # Try exact matches first
#         for name in possible_names:
#             # Check in fields (key-value pairs)
#             if name in fields:
#                 return self._clean_value(fields[name])
            
#             # Check with underscores replaced by spaces
#             name_with_spaces = name.replace("_", " ")
#             if name_with_spaces in fields:
#                 return self._clean_value(fields[name_with_spaces])
        
#         # Try partial matches (case-insensitive)
#         for key, value in fields.items():
#             key_lower = key.lower()
#             for name in possible_names:
#                 if name.lower() in key_lower or key_lower in name.lower():
#                     return self._clean_value(value)
        
#         # Special handling for patient name - check entities
#         if field_type == "patient_name" and entities:
#             persons = entities.get("persons", [])
#             if persons and len(persons) > 0:
#                 # Usually the first person mentioned is the patient
#                 return self._clean_value(persons[0])
        
#         return None
    
#     def _clean_value(self, value: Any) -> str:
#         """Clean and normalize extracted values"""
#         if value is None:
#             return None
        
#         # Convert to string
#         value_str = str(value).strip()
        
#         # Remove common OCR artifacts
#         value_str = re.sub(r'[_]{2,}', '', value_str)  # Remove multiple underscores
#         value_str = re.sub(r'\s+', ' ', value_str)     # Normalize whitespace
        
#         return value_str if value_str else None
    
#     def _extract_hospital_from_text(self, text: str) -> Optional[str]:
#         """Extract hospital name from text (usually at the top)"""
#         # Hospital names are usually in the first 200 characters
#         first_lines = text[:200]
        
#         # Look for common hospital keywords
#         hospital_patterns = [
#             r'([A-Z][a-zA-Z\s&]+(?:Hospital|Medical Center|Clinic|Healthcare))',
#             r'([A-Z][a-zA-Z\s&]+(?:University|Regional|General|District)\s+Hospital)',
#         ]
        
#         for pattern in hospital_patterns:
#             match = re.search(pattern, first_lines)
#             if match:
#                 return match.group(1).strip()
        
#         return None
    
#     def _extract_total_from_text(self, text: str) -> Optional[str]:
#         """Extract total amount from text"""
#         # Look for patterns like "Total: $1,234.56" or "Grand Total: 1234.56" or "Net Payable: 345,635.00"
#         patterns = [
#             r'(?:net payable|total|grand\s+total|amount\s+due|balance)[\s:()A-Z]*[\s:]*([£$€¥₹]?\s*[\d,]+\.?\d*)',
#             r'(?:gesamtbetrag)[\s:]*([£$€¥₹]?\s*[\d,]+\.?\d*)',  # German
#         ]
        
#         for pattern in patterns:
#             match = re.search(pattern, text.lower())
#             if match:
#                 return match.group(1).strip()
        
#         return None
    
#     def _detect_currency(self, json_output: Dict) -> str:
#         """Detect currency from the document"""
#         text = json_output.get("extracted_text_preview", "")
        
#         currency_symbols = {
#             '$': 'USD',
#             '€': 'EUR',
#             '£': 'GBP',
#             '¥': 'JPY',
#             '₹': 'INR',
#             'KES': 'KES',
#             'Ksh': 'KES'
#         }
        
#         for symbol, code in currency_symbols.items():
#             if symbol in text or code in text:
#                 return code
        
#         return 'KES'  # Default
    
#     def _extract_icd_codes(self, text: str) -> List[str]:
#         """Extract ICD-10 diagnosis codes"""
#         # ICD-10 format: Letter followed by 2 digits, optional decimal and more digits
#         # Example: A01.1, Z23, E11.9
#         pattern = r'\b[A-Z]\d{2}(?:\.\d{1,2})?\b'
#         matches = re.findall(pattern, text)
#         return list(set(matches))  # Remove duplicates
    
#     def _extract_cpt_codes(self, text: str) -> List[str]:
#         """Extract CPT procedure codes"""
#         # CPT format: 5 digits
#         # Example: 99213, 36415
#         pattern = r'\b\d{5}\b'
#         matches = re.findall(pattern, text)
#         # Filter out obvious non-CPT numbers (like years, amounts)
#         cpt_codes = [m for m in matches if not m.startswith(('19', '20'))]
#         return list(set(cpt_codes))
    
#     def _extract_line_items(self, json_output: Dict) -> List[Dict]:
#         """Extract service line items from tables, filtering out metadata rows"""
#         tables = json_output.get("tables", [])
#         line_items = []
        
#         for table in tables:
#             headers = table.get("headers", [])
#             rows = table.get("rows", [])
            
#             # Skip if no data
#             if not rows:
#                 continue
            
#             # Identify column indices
#             description_idx = self._find_column_index(headers, ["description", "service", "billing details", "item", "particulars"])
#             quantity_idx = self._find_column_index(headers, ["quantity", "qty", "units"])
#             rate_idx = self._find_column_index(headers, ["rate", "unit price", "price", "amount"])
#             total_idx = self._find_column_index(headers, ["total", "amount", "charges"])
            
#             for row in rows:
#                 if len(row) < 2:  # Skip invalid rows
#                     continue
                
#                 # Get row text for filtering
#                 row_text = ' '.join([str(cell) for cell in row])
#                 row_text_lower = row_text.lower()
                
#                 # Skip summary rows (total, subtotal, grand total, etc.)
#                 if any(keyword in row_text_lower for keyword in [
#                     'total', 'subtotal', 'grand total', 'balance', 
#                     'amount due', 'net payable', 'sub-total'
#                 ]):
#                     continue
                
#                 # Skip metadata rows (invoice no, receipt no, payment due, etc.)
#                 # These are common in the first row of some hospital invoices
#                 if any(keyword in row_text_lower for keyword in [
#                     'invoice no:', 'invoice date:', 'receipt no:', 
#                     'payment due:', 'bill no:', 'claim number:',
#                     'account no:', 'patient no:', 'not yet paid'
#                 ]):
#                     continue
                
#                 # Skip category header rows (sections like "ACCOMMODATION & NURSING")
#                 # These usually appear as all-caps headings without prices
#                 if row_text.isupper() and not any(char.isdigit() for char in row_text):
#                     continue
                
#                 # Skip rows that start with letters like "A.", "B.", "C." (section markers)
#                 if re.match(r'^[A-Z]\.\s+[A-Z\s&]+$', row_text.strip()):
#                     continue
                
#                 # Get description
#                 description = row[description_idx] if description_idx is not None and description_idx < len(row) else row[0]
#                 description = str(description).strip()
                
#                 # Skip if description is empty or too short
#                 if not description or len(description) < 3:
#                     continue
                
#                 # Skip if description is just a section marker
#                 if description in ['A', 'B', 'C', 'D', 'E', 'F']:
#                     continue
                
#                 line_item = {
#                     "description": description,
#                     "quantity": str(row[quantity_idx]).strip() if quantity_idx is not None and quantity_idx < len(row) else None,
#                     "unit_price": str(row[rate_idx]).strip() if rate_idx is not None and rate_idx < len(row) else None,
#                     "total": str(row[total_idx]).strip() if total_idx is not None and total_idx < len(row) else None
#                 }
                
#                 # Only add if we have at least a description and some financial data
#                 if line_item["description"] and (line_item["unit_price"] or line_item["total"]):
#                     line_items.append(line_item)
        
#         return line_items
    
#     def _find_column_index(self, headers: List[str], possible_names: List[str]) -> Optional[int]:
#         """Find column index by matching header names"""
#         headers_lower = [str(h).lower() for h in headers]
        
#         for idx, header in enumerate(headers_lower):
#             for name in possible_names:
#                 if name.lower() in header or header in name.lower():
#                     return idx
        
#         return None
    
#     def _assess_extraction_quality(self, insurance_data: Dict, metadata: Dict) -> Dict:
#         """Assess quality of extracted insurance data"""
#         critical_fields = [
#             ("patient_info", "full_name"),
#             ("patient_info", "insurance_policy_number"),
#             ("provider_info", "hospital_name"),
#             ("financial_info", "invoice_number"),
#             ("financial_info", "total_amount"),
#             ("clinical_info", "diagnosis")
#         ]
        
#         missing_fields = []
#         present_count = 0
        
#         for section, field in critical_fields:
#             value = insurance_data.get(section, {}).get(field)
#             if value and str(value).strip() and str(value).lower() not in ['none', 'null', 'n/a']:
#                 present_count += 1
#             else:
#                 missing_fields.append(f"{section}.{field}")
        
#         total_fields = len(critical_fields)
#         completeness = (present_count / total_fields) * 100
        
#         # Determine quality rating
#         if completeness >= 90:
#             quality = "excellent"
#         elif completeness >= 70:
#             quality = "good"
#         elif completeness >= 50:
#             quality = "fair"
#         else:
#             quality = "poor"
        
#         return {
#             "extraction_quality": quality,
#             "completeness_percentage": round(completeness, 1),
#             "critical_fields_found": present_count,
#             "critical_fields_total": total_fields,
#             "missing_critical_fields": missing_fields,
#             "ocr_confidence": metadata.get("ocr_confidence", 0),
#             "has_line_items": len(insurance_data.get("line_items", [])) > 0
#         }

# # Global instance
# insurance_fields_extractor = InsuranceFieldsExtractor()

# /backend/app/services/insurance_fields_extractor.py

from typing import Dict, Any, Optional, List
import re
from datetime import datetime

class InsuranceFieldsExtractor:
    """
    Extract standardized insurance-critical fields from hospital invoice OCR output.
    Works with any hospital invoice format.
    """
    
    # Common field name variations across different hospitals
    FIELD_MAPPINGS = {
        "patient_name": [
            "patient_name", "patient", "name of patient", "patient's name",
            "name", "full name", "beneficiary", "insured name"
        ],
        "patient_id": [
            "patient_id", "patient id", "medical record number", "mrn",
            "patient number", "record number", "patient no", "id number"
        ],
        "date_of_birth": [
            "date_of_birth", "dob", "birth date", "date of birth",
            "birthdate", "patient dob", "age/sex"
        ],
        "insurance_policy": [
            "insurance_policy", "policy number", "policy no", "insurance number",
            "policy id", "member id", "insurance id", "plan number"
        ],
        "hospital_name": [
            "hospital_name", "hospital", "facility", "facility name",
            "provider", "institution", "medical center"
        ],
        "provider_npi": [
            "npi", "provider_npi", "tax id", "provider id", "tin",
            "federal tax id", "npi number", "provider number"
        ],
        "invoice_number": [
            "invoice_number", "bill_no", "bill number", "invoice no",
            "billing number", "claim number", "receipt number", "receipt no"
        ],
        "invoice_date": [
            "invoice_date", "bill date", "billing date", "date",
            "statement date", "invoice date"
        ],
        "admission_date": [
            "admission_date", "date of admission", "admitted", "check in",
            "admission", "date / time of admission", "admitted on"
        ],
        "discharge_date": [
            "discharge_date", "date of discharge", "discharged", "check out",
            "discharge", "discharged on", "released"
        ],
        "diagnosis": [
            "diagnosis", "diagnoses", "condition", "medical condition",
            "diagnosis code", "icd", "icd-10", "primary diagnosis"
        ],
        "total_amount": [
            "total_amount", "total", "amount", "grand total",
            "total charges", "total due", "balance", "amount due", "net payable"
        ],
        "department": [
            "department", "dept", "treating department", "ward",
            "unit", "division", "service department"
        ],
        "doctor_name": [
            "doctor", "physician", "doctor name", "attending physician",
            "treating doctor", "name of treating doctor", "consultant"
        ]
    }
    
    def extract_insurance_fields(self, json_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standardized insurance fields from OCR JSON output
        
        Args:
            json_output: The complete OCR JSON output from any hospital invoice
            
        Returns:
            Standardized dictionary with insurance-critical fields
        """
        # Initialize result structure
        insurance_data = {
            "patient_info": {},
            "provider_info": {},
            "financial_info": {},
            "clinical_info": {},
            "line_items": [],
            "raw_confidence": {
                "extraction_quality": "unknown",
                "missing_critical_fields": []
            }
        }
        
        # Extract from key-value pairs (most common location)
        fields = json_output.get("fields", {})
        entities = json_output.get("entities", {})
        metadata = json_output.get("metadata", {})
        extracted_text = json_output.get("extracted_text_preview", "")
        tables = json_output.get("tables", [])
        
        # 1. Extract metadata from tables FIRST (invoice no, dates, etc.)
        table_metadata = self._extract_metadata_from_tables(tables, extracted_text)
        
        # 2. PATIENT INFORMATION
        insurance_data["patient_info"] = {
            "full_name": self._find_field(fields, "patient_name", entities),
            "patient_id": self._find_field(fields, "patient_id")
        }
        
        # 3. PROVIDER INFORMATION
        insurance_data["provider_info"] = {
            "hospital_name": self._find_field(fields, "hospital_name") or self._extract_hospital_from_text(extracted_text),
            "provider_npi": self._find_field(fields, "provider_npi"),
            "department": self._find_field(fields, "department"),
            "doctor_name": self._find_field(fields, "doctor_name")
        }
        
        # 4. FINANCIAL INFORMATION
        # Use table metadata as fallback if fields don't have values
        insurance_data["financial_info"] = {
            "invoice_number": self._find_field(fields, "invoice_number") or table_metadata.get("invoice_number"),
            "invoice_date": self._find_field(fields, "invoice_date") or table_metadata.get("invoice_date"),
            "total_amount": self._find_field(fields, "total_amount") or table_metadata.get("total_amount") or self._extract_total_from_text(extracted_text),
            "amount_due": table_metadata.get("amount_due") or self._extract_amount_due(extracted_text),
            "currency": self._detect_currency(json_output)
        }
        
        # 5. CLINICAL INFORMATION
        insurance_data["clinical_info"] = {
            "admission_date": self._find_field(fields, "admission_date") or table_metadata.get("admission_date"),
            "discharge_date": self._find_field(fields, "discharge_date") or table_metadata.get("discharge_date"),
            "diagnosis": self._find_field(fields, "diagnosis"),
            "diagnosis_codes": self._extract_icd_codes(extracted_text),
            "procedure_codes": self._extract_cpt_codes(extracted_text)
        }
        
        # 6. LINE ITEMS (Services) - filtered to exclude metadata rows
        insurance_data["line_items"] = self._extract_line_items(json_output)
        
        # 7. QUALITY ASSESSMENT
        insurance_data["raw_confidence"] = self._assess_extraction_quality(insurance_data, metadata)
        
        # Add metadata
        insurance_data["extraction_timestamp"] = datetime.utcnow().isoformat()
        insurance_data["document_type"] = json_output.get("document_type", "unknown")
        insurance_data["language"] = metadata.get("language", "en")
        
        return insurance_data
    
    def _extract_metadata_from_tables(self, tables: List[Dict], text: str) -> Dict[str, str]:
        """
        Extract invoice metadata from table rows
        Some invoices put Invoice No, Date, etc. in the first row of the table
        """
        metadata = {}
        
        for table in tables:
            rows = table.get("rows", [])
            headers = table.get("headers", [])
            
            if not rows:
                continue
            
            # Check all rows for metadata patterns (not just first 3)
            for row in rows:
                row_text = ' '.join([str(cell) for cell in row])
                row_text_lower = row_text.lower()
                
                # Extract Invoice Number
                if 'invoice no' in row_text_lower or 'receipt no' in row_text_lower:
                    match = re.search(r'(?:invoice|receipt)\s+no[:\s]+([A-Z0-9/-]+)', row_text, re.IGNORECASE)
                    if match:
                        metadata['invoice_number'] = match.group(1).strip()
                
                # Extract Invoice Date
                if 'invoice date' in row_text_lower or 'bill date' in row_text_lower:
                    match = re.search(r'(?:invoice|bill)\s+date[:\s]+(.+?)(?:\s+Payment|\s+Receipt|$)', row_text, re.IGNORECASE)
                    if match:
                        metadata['invoice_date'] = match.group(1).strip()
                
                # Extract Admission Date
                if 'admission date' in row_text_lower:
                    match = re.search(r'admission\s+date[:\s]+(.+?)(?:\s+Discharge|\s+\n|$)', row_text, re.IGNORECASE)
                    if match:
                        metadata['admission_date'] = match.group(1).strip()
                
                # Extract Discharge Date
                if 'discharge date' in row_text_lower:
                    match = re.search(r'discharge\s+date[:\s]+(.+?)(?:\s+Attending|\s+\n|$)', row_text, re.IGNORECASE)
                    if match:
                        metadata['discharge_date'] = match.group(1).strip()
                
                # Extract Subtotal
                if 'subtotal' in row_text_lower and 'ksh' in row_text_lower:
                    match = re.search(r'(?:subtotal)[^:]*:\s*(?:KSh\s*)?([\d,]+\.?\d*)', row_text, re.IGNORECASE)
                    if match:
                        amount = match.group(1).strip()
                        if not metadata.get('total_amount'):  # Don't overwrite if already set
                            metadata['total_amount'] = amount
                
                # Extract Balance Due / Amount Due
                if 'balance due' in row_text_lower or 'balance payable' in row_text_lower:
                    match = re.search(r'(?:balance\s+due|balance\s+payable)[^:]*:\s*(?:KSh\s*)?([\d,]+\.?\d*)', row_text, re.IGNORECASE)
                    if match:
                        amount = match.group(1).strip()
                        metadata['amount_due'] = amount
                
                # Extract Net Payable (could be total or amount due depending on context)
                if 'net payable' in row_text_lower:
                    match = re.search(r'(?:net payable)[^:]*:\s*(?:KSh\s*)?([\d,]+\.?\d*)', row_text, re.IGNORECASE)
                    if match:
                        amount = match.group(1).strip()
                        # If we don't have amount_due, this might be it
                        if not metadata.get('amount_due'):
                            metadata['amount_due'] = amount
                        if not metadata.get('total_amount'):
                            metadata['total_amount'] = amount
        
        return metadata
    
    def _find_field(self, fields: Dict, field_type: str, entities: Dict = None) -> Optional[str]:
        """Find field value using multiple possible field names"""
        possible_names = self.FIELD_MAPPINGS.get(field_type, [])
        
        # Try exact matches first
        for name in possible_names:
            # Check in fields (key-value pairs)
            if name in fields:
                return self._clean_value(fields[name])
            
            # Check with underscores replaced by spaces
            name_with_spaces = name.replace("_", " ")
            if name_with_spaces in fields:
                return self._clean_value(fields[name_with_spaces])
        
        # Try partial matches (case-insensitive)
        for key, value in fields.items():
            key_lower = key.lower()
            for name in possible_names:
                if name.lower() in key_lower or key_lower in name.lower():
                    return self._clean_value(value)
        
        # Special handling for patient name - check entities
        if field_type == "patient_name" and entities:
            persons = entities.get("persons", [])
            if persons and len(persons) > 0:
                # Usually the first person mentioned is the patient
                return self._clean_value(persons[0])
        
        return None
    
    def _clean_value(self, value: Any) -> str:
        """Clean and normalize extracted values"""
        if value is None:
            return None
        
        # Convert to string
        value_str = str(value).strip()
        
        # Remove common OCR artifacts
        value_str = re.sub(r'[_]{2,}', '', value_str)  # Remove multiple underscores
        value_str = re.sub(r'\s+', ' ', value_str)     # Normalize whitespace
        
        return value_str if value_str else None
    
    def _extract_hospital_from_text(self, text: str) -> Optional[str]:
        """Extract hospital name from text (usually at the top)"""
        # Hospital names are usually in the first 200 characters
        first_lines = text[:200]
        
        # Look for common hospital keywords
        hospital_patterns = [
            r'([A-Z][a-zA-Z\s&]+(?:Hospital|Medical Center|Clinic|Healthcare))',
            r'([A-Z][a-zA-Z\s&]+(?:University|Regional|General|District)\s+Hospital)',
        ]
        
        for pattern in hospital_patterns:
            match = re.search(pattern, first_lines)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_total_from_text(self, text: str) -> Optional[str]:
        """Extract total amount from text"""
        # Look for patterns like "Total: $1,234.56" or "Grand Total: 1234.56" or "Net Payable: 345,635.00"
        patterns = [
            r'(?:subtotal|net payable|total|grand\s+total)[\s:()A-Z]*[\s:]*(?:KSh\s*)?([£$€¥₹]?\s*[\d,]+\.?\d*)',
            r'(?:gesamtbetrag)[\s:]*([£$€¥₹]?\s*[\d,]+\.?\d*)',  # German
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_amount_due(self, text: str) -> Optional[str]:
        """Extract amount due / balance due from text"""
        patterns = [
            r'(?:balance\s+due|amount\s+due|balance\s+payable)[\s:()A-Z]*[\s:]*(?:KSh\s*)?([£$€¥₹]?\s*[\d,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).strip()
        
        return None
    
    def _detect_currency(self, json_output: Dict) -> str:
        """Detect currency from the document"""
        text = json_output.get("extracted_text_preview", "")
        
        currency_symbols = {
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP',
            '¥': 'JPY',
            '₹': 'INR',
            'KES': 'KES',
            'Ksh': 'KES'
        }
        
        for symbol, code in currency_symbols.items():
            if symbol in text or code in text:
                return code
        
        return 'KES'  # Default
    
    def _extract_icd_codes(self, text: str) -> List[str]:
        """Extract ICD-10 diagnosis codes"""
        # ICD-10 format: Letter followed by 2 digits, optional decimal and more digits
        # Example: A01.1, Z23, E11.9
        pattern = r'\b[A-Z]\d{2}(?:\.\d{1,2})?\b'
        matches = re.findall(pattern, text)
        return list(set(matches))  # Remove duplicates
    
    def _extract_cpt_codes(self, text: str) -> List[str]:
        """Extract CPT procedure codes"""
        # CPT format: 5 digits
        # Example: 99213, 36415
        pattern = r'\b\d{5}\b'
        matches = re.findall(pattern, text)
        # Filter out obvious non-CPT numbers (like years, amounts)
        cpt_codes = [m for m in matches if not m.startswith(('19', '20'))]
        return list(set(cpt_codes))
    
    def _extract_line_items(self, json_output: Dict) -> List[Dict]:
        """Extract service line items from tables, filtering out metadata rows"""
        tables = json_output.get("tables", [])
        line_items = []
        
        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            # Skip if no data
            if not rows:
                continue
            
            # Identify column indices
            description_idx = self._find_column_index(headers, ["description", "service", "billing details", "item", "particulars"])
            quantity_idx = self._find_column_index(headers, ["quantity", "qty", "units"])
            rate_idx = self._find_column_index(headers, ["rate", "unit price", "price", "amount"])
            total_idx = self._find_column_index(headers, ["total", "amount", "charges"])
            
            for row in rows:
                if len(row) < 2:  # Skip invalid rows
                    continue
                
                # Get row text for filtering
                row_text = ' '.join([str(cell) for cell in row])
                row_text_lower = row_text.lower()
                
                # Skip summary rows (total, subtotal, grand total, etc.)
                if any(keyword in row_text_lower for keyword in [
                    'total', 'subtotal', 'grand total', 'balance', 
                    'amount due', 'net payable', 'sub-total'
                ]):
                    continue
                
                # Skip metadata rows (invoice no, receipt no, payment due, etc.)
                # These are common in the first row of some hospital invoices
                if any(keyword in row_text_lower for keyword in [
                    'invoice no:', 'invoice date:', 'receipt no:', 
                    'payment due:', 'bill no:', 'claim number:',
                    'account no:', 'patient no:', 'not yet paid'
                ]):
                    continue
                
                # Skip category header rows (sections like "ACCOMMODATION & NURSING")
                # These usually appear as all-caps headings without prices
                if row_text.isupper() and not any(char.isdigit() for char in row_text):
                    continue
                
                # Skip rows that start with letters like "A.", "B.", "C." (section markers)
                if re.match(r'^[A-Z]\.\s+[A-Z\s&]+$', row_text.strip()):
                    continue
                
                # Get description
                description = row[description_idx] if description_idx is not None and description_idx < len(row) else row[0]
                description = str(description).strip()
                
                # Skip if description is empty or too short
                if not description or len(description) < 3:
                    continue
                
                # Skip if description is just a section marker
                if description in ['A', 'B', 'C', 'D', 'E', 'F']:
                    continue
                
                line_item = {
                    "description": description,
                    "quantity": str(row[quantity_idx]).strip() if quantity_idx is not None and quantity_idx < len(row) else None,
                    "unit_price": str(row[rate_idx]).strip() if rate_idx is not None and rate_idx < len(row) else None,
                    "total": str(row[total_idx]).strip() if total_idx is not None and total_idx < len(row) else None
                }
                
                # Only add if we have at least a description and some financial data
                if line_item["description"] and (line_item["unit_price"] or line_item["total"]):
                    line_items.append(line_item)
        
        return line_items
    
    def _find_column_index(self, headers: List[str], possible_names: List[str]) -> Optional[int]:
        """Find column index by matching header names"""
        headers_lower = [str(h).lower() for h in headers]
        
        for idx, header in enumerate(headers_lower):
            for name in possible_names:
                if name.lower() in header or header in name.lower():
                    return idx
        
        return None
    
    def _assess_extraction_quality(self, insurance_data: Dict, metadata: Dict) -> Dict:
        """Assess quality of extracted insurance data"""
        critical_fields = [
            ("patient_info", "full_name"),
            ("provider_info", "hospital_name"),
            ("financial_info", "invoice_number"),
            ("financial_info", "total_amount"),
            ("clinical_info", "diagnosis")
        ]
        
        missing_fields = []
        present_count = 0
        
        for section, field in critical_fields:
            value = insurance_data.get(section, {}).get(field)
            if value and str(value).strip() and str(value).lower() not in ['none', 'null', 'n/a']:
                present_count += 1
            else:
                missing_fields.append(f"{section}.{field}")
        
        total_fields = len(critical_fields)
        completeness = (present_count / total_fields) * 100
        
        # Determine quality rating
        if completeness >= 90:
            quality = "excellent"
        elif completeness >= 70:
            quality = "good"
        elif completeness >= 50:
            quality = "fair"
        else:
            quality = "poor"
        
        return {
            "extraction_quality": quality,
            "completeness_percentage": round(completeness, 1),
            "critical_fields_found": present_count,
            "critical_fields_total": total_fields,
            "missing_critical_fields": missing_fields,
            "ocr_confidence": metadata.get("ocr_confidence", 0),
            "has_line_items": len(insurance_data.get("line_items", [])) > 0
        }

# Global instance
insurance_fields_extractor = InsuranceFieldsExtractor()