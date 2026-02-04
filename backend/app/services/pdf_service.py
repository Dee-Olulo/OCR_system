# /backend/app/services/pdf_service.py

import PyPDF2
import pdfplumber
from pdf2image import convert_from_path
from typing import List, Dict, Tuple
import tempfile
import os

class PDFService:
    """Service for processing PDF documents"""
    
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> Tuple[str, bool, int]:
        """
        Extract text from PDF
        Returns: (text, is_scanned, page_count)
        """
        try:
            # Try extracting with pdfplumber (better for text PDFs)
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # Check if PDF is scanned (little to no text)
            is_scanned = len(text.strip()) < 100
            
            return text.strip(), is_scanned, page_count
            
        except Exception as e:
            print(f"PDF text extraction error: {e}")
            # Fallback to PyPDF2
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    page_count = len(reader.pages)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    
                    is_scanned = len(text.strip()) < 100
                    return text.strip(), is_scanned, page_count
            except:
                return "", True, 0
    
    @staticmethod
    def convert_pdf_to_images(pdf_path: str) -> List[str]:
        """
        Convert PDF pages to images for OCR
        Returns list of image file paths
        """
        try:
            # Create temp directory for images
            temp_dir = tempfile.mkdtemp()
            
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300)
            
            image_paths = []
            for i, image in enumerate(images):
                image_path = os.path.join(temp_dir, f"page_{i+1}.png")
                image.save(image_path, 'PNG')
                image_paths.append(image_path)
            
            return image_paths
        
        except Exception as e:
            print(f"PDF to image conversion error: {e}")
            return []
    
    @staticmethod
    def extract_tables_from_pdf(pdf_path: str) -> List[Dict]:
        """
        Extract tables from PDF
        Returns list of tables as dictionaries
        """
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    
                    for table_num, table in enumerate(page_tables, 1):
                        if table and len(table) > 0:
                            # Convert table to dictionary format
                            headers = table[0] if table[0] else []
                            rows = table[1:] if len(table) > 1 else []
                            
                            table_dict = {
                                "page": page_num,
                                "table_number": table_num,
                                "headers": headers,
                                "rows": rows,
                                "row_count": len(rows),
                                "column_count": len(headers)
                            }
                            tables.append(table_dict)
        
        except Exception as e:
            print(f"Table extraction error: {e}")
        
        return tables

pdf_service = PDFService()