# # /backend/app/main.py

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from contextlib import asynccontextmanager
# from app.config import settings
# from app.database import connect_to_mongo, close_mongo_connection
# from app.routes import auth, documents, ocr
# from app.routes import folder_routes, websocket_routes, task_routes
# from app.services.folder_monitor_service import folder_monitor_service
# from app.utils.error_tracking import error_tracker, logger


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Lifespan events"""
#     # Startup
#     print("🚀 Starting up...")
#     await connect_to_mongo()
#     print("✅ Application ready!")
#     yield
#     # Shutdown
#     print("🛑 Shutting down...")
#     await close_mongo_connection()

# # Create FastAPI app
# app = FastAPI(
#     title=settings.APP_NAME,
#     version=settings.VERSION,
#     description="OCR Document Intelligence System API",
#     lifespan=lifespan
# )

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.CORS_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Include routers
# app.include_router(auth.router, prefix="/api/v1")
# app.include_router(documents.router, prefix="/api/v1")
# app.include_router(ocr.router, prefix="/api/v1")
# app.include_router(folder_routes.router, prefix="/api/v1")
# app.include_router(task_routes.router, prefix="/api/v1")
# app.include_router(websocket_routes.router)
# # Shutdown event
# @app.on_event("shutdown")
# async def shutdown_event():
#     await folder_monitor_service.shutdown()

# @app.get("/")
# async def root():
#     """Root endpoint"""
#     return {
#         "message": "Welcome to OCR Document Intelligence System",
#         "version": settings.VERSION,
#         "docs": "/docs"
#     }

# @app.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     return {
#         "status": "healthy",
#         "service": settings.APP_NAME,
#         "version": settings.VERSION
#     }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "app.main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True
#     )
# /backend/app/main.py

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.routes import auth, documents, ocr
from app.routes import folder_routes, websocket_routes, task_routes, insurance_view
from app.services.folder_monitor_service import folder_monitor_service
from app.utils.error_tracking import error_tracker, logger
import time
import os

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup
    logger.info("🚀 Starting up...")
    await connect_to_mongo()
    logger.info("✅ Application ready!")
    yield
    # Shutdown
    logger.info("🛑 Shutting down...")
    await folder_monitor_service.shutdown()
    await close_mongo_connection()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="OCR Document Intelligence System API",
    lifespan=lifespan
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions"""
    error_tracker.log_error(
        error=exc,
        context={
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else "unknown"
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred",
            "type": type(exc).__name__
        }
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and their processing time"""
    start_time = time.time()
    
    # Log request
    logger.info(f"→ {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"← {request.method} {request.url.path} "
            f"Status: {response.status_code} "
            f"Time: {process_time:.3f}s"
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"✗ {request.method} {request.url.path} "
            f"Error: {str(e)} "
            f"Time: {process_time:.3f}s"
        )
        raise


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(ocr.router, prefix="/api/v1")
app.include_router(folder_routes.router, prefix="/api/v1")
app.include_router(task_routes.router, prefix="/api/v1")
app.include_router(websocket_routes.router)
app.include_router(insurance_view.router, prefix="/api/v1")


# Shutdown event (keep for compatibility)
@app.on_event("shutdown")
async def shutdown_event():
    await folder_monitor_service.shutdown()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to OCR Document Intelligence System",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "timestamp": time.time()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )