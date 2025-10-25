"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from config.settings import settings
from app.database import init_db
from app.routes import auth_router, token_router, users_router, audit_router, access_router, user_studies_router
from app.routes.cloud_storage import router as cloud_storage_router
from app.routes.roles import router as roles_router
from app.routes.viewer_3d import router as viewer_3d_router
from app.routes.measurements import router as measurements_router
from app.routes.segmentation import router as segmentation_router
from app.routes.cardiac_analyzer import router as cardiac_analyzer_router
from app.routes.perfusion_analyzer import router as perfusion_analyzer_router
import logging
from pathlib import Path

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MCP Server - SSO Gateway",
    description="Single Sign-On Gateway for Ubuntu Patient Care System",
    version="1.0.0"
)

# Add session middleware (required for OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(token_router)
app.include_router(users_router)
app.include_router(audit_router)
app.include_router(cloud_storage_router)
app.include_router(roles_router)
app.include_router(access_router)
app.include_router(user_studies_router)
app.include_router(viewer_3d_router)
app.include_router(measurements_router)
app.include_router(segmentation_router)
app.include_router(cardiac_analyzer_router)
app.include_router(perfusion_analyzer_router)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Starting MCP Server...")
    init_db()
    
    # Initialize default roles
    from app.database import SessionLocal
    from app.services.rbac_service import RBACService
    db = SessionLocal()
    try:
        RBACService.initialize_default_roles(db)
        logger.info("Default roles initialized")
    finally:
        db.close()
    
    logger.info("Database initialized")
    logger.info(f"Server running on http://{settings.MCP_HOST}:{settings.MCP_PORT}")

@app.get("/")
async def root():
    """Root endpoint - serve login page"""
    login_file = Path(__file__).parent.parent / "static" / "login.html"
    if login_file.exists():
        return FileResponse(login_file)
    return {"message": "Login page not found"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/login")
async def login_page():
    """Serve login page"""
    login_file = Path(__file__).parent.parent / "static" / "login.html"
    if login_file.exists():
        return FileResponse(login_file)
    return {"message": "Login page not found"}

@app.get("/signup")
async def signup_page():
    """Serve signup page"""
    signup_file = Path(__file__).parent.parent / "static" / "signup.html"
    if signup_file.exists():
        return FileResponse(signup_file)
    return {"message": "Signup page not found"}

@app.get("/dashboard")
async def dashboard_page():
    """Serve dashboard page"""
    dashboard_file = Path(__file__).parent.parent / "static" / "dashboard.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    return {"message": "Dashboard not found"}

@app.get("/test")
async def test_page():
    """Serve test login page"""
    test_file = Path(__file__).parent.parent / "static" / "test-login.html"
    if test_file.exists():
        return FileResponse(test_file)
    return {"message": "Test page not found"}

@app.get("/admin")
async def admin_dashboard():
    """Serve admin dashboard"""
    admin_file = Path(__file__).parent.parent / "static" / "admin-dashboard.html"
    if admin_file.exists():
        return FileResponse(admin_file)
    return {"message": "Admin dashboard not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        reload=True
    )
