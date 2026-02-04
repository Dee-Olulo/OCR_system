# /backend/app/models/document.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")

class DocumentCreate(BaseModel):
    filename: str
    file_type: str
    file_size: int

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    uploaded_at: datetime
    extracted_text: Optional[str] = None
    document_type: Optional[str] = None
    classification_confidence: Optional[int] = None
    entities: Optional[Dict[str, Any]] = None
    tables: Optional[List[Dict[str, Any]]] = None
    json_output_path: Optional[str] = None
    
    class Config:
        json_encoders = {ObjectId: str}

class DocumentInDB(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    tenant_id: str
    user_id: str
    filename: str
    original_path: str
    file_type: str
    file_size: int
    status: str = "pending"  # pending, processing, completed, failed
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    
    # OCR Results
    extracted_text: Optional[str] = None
    ocr_engine: Optional[str] = None
    language: Optional[str] = None
    confidence_score: Optional[float] = None
    
    # Phase 2 Fields
    document_type: Optional[str] = None
    classification_confidence: Optional[int] = None
    entities: Optional[Dict[str, Any]] = None
    tables: Optional[List[Dict[str, Any]]] = None
    
    # JSON Output - Store both path and data
    json_output_path: Optional[str] = None
    json_output: Optional[Dict[str, Any]] = None  # NEW: Store JSON directly in MongoDB
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class OCRResult(BaseModel):
    document_id: str
    extracted_text: str
    language: str
    confidence_score: float
    ocr_engine: str
    processing_time: float

class AdvancedOCRResult(BaseModel):
    """Extended OCR result with Phase 2 features"""
    document_id: str
    status: str
    extracted_text: str
    document_type: str
    classification_confidence: float
    entities: Dict[str, Any]
    tables: List[Dict[str, Any]]
    json_output: Optional[Dict[str, Any]] = None
    json_output_path: Optional[str] = None
    processed_at: Optional[datetime] = None
    ocr_engine: str
    
    class Config:
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}