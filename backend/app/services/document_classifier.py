# # /backend/app/services/document_classifier.py

# from typing import Tuple
# import re

# class DocumentClassifier:
#     """Service for classifying document types"""
    
#     # Document type keywords
#     DOCUMENT_TYPES = {
#         "invoice": [
#             "invoice", "bill to", "ship to", "payment terms", "due date",
#             "invoice number", "invoice date", "amount due", "subtotal", "total amount"
#         ],
#         "receipt": [
#             "receipt", "thank you", "purchased", "transaction", "cashier",
#             "receipt number", "tender", "change", "payment method"
#         ],
#         "purchase_order": [
#             "purchase order", "po number", "vendor", "ship to", "order date",
#             "requested by", "approved by", "delivery date"
#         ],
#         "contract": [
#             "agreement", "contract", "parties", "terms and conditions",
#             "signature", "effective date", "termination", "obligations"
#         ],
#         "identity_document": [
#             "passport", "driver license", "id card", "date of birth",
#             "nationality", "identification", "issued by", "expires"
#         ],
#         "bank_statement": [
#             "bank statement", "account number", "balance", "deposits",
#             "withdrawals", "statement period", "transactions"
#         ],
#         "letter": [
#             "dear", "sincerely", "regards", "yours", "attention",
#             "subject", "reference", "to whom it may concern"
#         ],
#         "form": [
#             "please fill", "checkbox", "signature", "date", "print name",
#             "form", "application", "section", "part"
#         ]
#     }
    
#     def classify_document(self, text: str) -> Tuple[str, float]:
#         """
#         Classify document based on content
#         Returns: (document_type, confidence_score)
#         """
#         if not text or len(text.strip()) < 50:
#             return "unknown", 0.0
        
#         text_lower = text.lower()
#         scores = {}
        
#         # Calculate score for each document type
#         for doc_type, keywords in self.DOCUMENT_TYPES.items():
#             score = 0
#             keyword_count = 0
            
#             for keyword in keywords:
#                 # Count keyword occurrences
#                 count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
#                 if count > 0:
#                     score += count
#                     keyword_count += 1
            
#             # Weighted score: keyword diversity + total occurrences
#             if keyword_count > 0:
#                 scores[doc_type] = (score * 10) + (keyword_count * 5)
        
#         if not scores:
#             return "unknown", 0.0
        
#         # Get document type with highest score
#         best_type = max(scores, key=scores.get)
#         best_score = scores[best_type]
        
#         # Calculate confidence (normalize to 0-100)
#         max_possible_score = len(self.DOCUMENT_TYPES[best_type]) * 15
#         confidence = min((best_score / max_possible_score) * 100, 100.0)
        
#         return best_type, round(confidence, 2)
    
#     def get_required_fields(self, document_type: str) -> list:
#         """Get list of required fields for document type"""
#         required_fields = {
#             "invoice": ["invoice_number", "invoice_date", "total_amount", "vendor"],
#             "receipt": ["receipt_number", "date", "total_amount", "merchant"],
#             "purchase_order": ["po_number", "order_date", "vendor", "total_amount"],
#             "contract": ["parties", "effective_date", "terms"],
#             "identity_document": ["name", "id_number", "date_of_birth"],
#             "bank_statement": ["account_number", "statement_period", "balance"],
#         }
        
#         return required_fields.get(document_type, [])

# document_classifier = DocumentClassifier()
# /backend/app/services/document_classifier.py

from typing import Tuple
import re

class DocumentClassifier:
    """Service for classifying document types with multi-language support"""
    
    # Document type keywords in multiple languages
    DOCUMENT_TYPES = {
        "invoice": {
            "en": [
                "invoice", "bill to", "ship to", "payment terms", "due date",
                "invoice number", "invoice date", "amount due", "subtotal", "total amount",
                "tax", "vat", "payment", "billing"
            ],
            "de": [
                "rechnung", "rechnungsnummer", "rechnungsdatum", "kundennummer",
                "gesamtbetrag", "zwischensumme", "mwst", "mehrwertsteuer",
                "zahlungsbedingungen", "fälligkeitsdatum", "bankverbindung",
                "iban", "bic", "betrag", "steuer", "netto", "brutto"
            ],
            "fr": ["facture", "montant", "total", "tva"],
            "es": ["factura", "importe", "total", "iva"],
        },
        "receipt": {
            "en": [
                "receipt", "thank you", "purchased", "transaction", "cashier",
                "receipt number", "tender", "change", "payment method"
            ],
            "de": [
                "quittung", "beleg", "kassenbon", "kassennummer", "vielen dank",
                "bezahlt", "rückgeld", "kasse"
            ],
            "fr": ["reçu", "ticket", "caisse"],
            "es": ["recibo", "ticket", "caja"],
        },
        "purchase_order": {
            "en": [
                "purchase order", "po number", "vendor", "ship to", "order date",
                "requested by", "approved by", "delivery date"
            ],
            "de": [
                "bestellung", "bestellnummer", "lieferant", "lieferdatum",
                "bestelldatum", "versand"
            ],
            "fr": ["bon de commande", "commande", "fournisseur"],
            "es": ["orden de compra", "pedido", "proveedor"],
        },
        "contract": {
            "en": [
                "agreement", "contract", "parties", "terms and conditions",
                "signature", "effective date", "termination", "obligations"
            ],
            "de": [
                "vertrag", "vereinbarung", "vertragspartner", "bedingungen",
                "unterschrift", "gültig ab", "kündigung", "verpflichtungen"
            ],
            "fr": ["contrat", "accord", "signature", "conditions"],
            "es": ["contrato", "acuerdo", "firma", "condiciones"],
        },
        "identity_document": {
            "en": [
                "passport", "driver license", "id card", "date of birth",
                "nationality", "identification", "issued by", "expires"
            ],
            "de": [
                "reisepass", "personalausweis", "führerschein", "geburtsdatum",
                "staatsangehörigkeit", "ausgestellt", "gültig bis"
            ],
            "fr": ["passeport", "carte d'identité", "permis"],
            "es": ["pasaporte", "documento de identidad", "licencia"],
        },
        "bank_statement": {
            "en": [
                "bank statement", "account number", "balance", "deposits",
                "withdrawals", "statement period", "transactions"
            ],
            "de": [
                "kontoauszug", "kontonummer", "saldo", "einzahlung",
                "auszahlung", "überweisung", "transaktion", "bank"
            ],
            "fr": ["relevé bancaire", "compte", "solde", "virement"],
            "es": ["extracto bancario", "cuenta", "saldo", "transferencia"],
        },
        "letter": {
            "en": [
                "dear", "sincerely", "regards", "yours", "attention",
                "subject", "reference", "to whom it may concern"
            ],
            "de": [
                "sehr geehrte", "mit freundlichen grüßen", "betreff",
                "referenz", "anrede"
            ],
            "fr": ["cher", "cordialement", "objet", "référence"],
            "es": ["estimado", "atentamente", "asunto", "referencia"],
        },
        "form": {
            "en": [
                "please fill", "checkbox", "signature", "date", "print name",
                "form", "application", "section", "part"
            ],
            "de": [
                "bitte ausfüllen", "formular", "antrag", "unterschrift",
                "datum", "abschnitt"
            ],
            "fr": ["veuillez remplir", "formulaire", "signature", "date"],
            "es": ["por favor complete", "formulario", "firma", "fecha"],
        }
    }
    
    def classify_document(self, text: str, language: str = None) -> Tuple[str, float]:
        """
        Classify document based on content with multi-language support
        
        Args:
            text: Document text
            language: Detected language code (e.g., 'de', 'en', 'fr')
        
        Returns: (document_type, confidence_score)
        """
        if not text or len(text.strip()) < 50:
            return "unknown", 0.0
        
        text_lower = text.lower()
        scores = {}
        
        # Calculate score for each document type
        for doc_type, lang_keywords in self.DOCUMENT_TYPES.items():
            score = 0
            keyword_count = 0
            
            # Check all language keywords if language not specified
            # Otherwise prioritize detected language
            languages_to_check = []
            if language and language in lang_keywords:
                languages_to_check = [language, "en"]  # Check detected lang + English
            else:
                languages_to_check = list(lang_keywords.keys())
            
            for lang in languages_to_check:
                if lang not in lang_keywords:
                    continue
                    
                keywords = lang_keywords[lang]
                lang_weight = 2.0 if lang == language else 1.0  # Boost detected language
                
                for keyword in keywords:
                    # Count keyword occurrences
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    count = len(re.findall(pattern, text_lower))
                    if count > 0:
                        score += (count * lang_weight)
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
        # Use all keywords from all languages for max possible score
        all_keywords_count = sum(
            len(keywords) 
            for lang_keywords in self.DOCUMENT_TYPES[best_type].values() 
            for keywords in [lang_keywords]
        )
        max_possible_score = all_keywords_count * 15
        confidence = min((best_score / max_possible_score) * 100, 100.0)
        
        # Boost confidence if we found strong matches
        if keyword_count > 5:
            confidence = min(confidence * 1.2, 100.0)
        
        print(f"📋 Classification: {best_type} (confidence: {confidence:.1f}%, keywords found: {keyword_count})")
        
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