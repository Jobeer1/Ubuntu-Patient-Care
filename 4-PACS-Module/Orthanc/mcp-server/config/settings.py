"""Configuration settings for MCP Server"""
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings"""
    
    def __init__(self):
        # Server Configuration
        self.MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
        self.MCP_PORT = int(os.getenv("MCP_PORT", "8080"))
        self.SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        
        # JWT Configuration
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))
        self.JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "86400"))
        
        # Google OAuth
        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/auth/google/callback")
        
        # Microsoft OAuth
        self.MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
        self.MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
        self.MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")
        self.MICROSOFT_REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:8080/auth/microsoft/callback")
        
        # Database
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mcp_server.db")
        
        # Redis
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.USE_REDIS = os.getenv("USE_REDIS", "false").lower() == "true"
        
        # RIS Configuration
        self.RIS_FRONTEND_URL = os.getenv("RIS_FRONTEND_URL", "https://127.0.0.1:5443")
        self.RIS_BACKEND_URL = os.getenv("RIS_BACKEND_URL", "http://127.0.0.1:5001")
        
        # PACS Configuration
        self.PACS_PROXY_URL = os.getenv("PACS_PROXY_URL", "http://127.0.0.1:5000")
        self.PACS_ORTHANC_URL = os.getenv("PACS_ORTHANC_URL", "http://127.0.0.1:8042")
        
        # Security
        allowed_origins_str = os.getenv(
            "ALLOWED_ORIGINS",
            "https://127.0.0.1:5443,http://127.0.0.1:5000,http://localhost:3000,http://localhost:8080"
        )
        self.ALLOWED_ORIGINS = [origin.strip() for origin in allowed_origins_str.split(',')]
        self.COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
        self.COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
        
        # Logging
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = os.getenv("LOG_FILE", "logs/mcp-server.log")

# Global settings instance
settings = Settings()
