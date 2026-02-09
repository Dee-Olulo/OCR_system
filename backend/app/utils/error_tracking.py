# /backend/app/utils/error_tracking.py

"""
Error tracking and logging setup
Integrates Sentry for production error monitoring
"""

import logging
import sys
from typing import Optional
from datetime import datetime
import traceback
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Sentry integration (optional - only if SENTRY_DSN is set)
SENTRY_ENABLED = False

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    SENTRY_DSN = os.getenv('SENTRY_DSN')
    
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                )
            ],
            traces_sample_rate=0.1,  # 10% of transactions
            profiles_sample_rate=0.1,
            environment=os.getenv('ENVIRONMENT', 'development'),
        )
        SENTRY_ENABLED = True
        logger.info("✓ Sentry error tracking enabled")
    else:
        logger.info("⚠️  Sentry DSN not configured. Error tracking disabled.")
except ImportError:
    logger.info("⚠️  Sentry not installed. Run: pip install sentry-sdk")


class ErrorTracker:
    """Error tracking and logging utility"""
    
    @staticmethod
    def log_error(
        error: Exception,
        context: dict = None,
        user_id: str = None,
        document_id: str = None
    ):
        """
        Log error with context
        
        Args:
            error: Exception object
            context: Additional context dict
            user_id: User ID if available
            document_id: Document ID if available
        """
        error_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "user_id": user_id,
            "document_id": document_id,
            "context": context or {}
        }
        
        # Log to file
        logger.error(f"Error occurred: {error_data}")
        
        # Send to Sentry if enabled
        if SENTRY_ENABLED:
            with sentry_sdk.push_scope() as scope:
                if user_id:
                    scope.set_user({"id": user_id})
                if document_id:
                    scope.set_tag("document_id", document_id)
                if context:
                    scope.set_context("additional_context", context)
                
                sentry_sdk.capture_exception(error)
    
    @staticmethod
    def log_warning(message: str, context: dict = None):
        """Log warning message"""
        logger.warning(f"{message} - Context: {context}")
    
    @staticmethod
    def log_info(message: str, context: dict = None):
        """Log info message"""
        logger.info(f"{message} - Context: {context}")
    
    @staticmethod
    def capture_message(message: str, level: str = "info"):
        """Capture custom message in Sentry"""
        if SENTRY_ENABLED:
            sentry_sdk.capture_message(message, level=level)
        
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)


# Create global instance
error_tracker = ErrorTracker()


# Decorator for automatic error tracking
def track_errors(func):
    """Decorator to automatically track errors in functions"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_tracker.log_error(
                error=e,
                context={
                    "function": func.__name__,
                    "args": str(args)[:200],  # Truncate long args
                    "kwargs": str(kwargs)[:200]
                }
            )
            raise
    return wrapper


async def track_errors_async(func):
    """Decorator for async functions"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_tracker.log_error(
                error=e,
                context={
                    "function": func.__name__,
                    "args": str(args)[:200],
                    "kwargs": str(kwargs)[:200]
                }
            )
            raise
    return wrapper