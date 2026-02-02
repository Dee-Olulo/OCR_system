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
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = [".jpg", ".jpeg", ".png", ".tiff", ".tif"]
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:4200"]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load from environment variables
        self.MONGODB_URL = os.getenv("MONGODB_URL", self.MONGODB_URL)
        self.DATABASE_NAME = os.getenv("DATABASE_NAME", self.DATABASE_NAME)
        self.SECRET_KEY = os.getenv("SECRET_KEY", self.SECRET_KEY)
        self.DEBUG = os.getenv("DEBUG", str(self.DEBUG)).lower() == "true"

settings = Settings()