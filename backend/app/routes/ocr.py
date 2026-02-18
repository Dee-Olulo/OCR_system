# /backend/app/routes/ocr.py

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from datetime import datetime
import os
from app.models.document import OCRResult
from app.utils.security import get_current_user
from app.database import get_database
from app.services.ocr_service import ocr_service
from app.services.pdf_service import pdf_service
from app.services.docx_service import docx_service
from app.services.excel_service import excel_service

router = APIRouter(prefix="/ocr", tags=["OCR Processing"])

@router.post("/process/{document_id}", response_model=OCRResult)
async def process_document(
    document_id: str,
    engine: str = Query("tesseract", regex="^(tesseract|easyocr|both)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Process document with OCR

    Supported formats:
    - Images: JPG, PNG, TIFF
    - PDF: digital (text extracted directly) or scanned (converted to images then OCR)
    - Word: DOCX, DOC
    - Excel: XLSX, XLS
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

    # Update status to processing
    await db.documents.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"status": "processing"}}
    )

    try:
        file_path = document["original_path"]
        file_ext = os.path.splitext(document["filename"])[1].lower()
        extracted_text = ""
        ocr_engine_used = "none"
        confidence_score = 0.0
        processing_time = 0.0

        # ── PDF ──────────────────────────────────────────────────────────────
        if file_ext == ".pdf":
            text, is_scanned, page_count = pdf_service.extract_text_from_pdf(file_path)

            if is_scanned:
                # Scanned PDF → convert each page to image → OCR
                print(f"Scanned PDF detected ({page_count} pages) - converting to images...")
                image_paths = pdf_service.convert_pdf_to_images(file_path)
                extracted_text = ""
                for img_path in image_paths:
                    if engine == "both":
                        result = ocr_service.extract_text_both(img_path)
                        page_result = result["best_result"]
                    else:
                        page_result = ocr_service.extract_text(img_path, engine)

                    if page_result["success"]:
                        extracted_text += page_result["text"] + "\n"
                        confidence_score = page_result.get("confidence", 0.0)
                        processing_time += page_result.get("processing_time", 0.0)
                        ocr_engine_used = page_result.get("ocr_engine", engine)

                pdf_service.cleanup_images(image_paths)

            else:
                # Digital PDF → text extracted directly, no OCR needed
                print(f"Digital PDF detected ({page_count} pages) - extracting text directly...")
                extracted_text = text
                ocr_engine_used = "pymupdf"
                confidence_score = 1.0

        # ── DOCX / DOC ───────────────────────────────────────────────────────
        elif file_ext in [".docx", ".doc"]:
            print(f"Word document detected - extracting text...")
            extracted_text = docx_service.extract_text_from_docx(file_path)
            ocr_engine_used = "python-docx"
            confidence_score = 1.0

        # ── XLSX / XLS ───────────────────────────────────────────────────────
        elif file_ext in [".xlsx", ".xls"]:
            print(f"Excel file detected - extracting text...")
            extracted_text = excel_service.extract_text_from_excel(file_path)
            ocr_engine_used = "openpyxl"
            confidence_score = 1.0

        # ── IMAGES ───────────────────────────────────────────────────────────
        elif file_ext in [".jpg", ".jpeg", ".png", ".tiff", ".tif"]:
            print(f"Image detected - running OCR...")
            if engine == "both":
                result = ocr_service.extract_text_both(file_path)
                ocr_result = result["best_result"]
            else:
                ocr_result = ocr_service.extract_text(file_path, engine)

            if not ocr_result["success"]:
                await db.documents.update_one(
                    {"_id": ObjectId(document_id)},
                    {"$set": {"status": "failed", "processed_at": datetime.utcnow()}}
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"OCR processing failed: {ocr_result['error']}"
                )

            extracted_text = ocr_result["text"]
            confidence_score = ocr_result.get("confidence", 0.0)
            processing_time = ocr_result.get("processing_time", 0.0)
            ocr_engine_used = ocr_result.get("ocr_engine", engine)

        # ── UNSUPPORTED ──────────────────────────────────────────────────────
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}"
            )

        # ── SAVE RESULTS ─────────────────────────────────────────────────────
        if not extracted_text.strip():
            await db.documents.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"status": "failed", "processed_at": datetime.utcnow()}}
            )
            raise HTTPException(
                status_code=500,
                detail="No text could be extracted from this document."
            )

        await db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "status": "completed",
                    "extracted_text": extracted_text,
                    "ocr_engine": ocr_engine_used,
                    "language": "en",
                    "confidence_score": confidence_score,
                    "processed_at": datetime.utcnow()
                }
            }
        )

        return OCRResult(
            document_id=document_id,
            extracted_text=extracted_text,
            language="en",
            confidence_score=confidence_score,
            ocr_engine=ocr_engine_used,
            processing_time=processing_time
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"status": "failed", "processed_at": datetime.utcnow()}}
        )
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.get("/result/{document_id}")
async def get_ocr_result(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get OCR result for a processed document"""
    db = get_database()

    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")

    document = await db.documents.find_one({
        "_id": ObjectId(document_id),
        "tenant_id": current_user["tenant_id"]
    })

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document["status"] != "completed":
        return {
            "document_id": document_id,
            "status": document["status"],
            "message": f"Document is {document['status']}"
        }

    return {
        "document_id": document_id,
        "status": "completed",
        "extracted_text": document.get("extracted_text", ""),
        "language": document.get("language", "en"),
        "confidence_score": document.get("confidence_score", 0.0),
        "ocr_engine": document.get("ocr_engine", "unknown"),
        "processed_at": document.get("processed_at")
    }