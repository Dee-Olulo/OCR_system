# /backend/app/services/table_extraction_service.py

"""
Table extraction service for images and scanned documents
Extracts invoice line items, spreadsheet data, etc.
"""

import re
from typing import List, Dict, Tuple
import cv2
import numpy as np

class TableExtractionService:
    """Extract tables from text and images"""
    
    def extract_tables_from_text(self, text: str) -> List[Dict]:
        """
        Extract tables from plain text using pattern recognition
        Perfect for OCR output
        """
        tables = []
        
        # Strategy 1: Detect invoice line items pattern
        invoice_table = self._extract_invoice_line_items(text)
        if invoice_table:
            tables.append(invoice_table)
        
        # Strategy 2: Detect tabular data with multiple spaces/tabs
        text_tables = self._extract_aligned_tables(text)
        tables.extend(text_tables)
        
        return tables
    
    def _extract_invoice_line_items(self, text: str) -> Dict:
        """
        Extract invoice line items (Pos., Description, Quantity, Price, Total)
        Works for German and English invoices
        """
        lines = text.split('\n')
        
        # Find header row
        header_patterns = [
            # German patterns
            r'pos\.?\s+beschreibung.*menge.*preis.*betrag',
            r'position.*beschreibung.*anzahl.*einzelpreis.*gesamtpreis',
            # English patterns
            r'item.*description.*qty.*price.*amount',
            r'pos.*desc.*quantity.*unit.*total',
        ]
        
        header_idx = None
        header_line = None
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for pattern in header_patterns:
                if re.search(pattern, line_lower):
                    header_idx = i
                    header_line = line
                    break
            if header_idx is not None:
                break
        
        if header_idx is None:
            return None
        
        # Extract header columns
        headers = self._parse_header_columns(header_line)
        
        if not headers:
            return None
        
        # Extract data rows
        rows = []
        for i in range(header_idx + 1, len(lines)):
            line = lines[i].strip()
            
            # Stop at totals/summary section
            if self._is_summary_line(line):
                break
            
            # Parse line item
            row_data = self._parse_line_item(line)
            
            if row_data and len(row_data) >= 3:  # At least pos, description, amount
                rows.append(row_data)
        
        if not rows:
            return None
        
        print(f"✓ Extracted invoice table: {len(rows)} line items")
        
        return {
            "table_type": "invoice_line_items",
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "column_count": len(headers)
        }
    
    def _parse_header_columns(self, header_line: str) -> List[str]:
        """Parse header columns from header line"""
        # Common header patterns
        header_mapping = {
            'pos': 'Position',
            'position': 'Position',
            'item': 'Position',
            'beschreibung': 'Description',
            'description': 'Description',
            'desc': 'Description',
            'menge': 'Quantity',
            'quantity': 'Quantity',
            'qty': 'Quantity',
            'anzahl': 'Quantity',
            'einzelpreis': 'Unit Price',
            'unit price': 'Unit Price',
            'price': 'Unit Price',
            'preis': 'Unit Price',
            'gesamtpreis': 'Total',
            'total': 'Total',
            'amount': 'Total',
            'betrag': 'Total',
        }
        
        # Split by whitespace and detect columns
        parts = re.split(r'\s{2,}', header_line.strip())
        
        headers = []
        for part in parts:
            part_lower = part.lower().strip('.:')
            mapped = header_mapping.get(part_lower, part)
            if mapped:
                headers.append(mapped)
        
        # Fallback: create generic headers
        if len(headers) < 3:
            headers = ['Position', 'Description', 'Quantity', 'Unit Price', 'Total']
        
        return headers
    
    def _parse_line_item(self, line: str) -> List[str]:
        """
        Parse invoice line item
        Example: "1 Webdesign Leistungen 8 Std. | 70,00 € 560,00 €"
        """
        if not line or len(line.strip()) < 3:
            return None
        
        # Check if line starts with a number (position)
        if not re.match(r'^\s*\d+', line):
            return None
        
        # Split by pipe or multiple spaces
        if '|' in line:
            parts = [p.strip() for p in re.split(r'\|', line)]
        else:
            parts = [p.strip() for p in re.split(r'\s{2,}', line)]
        
        # Clean up parts
        cleaned_parts = []
        for part in parts:
            part = part.strip()
            if part:
                cleaned_parts.append(part)
        
        return cleaned_parts if len(cleaned_parts) >= 2 else None
    
    def _is_summary_line(self, line: str) -> bool:
        """Check if line is a summary/total line"""
        summary_keywords = [
            'zwischensumme', 'subtotal', 'sub-total',
            'gesamtbetrag', 'total amount', 'grand total',
            'mwst', 'vat', 'tax', 'steuer',
            'zahlungsbedingungen', 'payment terms',
            'bankverbindung', 'bank details',
        ]
        
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in summary_keywords)
    
    def _extract_aligned_tables(self, text: str) -> List[Dict]:
        """
        Extract tables that use spaces/tabs for alignment
        """
        tables = []
        lines = text.split('\n')
        
        current_table = []
        in_table = False
        
        for line in lines:
            # Check if line looks like table data (multiple aligned columns)
            if self._is_table_row(line):
                in_table = True
                current_table.append(line)
            else:
                # End of table
                if in_table and len(current_table) > 2:
                    table_dict = self._convert_aligned_table(current_table)
                    if table_dict:
                        tables.append(table_dict)
                
                current_table = []
                in_table = False
        
        # Check last table
        if len(current_table) > 2:
            table_dict = self._convert_aligned_table(current_table)
            if table_dict:
                tables.append(table_dict)
        
        return tables
    
    def _is_table_row(self, line: str) -> bool:
        """Check if line looks like a table row"""
        # Has multiple sections separated by 2+ spaces
        parts = re.split(r'\s{2,}', line.strip())
        return len(parts) >= 3
    
    def _convert_aligned_table(self, lines: List[str]) -> Dict:
        """Convert aligned text lines to table structure"""
        if len(lines) < 2:
            return None
        
        # Use first line as headers
        headers = [h.strip() for h in re.split(r'\s{2,}', lines[0].strip())]
        
        # Extract rows
        rows = []
        for line in lines[1:]:
            row_data = [d.strip() for d in re.split(r'\s{2,}', line.strip())]
            if len(row_data) >= len(headers) - 1:  # Allow some flexibility
                rows.append(row_data)
        
        if not rows:
            return None
        
        return {
            "table_type": "aligned_text_table",
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "column_count": len(headers)
        }

table_extraction_service = TableExtractionService()