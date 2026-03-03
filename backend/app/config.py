# /backend/app/config.py

from pydantic import BaseModel
from typing import Optional
import os

class Settings(BaseModel):
    # App Settings
    APP_NAME: str = "OCR Document Intelligence System"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "ocr_system"
    
    # Security
    SECRET_KEY: str = "JmpDw_1Jsej-ZHpFGK6VIK-ReuvUf6zn2rjN1lhxt38"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: list = [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".pdf", ".docx", ".doc", ".xlsx", ".xls"]
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:4200"]

    OCR_REGION_CONFIDENCE_THRESHOLD: int = 70
    OCR_REGION_PADDING: int = 8
    OCR_REGION_SCALE: int = 3
    OCR_REGION_MIN_HEIGHT: int = 20
    OCR_REGION_MAX_REPROCESS: int = 10

    # Secret shared between n8n and this backend.
    # n8n sends it in the X-Webhook-Secret header on every call.
    # The backend sends it when calling n8n webhook endpoints.
    N8N_WEBHOOK_SECRET: str = ""

    # Base URL of the n8n instance
    N8N_BASE_URL: str = "http://localhost:5678"

    # Production webhook URL — Angular POSTs here after upload to trigger pipeline.
    # Format: {N8N_BASE_URL}/webhook/{path-you-set-in-n8n-webhook-node}
    N8N_INVOICE_WEBHOOK_URL: str = "http://localhost:5678/webhook/ocr-invoice-process"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load from environment variables
        self.MONGODB_URL = os.getenv("MONGODB_URL", self.MONGODB_URL)
        self.DATABASE_NAME = os.getenv("DATABASE_NAME", self.DATABASE_NAME)
        self.SECRET_KEY = os.getenv("SECRET_KEY", self.SECRET_KEY)
        self.DEBUG = os.getenv("DEBUG", str(self.DEBUG)).lower() == "true"
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", ",".join(self.CORS_ORIGINS)).split(",")
        self.N8N_WEBHOOK_SECRET = os.getenv("N8N_WEBHOOK_SECRET", self.N8N_WEBHOOK_SECRET)
        self.N8N_BASE_URL = os.getenv("N8N_BASE_URL", self.N8N_BASE_URL)
        self.N8N_INVOICE_WEBHOOK_URL = os.getenv("N8N_INVOICE_WEBHOOK_URL", self.N8N_INVOICE_WEBHOOK_URL)
settings = Settings()