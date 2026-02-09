# # /backend/app/routes/ocr_phase2.py

# from fastapi import APIRouter, Depends, HTTPException, Query
# from fastapi.responses import FileResponse
# from bson import ObjectId
# from datetime import datetime
# import os
# import json
# from app.models.document import OCRResult, AdvancedOCRResult
# from app.utils.security import get_current_user
# from app.database import get_database
# from app.services.ocr_service import ocr_service
# from app.services.pdf_service import pdf_service
# from app.services.document_processor import document_processor
# from app.services.entity_extraction_service import entity_extraction_service
# from app.services.document_classifier import document_classifier
# from app.services.json_output_service import json_output_service
# from app.services.language_detection_service import language_detection_service
# from app.services.table_extraction_service import table_extraction_service
# from app.utils.error_tracking import error_tracker

# router = APIRouter(prefix="/ocr", tags=["OCR Processing - Phase 2"])

# @router.post("/process-advanced/{document_id}")
# async def process_document_advanced(
#     document_id: str,
#     engine: str = Query("tesseract", regex="^(tesseract|easyocr|both)$"),
#     language: str = Query(None, description="Language code (auto-detect if not specified)"),
#     auto_detect_language: bool = Query(True, description="Automatically detect language"),
#     extract_entities: bool = Query(True, description="Extract entities using NLP"),
#     extract_tables: bool = Query(True, description="Extract tables"),
#     classify_document: bool = Query(True, description="Classify document type"),
#     generate_json: bool = Query(True, description="Generate structured JSON output"),
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Advanced document processing with Phase 2 features:
#     - Multi-language support with automatic detection
#     - PDF/DOCX/XLSX/PPTX support
#     - Table extraction
#     - Entity recognition (NER)
#     - Document classification
#     - Structured JSON output
#     """
#     db = get_database()
    
#     # Validate ObjectId
#     if not ObjectId.is_valid(document_id):
#         raise HTTPException(status_code=400, detail="Invalid document ID")
    
#     # Get document
#     document = await db.documents.find_one({
#         "_id": ObjectId(document_id),
#         "tenant_id": current_user["tenant_id"]
#     })
    
#     if not document:
#         raise HTTPException(status_code=404, detail="Document not found")
    
#     file_path = document["original_path"]
#     filename = document["filename"]
#     file_ext = os.path.splitext(file_path)[1].lower()
    
#     # Update status
#     await db.documents.update_one(
#         {"_id": ObjectId(document_id)},
#         {"$set": {"status": "processing"}}
#     )
    
#     try:
#         extracted_text = ""
#         tables = []
#         entities = {}
#         doc_type = "unknown"
#         classification_confidence = 0.0
#         json_output_data = None
#         json_file_path = None
#         detected_language = language or 'en'
#         language_confidence = 0.0
        
#         # Try to detect language from filename first
#         hint_lang = language_detection_service.detect_from_filename(filename) if auto_detect_language else None
        
#         # Process based on file type
#         if file_ext == ".pdf":
#             print(f"📄 Processing PDF: {filename}")
            
#             # Extract text from PDF
#             text, is_scanned, page_count = pdf_service.extract_text_from_pdf(file_path)
            
#             if is_scanned:
#                 # Convert to images and OCR with language detection
#                 print(f"🖼️  PDF is scanned, converting to images...")
#                 image_paths = pdf_service.convert_pdf_to_images(file_path)
                
#                 for img_path in image_paths:
#                     # Use auto language detection for first page
#                     if not extracted_text and auto_detect_language:
#                         result = ocr_service.extract_text_with_auto_detection(
#                             img_path, 
#                             engine,
#                             hint_lang=hint_lang
#                         )
#                         detected_language = result.get("detected_language", "en")
#                         language_confidence = result.get("language_confidence", 0.0)
#                     else:
#                         # Use detected language for subsequent pages
#                         result = ocr_service.extract_text(
#                             img_path, 
#                             engine, 
#                             lang_code=detected_language,
#                             auto_detect=False
#                         )
                    
#                     if result["success"]:
#                         extracted_text += result["text"] + "\n"
                
#                 # Cleanup temp images
#                 for img_path in image_paths:
#                     if os.path.exists(img_path):
#                         os.remove(img_path)
#             else:
#                 extracted_text = text
#                 # Detect language from extracted text
#                 if auto_detect_language:
#                     detected_language, lang_conf = language_detection_service.detect_language(extracted_text)
#                     language_confidence = lang_conf * 100
            
#             # Extract tables from PDF
#             if extract_tables:
#                 tables = pdf_service.extract_tables_from_pdf(file_path)
        
#         elif file_ext in [".docx", ".doc"]:
#             print(f"📝 Processing DOCX: {filename}")
            
#             # Extract text from DOCX
#             extracted_text = document_processor.extract_text_from_docx(file_path)
            
#             # Detect language
#             if auto_detect_language:
#                 detected_language, lang_conf = language_detection_service.detect_language(extracted_text)
#                 language_confidence = lang_conf * 100
            
#             # Extract tables
#             if extract_tables:
#                 tables = document_processor.extract_tables_from_docx(file_path)
        
#         elif file_ext in [".xlsx", ".xls"]:
#             print(f"📊 Processing Excel: {filename}")
            
#             # Extract data from Excel
#             excel_data = document_processor.extract_data_from_excel(file_path)
            
#             # Convert Excel sheets to text and tables
#             for sheet_name, sheet_data in excel_data.items():
#                 extracted_text += f"\n=== Sheet: {sheet_name} ===\n"
                
#                 # Add sheet as table
#                 if extract_tables:
#                     tables.append({
#                         "sheet_name": sheet_name,
#                         "headers": sheet_data["headers"],
#                         "rows": sheet_data["rows"],
#                         "row_count": sheet_data["row_count"],
#                         "column_count": sheet_data["column_count"]
#                     })
            
#             # Detect language from extracted text
#             if auto_detect_language:
#                 detected_language, lang_conf = language_detection_service.detect_language(extracted_text)
#                 language_confidence = lang_conf * 100
        
#         elif file_ext in [".pptx", ".ppt"]:
#             print(f"📊 Processing PowerPoint: {filename}")
            
#             # Extract text from PowerPoint
#             extracted_text = document_processor.extract_text_from_pptx(file_path)
            
#             # Detect language
#             if auto_detect_language:
#                 detected_language, lang_conf = language_detection_service.detect_language(extracted_text)
#                 language_confidence = lang_conf * 100
        
#         else:
#             # Regular image - use OCR with language detection
#             print(f"🖼️  Processing image: {filename}")
            
#             if auto_detect_language:
#                 result = ocr_service.extract_text_with_auto_detection(
#                     file_path,
#                     engine,
#                     hint_lang=hint_lang
#                 )
#             else:
#                 result = ocr_service.extract_text(
#                     file_path,
#                     engine,
#                     lang_code=language,
#                     auto_detect=False
#                 )
            
#             if result["success"]:
#                 extracted_text = result["text"]
#                 detected_language = result.get("detected_language", language or "en")
#                 language_confidence = result.get("language_confidence", 0.0)
#             else:
#                 raise Exception(result["error"])
        
#         # Log detected language
#         lang_name = language_detection_service.get_language_name(detected_language)
#         print(f"🌍 Final detected language: {lang_name} ({detected_language}) - Confidence: {language_confidence:.1f}%")
        
#         # Extract entities using NLP
#         if extract_entities and extracted_text:
#             entities = entity_extraction_service.extract_entities(extracted_text)
#             print(f"✓ Extracted {sum(len(v) if isinstance(v, list) else 0 for v in entities.values())} entities")
        
#         # Classify document
#         # NEW CODE (add language parameter):
#         if classify_document and extracted_text:
#             doc_type, classification_confidence = document_classifier.classify_document(
#                 extracted_text,
#                 language=detected_language  # ← Add this!
#             )
        
#         # Generate structured JSON output
#         if generate_json:
#             print(f"📋 Generating JSON output for document type: {doc_type}")
            
#             # Use dynamic JSON generation
#             json_output_data = json_output_service.generate_dynamic_json(
#                 entities=entities,
#                 tables=tables,
#                 document_type=doc_type,
#                 extracted_text=extracted_text
#             )
            
#             # Add language information to JSON output
#             if "metadata" not in json_output_data:
#                 json_output_data["metadata"] = {}
            
#             json_output_data["metadata"]["language"] = detected_language
#             json_output_data["metadata"]["language_name"] = lang_name
#             json_output_data["metadata"]["language_confidence"] = round(language_confidence, 2)
            
#             # Save JSON file
#             json_filename = f"{document_id}_output.json"
#             json_file_path = os.path.join(os.path.dirname(file_path), json_filename)
            
#             success = json_output_service.save_json_to_file(json_output_data, json_file_path)
            
#             if success:
#                 print(f"✓ JSON saved to file: {json_file_path}")
#             else:
#                 print(f"✗ Failed to save JSON to file")
#                 json_file_path = None
        
#         # Update document with results
#         update_data = {
#             "status": "completed",
#             "extracted_text": extracted_text,
#             "document_type": doc_type,
#             "classification_confidence": int(classification_confidence),
#             "processed_at": datetime.utcnow(),
#             "ocr_engine": engine,
#             "language": detected_language,
#             "language_name": lang_name,
#             "language_confidence": round(language_confidence, 2),
#             "entities": entities,
#             "tables": tables,
#         }
        
#         # Save JSON to both file path AND database
#         if generate_json and json_output_data:
#             update_data["json_output_path"] = json_file_path
#             update_data["json_output"] = json_output_data
#             print(f"✓ JSON output saved to database")
        
#         await db.documents.update_one(
#             {"_id": ObjectId(document_id)},
#             {"$set": update_data}
#         )
        
#         print(f"✅ Document {document_id} processing completed successfully")
        
#         return {
#             "document_id": document_id,
#             "status": "completed",
#             "extracted_text": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
#             "document_type": doc_type,
#             "classification_confidence": classification_confidence,
#             "language": detected_language,
#             "language_name": lang_name,
#             "language_confidence": language_confidence,
#             "entities_count": {
#                 "persons": len(entities.get("persons", [])),
#                 "organizations": len(entities.get("organizations", [])),
#                 "dates": len(entities.get("dates", [])),
#                 "monetary_values": len(entities.get("money", [])),
#                 "emails": len(entities.get("emails", [])),
#                 "phone_numbers": len(entities.get("phone_numbers", [])),
#             },
#             "tables_count": len(tables),
#             "json_output": json_output_data if generate_json else None,
#             "message": "Document processed successfully with multi-language support"
#         }
    
#     except Exception as e:
#         import traceback
#         error_trace = traceback.format_exc()
#         print(f"✗ Processing error: {str(e)}")
#         print(error_trace)
        
#         # Update status to failed
#         await db.documents.update_one(
#             {"_id": ObjectId(document_id)},
#             {"$set": {
#                 "status": "failed",
#                 "processed_at": datetime.utcnow(),
#                 "error": str(e)
#             }}
#         )
#         raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


# @router.get("/supported-languages")
# async def get_supported_languages():
#     """Get list of all supported languages for OCR"""
#     languages = language_detection_service.get_supported_languages()
#     return {
#         "languages": languages,
#         "total_count": len(languages),
#         "default_language": "en"
#     }


# @router.get("/result-advanced/{document_id}")
# async def get_advanced_result(
#     document_id: str,
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Get advanced processing results including entities, tables, language info, and JSON output
#     """
#     db = get_database()
    
#     if not ObjectId.is_valid(document_id):
#         raise HTTPException(status_code=400, detail="Invalid document ID")
    
#     document = await db.documents.find_one({
#         "_id": ObjectId(document_id),
#         "tenant_id": current_user["tenant_id"]
#     })
    
#     if not document:
#         raise HTTPException(status_code=404, detail="Document not found")
    
#     # Get json_output from database (preferred method)
#     json_data = document.get("json_output")
    
#     # Fallback: Load from file if not in database
#     if not json_data:
#         json_path = document.get("json_output_path")
#         if json_path and os.path.exists(json_path):
#             try:
#                 with open(json_path, 'r', encoding='utf-8') as f:
#                     json_data = json.load(f)
#                     print(f"✓ Loaded JSON from file (fallback): {json_path}")
#             except Exception as e:
#                 print(f"✗ Error loading JSON from file: {e}")
#                 json_data = None
    
#     # Build response with all fields including language info
#     response = {
#         "document_id": str(document["_id"]),
#         "status": document.get("status", "pending"),
#         "document_type": document.get("document_type", "unknown"),
#         "classification_confidence": document.get("classification_confidence", 0),
#         "language": document.get("language", "en"),
#         "language_name": document.get("language_name", "English"),
#         "language_confidence": document.get("language_confidence", 0.0),
#         "extracted_text": document.get("extracted_text", ""),
#         "entities": document.get("entities", {}),
#         "tables": document.get("tables", []),
#         "json_output": json_data,
#         "json_output_path": document.get("json_output_path"),
#         "processed_at": document.get("processed_at"),
#         "ocr_engine": document.get("ocr_engine", "unknown"),
#     }
    
#     return response


# @router.get("/download-json/{document_id}")
# async def download_json_output(
#     document_id: str,
#     current_user: dict = Depends(get_current_user)
# ):
#     """Download the generated JSON output file"""
    
#     db = get_database()
    
#     if not ObjectId.is_valid(document_id):
#         raise HTTPException(status_code=400, detail="Invalid document ID")
    
#     document = await db.documents.find_one({
#         "_id": ObjectId(document_id),
#         "tenant_id": current_user["tenant_id"]
#     })
    
#     if not document:
#         raise HTTPException(status_code=404, detail="Document not found")
    
#     json_path = document.get("json_output_path")
    
#     # If file doesn't exist but we have json_output in database, create temp file
#     if not json_path or not os.path.exists(json_path):
#         json_data = document.get("json_output")
#         if json_data:
#             # Create temporary file from database data
#             import tempfile
#             temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
#             json.dump(json_data, temp_file, indent=2, ensure_ascii=False)
#             temp_file.close()
#             json_path = temp_file.name
#             print(f"✓ Created temporary JSON file from database data")
#         else:
#             raise HTTPException(status_code=404, detail="JSON output not found")
    
#     return FileResponse(
#         path=json_path,
#         filename=f"{document['filename']}_output.json",
#         media_type="application/json"
#     )
# /backend/app/routes/ocr_phase2.py

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from bson import ObjectId
from datetime import datetime
import os
import json
from app.models.document import OCRResult, AdvancedOCRResult
from app.utils.security import get_current_user
from app.database import get_database
from app.services.ocr_service import ocr_service
from app.services.pdf_service import pdf_service
from app.services.document_processor import document_processor
from app.services.entity_extraction_service import entity_extraction_service
from app.services.document_classifier import document_classifier
from app.services.json_output_service import json_output_service
from app.services.language_detection_service import language_detection_service
from app.services.table_extraction_service import table_extraction_service
from app.utils.error_tracking import error_tracker

router = APIRouter(prefix="/ocr", tags=["OCR Processing - Phase 2"])

@router.post("/process-advanced/{document_id}")
async def process_document_advanced(
    document_id: str,
    engine: str = Query("tesseract", pattern="^(tesseract|easyocr|both)$"),
    language: str = Query(None, description="Language code (auto-detect if not specified)"),
    auto_detect_language: bool = Query(True, description="Automatically detect language"),
    extract_entities: bool = Query(True, description="Extract entities using NLP"),
    extract_tables: bool = Query(True, description="Extract tables"),
    classify_document: bool = Query(True, description="Classify document type"),
    generate_json: bool = Query(True, description="Generate structured JSON output"),
    current_user: dict = Depends(get_current_user)
):
    """
    Advanced document processing with Phase 2 features:
    - Multi-language support with automatic detection
    - PDF/DOCX/XLSX/PPTX support
    - Table extraction (from PDFs and OCR text)
    - Entity recognition (NER)
    - Document classification (multi-language)
    - Structured JSON output
    - Error tracking and logging
    """
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    # Get document
    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "tenant_id": current_user["tenant_id"]
    })
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = document["original_path"]
    filename = document["filename"]
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Update status
    await db.documents.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"status": "processing"}}
    )
    
    try:
        extracted_text = ""
        tables = []
        entities = {}
        doc_type = "unknown"
        classification_confidence = 0.0
        json_output_data = None
        json_file_path = None
        detected_language = language or 'en'
        language_confidence = 0.0
        
        # Try to detect language from filename first
        hint_lang = language_detection_service.detect_from_filename(filename) if auto_detect_language else None
        
        # Process based on file type
        if file_ext == ".pdf":
            print(f"📄 Processing PDF: {filename}")
            
            # Extract text from PDF
            text, is_scanned, page_count = pdf_service.extract_text_from_pdf(file_path)
            
            if is_scanned:
                # Convert to images and OCR with language detection
                print(f"🖼️  PDF is scanned, converting to images...")
                image_paths = pdf_service.convert_pdf_to_images(file_path)
                
                for img_path in image_paths:
                    # Use auto language detection for first page
                    if not extracted_text and auto_detect_language:
                        result = ocr_service.extract_text_with_auto_detection(
                            img_path, 
                            engine,
                            hint_lang=hint_lang
                        )
                        detected_language = result.get("detected_language", "en")
                        language_confidence = result.get("language_confidence", 0.0)
                    else:
                        # Use detected language for subsequent pages
                        result = ocr_service.extract_text(
                            img_path, 
                            engine, 
                            lang_code=detected_language,
                            auto_detect=False
                        )
                    
                    if result["success"]:
                        extracted_text += result["text"] + "\n"
                
                # Cleanup temp images
                for img_path in image_paths:
                    if os.path.exists(img_path):
                        os.remove(img_path)
            else:
                extracted_text = text
                # Detect language from extracted text
                if auto_detect_language:
                    detected_language, lang_conf = language_detection_service.detect_language(extracted_text)
                    language_confidence = lang_conf * 100
            
            # Extract tables from PDF
            if extract_tables:
                tables = pdf_service.extract_tables_from_pdf(file_path)
                
                # If no tables found from PDF structure, try text-based extraction
                if not tables and extracted_text:
                    print(f"📊 No PDF tables found, attempting text-based extraction...")
                    text_tables = table_extraction_service.extract_tables_from_text(extracted_text)
                    if text_tables:
                        tables.extend(text_tables)
                        print(f"✓ Extracted {len(text_tables)} tables from OCR text")
        
        elif file_ext in [".docx", ".doc"]:
            print(f"📝 Processing DOCX: {filename}")
            
            # Extract text from DOCX
            extracted_text = document_processor.extract_text_from_docx(file_path)
            
            # Detect language
            if auto_detect_language:
                detected_language, lang_conf = language_detection_service.detect_language(extracted_text)
                language_confidence = lang_conf * 100
            
            # Extract tables
            if extract_tables:
                tables = document_processor.extract_tables_from_docx(file_path)
        
        elif file_ext in [".xlsx", ".xls"]:
            print(f"📊 Processing Excel: {filename}")
            
            # Extract data from Excel
            excel_data = document_processor.extract_data_from_excel(file_path)
            
            # Convert Excel sheets to text and tables
            for sheet_name, sheet_data in excel_data.items():
                extracted_text += f"\n=== Sheet: {sheet_name} ===\n"
                
                # Add sheet as table
                if extract_tables:
                    tables.append({
                        "sheet_name": sheet_name,
                        "headers": sheet_data["headers"],
                        "rows": sheet_data["rows"],
                        "row_count": sheet_data["row_count"],
                        "column_count": sheet_data["column_count"]
                    })
            
            # Detect language from extracted text
            if auto_detect_language:
                detected_language, lang_conf = language_detection_service.detect_language(extracted_text)
                language_confidence = lang_conf * 100
        
        elif file_ext in [".pptx", ".ppt"]:
            print(f"📊 Processing PowerPoint: {filename}")
            
            # Extract text from PowerPoint
            extracted_text = document_processor.extract_text_from_pptx(file_path)
            
            # Detect language
            if auto_detect_language:
                detected_language, lang_conf = language_detection_service.detect_language(extracted_text)
                language_confidence = lang_conf * 100
        
        else:
            # Regular image - use OCR with language detection
            print(f"🖼️  Processing image: {filename}")
            
            if auto_detect_language:
                result = ocr_service.extract_text_with_auto_detection(
                    file_path,
                    engine,
                    hint_lang=hint_lang
                )
            else:
                result = ocr_service.extract_text(
                    file_path,
                    engine,
                    lang_code=language,
                    auto_detect=False
                )
            
            if result["success"]:
                extracted_text = result["text"]
                detected_language = result.get("detected_language", language or "en")
                language_confidence = result.get("language_confidence", 0.0)
            else:
                raise Exception(result["error"])
            
            # Extract tables from OCR text (critical for scanned invoices/documents)
            if extract_tables and extracted_text:
                print(f"📊 Attempting to extract tables from OCR text...")
                text_tables = table_extraction_service.extract_tables_from_text(extracted_text)
                if text_tables:
                    tables.extend(text_tables)
                    print(f"✓ Extracted {len(text_tables)} tables from OCR text")
        
        # Log detected language
        lang_name = language_detection_service.get_language_name(detected_language)
        print(f"🌍 Final detected language: {lang_name} ({detected_language}) - Confidence: {language_confidence:.1f}%")
        
        # Extract entities using NLP
        if extract_entities and extracted_text:
            entities = entity_extraction_service.extract_entities(extracted_text)
            print(f"✓ Extracted {sum(len(v) if isinstance(v, list) else 0 for v in entities.values())} entities")
        
        # Classify document WITH LANGUAGE PARAMETER (critical fix)
        if classify_document and extracted_text:
            doc_type, classification_confidence = document_classifier.classify_document(
                extracted_text,
                language=detected_language  # ← Critical: Pass detected language
            )
            print(f"✓ Classified as: {doc_type} (confidence: {classification_confidence}%)")
        
        # Generate structured JSON output
        if generate_json:
            print(f"📋 Generating JSON output for document type: {doc_type}")
            
            # Use dynamic JSON generation
            json_output_data = json_output_service.generate_dynamic_json(
                entities=entities,
                tables=tables,
                document_type=doc_type,
                extracted_text=extracted_text
            )
            
            # Add language information to JSON output
            if "metadata" not in json_output_data:
                json_output_data["metadata"] = {}
            
            json_output_data["metadata"]["language"] = detected_language
            json_output_data["metadata"]["language_name"] = lang_name
            json_output_data["metadata"]["language_confidence"] = round(language_confidence, 2)
            
            # Save JSON file
            json_filename = f"{document_id}_output.json"
            json_file_path = os.path.join(os.path.dirname(file_path), json_filename)
            
            success = json_output_service.save_json_to_file(json_output_data, json_file_path)
            
            if success:
                print(f"✓ JSON saved to file: {json_file_path}")
            else:
                print(f"✗ Failed to save JSON to file")
                json_file_path = None
        
        # Update document with results
        update_data = {
            "status": "completed",
            "extracted_text": extracted_text,
            "document_type": doc_type,
            "classification_confidence": int(classification_confidence),
            "processed_at": datetime.utcnow(),
            "ocr_engine": engine,
            "language": detected_language,
            "language_name": lang_name,
            "language_confidence": round(language_confidence, 2),
            "entities": entities,
            "tables": tables,
        }
        
        # Save JSON to both file path AND database
        if generate_json and json_output_data:
            update_data["json_output_path"] = json_file_path
            update_data["json_output"] = json_output_data
            print(f"✓ JSON output saved to database")
        
        await db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": update_data}
        )
        
        print(f"✅ Document {document_id} processing completed successfully")
        
        # Log success to error tracker
        error_tracker.log_info(
            f"Document processed successfully: {document_id}",
            context={
                "document_type": doc_type,
                "language": detected_language,
                "tables_extracted": len(tables),
                "classification_confidence": classification_confidence,
                "user_id": str(current_user.get("_id", "unknown"))
            }
        )
        
        return {
            "document_id": document_id,
            "status": "completed",
            "extracted_text": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
            "document_type": doc_type,
            "classification_confidence": classification_confidence,
            "language": detected_language,
            "language_name": lang_name,
            "language_confidence": language_confidence,
            "entities_count": {
                "persons": len(entities.get("persons", [])),
                "organizations": len(entities.get("organizations", [])),
                "dates": len(entities.get("dates", [])),
                "monetary_values": len(entities.get("money", [])),
                "emails": len(entities.get("emails", [])),
                "phone_numbers": len(entities.get("phone_numbers", [])),
            },
            "tables_count": len(tables),
            "json_output": json_output_data if generate_json else None,
            "message": "Document processed successfully with multi-language support"
        }
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"✗ Processing error: {str(e)}")
        print(error_trace)
        
        # Log error with full context using error tracker
        error_tracker.log_error(
            error=e,
            context={
                "document_id": document_id,
                "filename": filename,
                "file_type": file_ext,
                "user_id": str(current_user.get("_id", "unknown")),
                "tenant_id": str(current_user.get("tenant_id", "unknown"))
            },
            user_id=str(current_user.get("_id", "unknown")),
            document_id=document_id
        )
        
        # Update status to failed
        await db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {
                "status": "failed",
                "processed_at": datetime.utcnow(),
                "error": str(e)
            }}
        )
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.get("/supported-languages")
async def get_supported_languages():
    """Get list of all supported languages for OCR"""
    languages = language_detection_service.get_supported_languages()
    return {
        "languages": languages,
        "total_count": len(languages),
        "default_language": "en"
    }


@router.get("/result-advanced/{document_id}")
async def get_advanced_result(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get advanced processing results including entities, tables, language info, and JSON output
    """
    db = get_database()
    
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "tenant_id": current_user["tenant_id"]
    })
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get json_output from database (preferred method)
    json_data = document.get("json_output")
    
    # Fallback: Load from file if not in database
    if not json_data:
        json_path = document.get("json_output_path")
        if json_path and os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    print(f"✓ Loaded JSON from file (fallback): {json_path}")
            except Exception as e:
                print(f"✗ Error loading JSON from file: {e}")
                json_data = None
    
    # Build response with all fields including language info
    response = {
        "document_id": str(document["_id"]),
        "status": document.get("status", "pending"),
        "document_type": document.get("document_type", "unknown"),
        "classification_confidence": document.get("classification_confidence", 0),
        "language": document.get("language", "en"),
        "language_name": document.get("language_name", "English"),
        "language_confidence": document.get("language_confidence", 0.0),
        "extracted_text": document.get("extracted_text", ""),
        "entities": document.get("entities", {}),
        "tables": document.get("tables", []),
        "json_output": json_data,
        "json_output_path": document.get("json_output_path"),
        "processed_at": document.get("processed_at"),
        "ocr_engine": document.get("ocr_engine", "unknown"),
    }
    
    return response


@router.get("/download-json/{document_id}")
async def download_json_output(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Download the generated JSON output file"""
    
    db = get_database()
    
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "tenant_id": current_user["tenant_id"]
    })
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    json_path = document.get("json_output_path")
    
    # If file doesn't exist but we have json_output in database, create temp file
    if not json_path or not os.path.exists(json_path):
        json_data = document.get("json_output")
        if json_data:
            # Create temporary file from database data
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
            json.dump(json_data, temp_file, indent=2, ensure_ascii=False)
            temp_file.close()
            json_path = temp_file.name
            print(f"✓ Created temporary JSON file from database data")
        else:
            raise HTTPException(status_code=404, detail="JSON output not found")
    
    return FileResponse(
        path=json_path,
        filename=f"{document['filename']}_output.json",
        media_type="application/json"
    )