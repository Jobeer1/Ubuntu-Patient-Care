"""
Orthanc Management API - Core Application
FastAPI-based REST API for the Orthanc Management Module
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from typing import Optional

from ..database.manager import DatabaseManager
from ..database.config import DatabaseSettings
from ..managers import ManagerFactory
from .middleware import SecurityMiddleware, AuditMiddleware, RateLimitMiddleware
from .auth import AuthManager
from .routers import doctors, authorizations, configurations, audit, shares, dashboard

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for dependency injection
db_manager: Optional[DatabaseManager] = None
manager_factory: Optional[ManagerFactory] = None
auth_manager: Optional[AuthManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global db_manager, manager_factory, auth_manager
    
    try:
        # Initialize database
        logger.info("Initializing database connection...")
        settings = DatabaseSettings()
        db_manager = DatabaseManager(settings)
        
        if not db_manager.initialize():
            raise Exception("Failed to initialize database")
        
        logger.info(f"Database initialized: {settings.database_type.value}")
        
        # Initialize managers
        logger.info("Initializing business logic managers...")
        manager_factory = ManagerFactory(db_manager)
        
        # Initialize authentication
        logger.info("Initializing authentication system...")
        auth_manager = AuthManager(manager_factory)
        
        # Create default admin user if none exists
        await auth_manager.ensure_default_admin()
        
        logger.info("✅ Orthanc Management API initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise
    
    finally:
        # Cleanup
        if db_manager:
            logger.info("Closing database connections...")
            # db_manager.close_all_connections()  # We'll implement this later
        logger.info("✅ Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Orthanc Management API",
    description="Comprehensive PACS management system for South African healthcare",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Security configuration
security = HTTPBearer()

# CORS middleware for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development
        "http://localhost:8080",  # Vue development
        "http://localhost:4200",  # Angular development
        "https://orthanc-management.hospital.co.za",  # Production domain
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "orthanc-management.hospital.co.za",
        "*.hospital.co.za"
    ]
)

# Custom middleware
app.add_middleware(SecurityMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)


# Dependency injection functions
async def get_db_manager() -> DatabaseManager:
    """Get database manager dependency"""
    if db_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )
    return db_manager


async def get_manager_factory() -> ManagerFactory:
    """Get manager factory dependency"""
    if manager_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Managers not initialized"
        )
    return manager_factory


async def get_auth_manager() -> AuthManager:
    """Get authentication manager dependency"""
    if auth_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not initialized"
        )
    return auth_manager


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_mgr: AuthManager = Depends(get_auth_manager)
):
    """Get current authenticated user"""
    try:
        user = await auth_mgr.verify_token(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(current_user=Depends(get_current_user)):
    """Require admin privileges"""
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def require_doctor(current_user=Depends(get_current_user)):
    """Require doctor privileges"""
    if current_user.get('role') not in ['admin', 'doctor']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor privileges required"
        )
    return current_user


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": time.time(),
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)} - {request.url}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "timestamp": time.time(),
                "path": str(request.url.path)
            }
        }
    )


# Health check endpoints
@app.get("/health", tags=["System"])
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "2.0.0",
        "service": "Orthanc Management API"
    }


@app.get("/health/detailed", tags=["System"])
async def detailed_health_check(
    managers: ManagerFactory = Depends(get_manager_factory)
):
    """Detailed system health check"""
    try:
        # Test database connection
        db_health = db_manager.get_health_status()
        
        # Test manager connections
        manager_health = managers.test_all_connections()
        
        # Check if all managers are healthy
        all_managers_healthy = all(
            result['status'] == 'healthy' 
            for result in manager_health.values()
        )
        
        overall_status = "healthy" if db_health['healthy'] and all_managers_healthy else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": time.time(),
            "version": "2.0.0",
            "components": {
                "database": db_health,
                "managers": manager_health
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e)
        }


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """API root endpoint"""
    return {
        "message": "Orthanc Management API",
        "version": "2.0.0",
        "description": "Comprehensive PACS management for South African healthcare",
        "docs": "/api/docs",
        "health": "/health",
        "compliance": ["HPCSA", "POPIA"],
        "features": [
            "Doctor management",
            "Patient authorization",
            "Configuration management",
            "Audit logging",
            "Patient sharing",
            "Real-time dashboard"
        ]
    }


# Include API routers
app.include_router(
    doctors.router,
    prefix="/api/doctors",
    tags=["Doctor Management"],
    dependencies=[Depends(get_manager_factory)]
)

app.include_router(
    authorizations.router,
    prefix="/api/authorizations",
    tags=["Patient Authorization"],
    dependencies=[Depends(get_manager_factory)]
)

app.include_router(
    configurations.router,
    prefix="/api/configurations",
    tags=["Configuration Management"],
    dependencies=[Depends(get_manager_factory)]
)

app.include_router(
    audit.router,
    prefix="/api/audit",
    tags=["Audit & Compliance"],
    dependencies=[Depends(get_manager_factory)]
)

app.include_router(
    shares.router,
    prefix="/api/shares",
    tags=["Patient Sharing"],
    dependencies=[Depends(get_manager_factory)]
)

app.include_router(
    dashboard.router,
    prefix="/api/dashboard",
    tags=["Dashboard & Analytics"],
    dependencies=[Depends(get_manager_factory)]
)


if __name__ == "__main__":
    import uvicorn
    
    # Development server configuration
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
