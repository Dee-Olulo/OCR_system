# /backend/app/services/json_output_service.py

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re

class JSONOutputService:
    """Service for generating dynamic structured JSON output from OCR results"""
    
    def generate_dynamic_json(self,
         entities: Dict,
        tables: List,
        document_type: str,
        extracted_text: str
    ) -> Dict[str, Any]:
        """
        Generate dynamic JSON structure based on actual extracted data
        
        This creates a flexible JSON structure that adapts to the document content
        rather than forcing data into a predefined template
        """
        
        # Base structure with metadata
        output = {
            "document_type": document_type,
            "extraction_timestamp": datetime.utcnow().isoformat(),
            # "metadata": {
            #     "text_length": len(extracted_text) if extracted_text else 0,
            #     "has_tables": len(tables) > 0 if tables else False,
            #     "table_count": len(tables) if tables else 0,
            #     "entity_types_found": list(entities.keys()) if entities else []
            # }
        }
         # Add key-value pairs if available
        kv_pairs = entities.get("key_value_pairs", {})
        if kv_pairs:
            output["fields"] = kv_pairs

        # Add all entities in a structured way
        entities_output = {}
        
        if entities.get("persons"):
            entities_output["persons"] = entities["persons"]
        
        if entities.get("organizations"):
            entities_output["organizations"] = entities["organizations"]
        
        if entities.get("locations"):
            entities_output["locations"] = entities["locations"]
        
        if entities.get("dates"):
            entities_output["dates"] = entities["dates"]
        
        if entities.get("money"):
            entities_output["monetary_values"] = entities["money"]
        
        if entities.get("emails"):
            entities_output["emails"] = entities["emails"]
        
        if entities.get("phone_numbers"):
            entities_output["phone_numbers"] = entities["phone_numbers"]
        
        if entities.get("invoice_numbers"):
            entities_output["invoice_numbers"] = entities["invoice_numbers"]
        
        if entities_output:
            output["entities"] = entities_output
        
        # Add tables if available
        if tables:
            output["tables"] = tables
        
        # Add text preview
        if extracted_text:
            preview_length = min(1000, len(extracted_text))
            output["extracted_text_preview"] = extracted_text[:preview_length]
            if len(extracted_text) > preview_length:
                output["extracted_text_preview"] += "... (truncated)"
        
        # Add metadata
        output["metadata"] = {
            "has_entities": len(entities_output) > 0,
            "has_tables": len(tables) > 0,
            "has_key_value_pairs": len(kv_pairs) > 0,
            "total_entities": sum(len(v) if isinstance(v, list) else 0 for v in entities_output.values()),
            "table_count": len(tables),
            "text_length": len(extracted_text) if extracted_text else 0
        }
        
        return output
    
    def _extract_invoice_data(
        self,
        entities: Dict[str, Any],
        text: str,
        tables: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract invoice-specific fields dynamically"""
        
        invoice_data = {}
        
        # Extract invoice number (common patterns)
        invoice_patterns = [
            r'invoice\s*(?:no|number|#)?[\s:]*([A-Z0-9\-]+)',
            r'invoice[\s:]+([0-9]+)',
            r'#\s*([0-9]+)'
        ]
        
        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_data["invoice_number"] = match.group(1)
                break
        
        # Extract dates if available
        if entities.get("dates"):
            dates_list = entities["dates"]
            if isinstance(dates_list, list) and dates_list:
                invoice_data["dates_found"] = dates_list
                # Try to identify specific date types
                if len(dates_list) > 0:
                    invoice_data["primary_date"] = dates_list[0]
                if len(dates_list) > 1:
                    invoice_data["secondary_date"] = dates_list[1]
        
        # Extract monetary amounts
        if entities.get("money"):
            amounts = entities["money"]
            if isinstance(amounts, list) and amounts:
                invoice_data["amounts"] = amounts
                # Last amount is often the total
                invoice_data["potential_total"] = amounts[-1]
                # Largest amount might be the total
                try:
                    numeric_amounts = [float(re.sub(r'[^\d.]', '', str(amt))) for amt in amounts if amt]
                    if numeric_amounts:
                        invoice_data["largest_amount"] = max(numeric_amounts)
                except:
                    pass
        
        # Extract organizations (vendor/customer)
        if entities.get("organizations"):
            orgs = entities["organizations"]
            if isinstance(orgs, list) and orgs:
                invoice_data["organizations"] = orgs
                if len(orgs) > 0:
                    invoice_data["primary_organization"] = orgs[0]
        
        # Extract contact information
        if entities.get("emails"):
            invoice_data["emails"] = entities["emails"]
        if entities.get("phone_numbers"):
            invoice_data["phone_numbers"] = entities["phone_numbers"]
        
        # Extract line items from tables
        if tables:
            invoice_data["line_items"] = self._extract_line_items_from_tables(tables)
        
        # Extract key-value pairs if available
        if entities.get("key_value_pairs"):
            invoice_data["extracted_fields"] = entities["key_value_pairs"]
        
        return invoice_data
    
    def _extract_receipt_data(self, entities: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Extract receipt-specific fields"""
        
        receipt_data = {}
        
        # Store name (often at top of receipt)
        lines = text.split('\n')
        if lines:
            receipt_data["first_line"] = lines[0].strip()
        
        # Extract amounts
        if entities.get("money"):
            amounts = entities["money"]
            if isinstance(amounts, list):
                receipt_data["amounts"] = amounts
                if amounts:
                    receipt_data["potential_total"] = amounts[-1]
        
        # Extract dates
        if entities.get("dates"):
            dates = entities["dates"]
            if isinstance(dates, list) and dates:
                receipt_data["transaction_date"] = dates[0]
                receipt_data["all_dates"] = dates
        
        # Extract organizations
        if entities.get("organizations"):
            orgs = entities["organizations"]
            if isinstance(orgs, list) and orgs:
                receipt_data["merchant"] = orgs[0]
        
        return receipt_data
    
    def _extract_form_fields(self, entities: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Extract form fields dynamically"""
        
        form_data = {"fields": []}
        
        # Use key-value pairs if available
        if entities.get("key_value_pairs"):
            kv_pairs = entities["key_value_pairs"]
            if isinstance(kv_pairs, dict):
                form_data["extracted_fields"] = kv_pairs
                for key, value in kv_pairs.items():
                    form_data["fields"].append({
                        "field_name": key,
                        "field_value": value
                    })
        
        # Look for additional key-value patterns in text
        field_pattern = r'([A-Za-z\s]+):\s*([^\n]+)'
        matches = re.findall(field_pattern, text)
        
        for field_name, field_value in matches:
            # Avoid duplicates
            existing = any(f["field_name"] == field_name.strip() for f in form_data["fields"])
            if not existing:
                form_data["fields"].append({
                    "field_name": field_name.strip(),
                    "field_value": field_value.strip()
                })
        
        return form_data
    
    def _extract_letter_data(self, entities: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Extract letter-specific information"""
        
        letter_data = {}
        
        # Extract dates
        if entities.get("dates"):
            dates = entities["dates"]
            if isinstance(dates, list) and dates:
                letter_data["letter_date"] = dates[0]
                letter_data["all_dates"] = dates
        
        # Extract persons
        if entities.get("persons"):
            persons = entities["persons"]
            if isinstance(persons, list):
                letter_data["persons_mentioned"] = persons
        
        # Extract organizations
        if entities.get("organizations"):
            orgs = entities["organizations"]
            if isinstance(orgs, list):
                letter_data["organizations_mentioned"] = orgs
        
        # Extract contact info
        if entities.get("emails"):
            letter_data["emails"] = entities["emails"]
        if entities.get("phone_numbers"):
            letter_data["phone_numbers"] = entities["phone_numbers"]
        
        return letter_data
    
    def _extract_contract_data(self, entities: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Extract contract-specific information"""
        
        contract_data = {}
        
        # Extract parties
        if entities.get("persons"):
            contract_data["parties_individuals"] = entities["persons"]
        if entities.get("organizations"):
            contract_data["parties_organizations"] = entities["organizations"]
        
        # Extract dates
        if entities.get("dates"):
            dates = entities["dates"]
            if isinstance(dates, list) and dates:
                contract_data["effective_date"] = dates[0]
                contract_data["all_dates"] = dates
        
        # Extract monetary values
        if entities.get("money"):
            contract_data["monetary_values"] = entities["money"]
        
        return contract_data
    
    def _extract_line_items_from_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract line items from table data"""
        line_items = []
        
        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            
            # Create structured line items
            for row_idx, row in enumerate(rows):
                if not row:
                    continue
                    
                item = {
                    "row_number": row_idx + 1
                }
                
                # Map row values to headers if available
                if headers:
                    for col_idx, header in enumerate(headers):
                        if col_idx < len(row):
                            item[header] = row[col_idx]
                else:
                    # No headers, use generic column names
                    for col_idx, value in enumerate(row):
                        item[f"column_{col_idx + 1}"] = value
                
                line_items.append(item)
        
        return line_items
    
    def save_json_to_file(self, data: Dict[str, Any], filepath: str) -> bool:
        """Save JSON data to file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving JSON to file: {e}")
            return False
    
    # # Backward compatibility methods
    # def generate_invoice_json(self, entities: Dict, tables: list, text: str) -> Dict[str, Any]:
    #     """Backward compatible invoice JSON generation"""
    #     return self.generate_dynamic_json(entities, tables, "invoice", text)
    
    # def generate_generic_json(self, entities: Dict, tables: list, document_type: str, text: str) -> Dict[str, Any]:
    #     """Backward compatible generic JSON generation"""
    #     return self.generate_dynamic_json(entities, tables, document_type, text)

# Global instance
json_output_service = JSONOutputService()