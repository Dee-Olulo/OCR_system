# /backend/app/services/document_classifier.py

from typing import Tuple
import re

class DocumentClassifier:
    """Service for classifying document types"""
    
    # Document type keywords
    DOCUMENT_TYPES = {
        "invoice": [
            "invoice", "bill to", "ship to", "payment terms", "due date",
            "invoice number", "invoice date", "amount due", "subtotal", "total amount"
        ],
        "receipt": [
            "receipt", "thank you", "purchased", "transaction", "cashier",
            "receipt number", "tender", "change", "payment method"
        ],
        "purchase_order": [
            "purchase order", "po number", "vendor", "ship to", "order date",
            "requested by", "approved by", "delivery date"
        ],
        "contract": [
            "agreement", "contract", "parties", "terms and conditions",
            "signature", "effective date", "termination", "obligations"
        ],
        "identity_document": [
            "passport", "driver license", "id card", "date of birth",
            "nationality", "identification", "issued by", "expires"
        ],
        "bank_statement": [
            "bank statement", "account number", "balance", "deposits",
            "withdrawals", "statement period", "transactions"
        ],
        "letter": [
            "dear", "sincerely", "regards", "yours", "attention",
            "subject", "reference", "to whom it may concern"
        ],
        "form": [
            "please fill", "checkbox", "signature", "date", "print name",
            "form", "application", "section", "part"
        ]
    }
    
    def classify_document(self, text: str) -> Tuple[str, float]:
        """
        Classify document based on content
        Returns: (document_type, confidence_score)
        """
        if not text or len(text.strip()) < 50:
            return "unknown", 0.0
        
        text_lower = text.lower()
        scores = {}
        
        # Calculate score for each document type
        for doc_type, keywords in self.DOCUMENT_TYPES.items():
            score = 0
            keyword_count = 0
            
            for keyword in keywords:
                # Count keyword occurrences
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                if count > 0:
                    score += count
                    keyword_count += 1
            
            # Weighted score: keyword diversity + total occurrences
            if keyword_count > 0:
                scores[doc_type] = (score * 10) + (keyword_count * 5)
        
        if not scores:
            return "unknown", 0.0
        
        # Get document type with highest score
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # Calculate confidence (normalize to 0-100)
        max_possible_score = len(self.DOCUMENT_TYPES[best_type]) * 15
        confidence = min((best_score / max_possible_score) * 100, 100.0)
        
        return best_type, round(confidence, 2)
    
    def get_required_fields(self, document_type: str) -> list:
        """Get list of required fields for document type"""
        required_fields = {
            "invoice": ["invoice_number", "invoice_date", "total_amount", "vendor"],
            "receipt": ["receipt_number", "date", "total_amount", "merchant"],
            "purchase_order": ["po_number", "order_date", "vendor", "total_amount"],
            "contract": ["parties", "effective_date", "terms"],
            "identity_document": ["name", "id_number", "date_of_birth"],
            "bank_statement": ["account_number", "statement_period", "balance"],
        }
        
        return required_fields.get(document_type, [])

document_classifier = DocumentClassifier()