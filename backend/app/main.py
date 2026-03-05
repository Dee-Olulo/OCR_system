# /backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.routes import auth, documents, ocr, llm_extraction
from app.routes.webhook import router as webhook_router
from app.routes.sheets  import router as sheets_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up OCR System...")
    await connect_to_mongo()
    print(f"MongoDB connected: {settings.DATABASE_NAME}")
    print(f"n8n invoice webhook: {settings.N8N_INVOICE_WEBHOOK_URL}")
    yield
    print("Shutting down...")
    await close_mongo_connection()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="OCR Document Intelligence System — Phase 5 (n8n Automation)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router,           prefix="/api/v1")
app.include_router(documents.router,      prefix="/api/v1")
app.include_router(ocr.router,            prefix="/api/v1")
app.include_router(llm_extraction.router, prefix="/api/v1")
app.include_router(webhook_router,        prefix="/api/v1")
app.include_router(sheets_router,         prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service":              settings.APP_NAME,
        "version":              settings.VERSION,
        "docs":                 "/docs",
        "n8n_webhook_url":      settings.N8N_INVOICE_WEBHOOK_URL,
        "n8n_secret_set":       bool(settings.N8N_WEBHOOK_SECRET),
        "sheets_configured": bool(settings.MASTER_SPREADSHEET_ID),
    }


@app.get("/health")
async def health_check():
    """Basic liveness probe — unchanged from previous phases."""
    return {
        "status":  "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)