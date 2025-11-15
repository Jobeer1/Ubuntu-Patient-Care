"""
FastAPI Startup Configuration (Task 2.3)

This file configures the FastAPI application for the MCP Server.
It handles:
- Database initialization
- Redis connection pool
- Middleware setup
- Exception handlers
- Startup/shutdown events
"""

import os
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

logger = logging.getLogger(__name__)


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

async def startup_event(app: FastAPI):
    """Initialize application on startup"""
    logger.info("=== FastAPI Startup ===")
    
    # 1. Verify database connection
    try:
        from api.main import engine, Base
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables initialized")
    
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {str(e)}")
        raise
    
    # 2. Verify Redis connection
    try:
        import redis
        
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis_client = redis.from_url(redis_url)
        redis_client.ping()
        logger.info("✓ Redis connection successful")
    
    except Exception as e:
        logger.warning(f"⚠ Redis unavailable: {str(e)} (caching disabled)")
    
    # 3. Log API configuration
    logger.info(f"✓ API running on {os.getenv('API_HOST', '0.0.0.0')}:{os.getenv('API_PORT', '8000')}")
    logger.info(f"✓ Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"✓ Log level: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info("=== API Ready ===")


async def shutdown_event(app: FastAPI):
    """Clean up on shutdown"""
    logger.info("=== FastAPI Shutdown ===")
    
    try:
        from api.main import engine
        engine.dispose()
        logger.info("✓ Database connections closed")
    except Exception as e:
        logger.warning(f"⚠ Error closing database: {str(e)}")
    
    logger.info("=== API Shutdown Complete ===")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI 0.93+"""
    # Startup
    await startup_event(app)
    yield
    # Shutdown
    await shutdown_event(app)


# ============================================================================
# Configuration
# ============================================================================

def configure_app(app: FastAPI):
    """Configure FastAPI application"""
    
    # 1. CORS Configuration
    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"✓ CORS configured for origins: {cors_origins}")
    
    # 2. Startup/Shutdown events
    app.add_event_handler("startup", lambda: startup_event(app))
    app.add_event_handler("shutdown", lambda: shutdown_event(app))
    
    # 3. Custom middleware for request logging
    @app.middleware("http")
    async def log_requests(request, call_next):
        """Log all HTTP requests"""
        start_time = datetime.utcnow()
        
        # Call the actual endpoint
        response = await call_next(request)
        
        # Calculate processing time
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log the request
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {process_time:.3f}s"
        )
        
        return response
    
    return app


# ============================================================================
# Create Application
# ============================================================================

def create_app() -> FastAPI:
    """Factory function to create configured FastAPI app"""
    from api.main import app as base_app
    
    # Configure the app
    configure_app(base_app)
    
    return base_app


# Import and configure the app
if __name__ == "__main__":
    import uvicorn
    
    app = create_app()
    
    # Read configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    workers = int(os.getenv("API_WORKERS", "4"))
    reload = os.getenv("ENVIRONMENT", "production") == "development"
    
    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        log_level="info"
    )
