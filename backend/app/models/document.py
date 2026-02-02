# /backend/app/models/document.py

from pydantic import BaseModel, Field
from typing import Optional
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
    extracted_text: Optional[str] = None
    ocr_engine: Optional[str] = None
    language: Optional[str] = None
    confidence_score: Optional[float] = None
    
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