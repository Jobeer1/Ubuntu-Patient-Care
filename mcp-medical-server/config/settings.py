"""Configuration settings for Medical Schemes Server"""
import os
from typing import Optional

class Settings:
    """Application settings"""
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./medical_schemes.db"
    )
    
    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "your-secret-key-change-in-production-min-32-chars"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_COOKIE_NAME: str = "access_token"
    JWT_COOKIE_SECURE: bool = os.getenv("JWT_COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_HTTPONLY: bool = True
    JWT_COOKIE_SAMESITE: str = "Lax"
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_CALLBACK_URL: str = os.getenv(
        "GOOGLE_CALLBACK_URL",
        "http://localhost:8080/auth/google/callback"
    )
    
    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: Optional[str] = os.getenv("MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET: Optional[str] = os.getenv("MICROSOFT_CLIENT_SECRET")
    MICROSOFT_CALLBACK_URL: str = os.getenv(
        "MICROSOFT_CALLBACK_URL",
        "http://localhost:8080/auth/microsoft/callback"
    )
    MICROSOFT_TENANT: str = os.getenv("MICROSOFT_TENANT", "common")
    
    # SSO Configuration
    SSO_ENABLED: bool = os.getenv("SSO_ENABLED", "true").lower() == "true"
    GOOGLE_SSO_ENABLED: bool = GOOGLE_CLIENT_ID is not None and GOOGLE_CLIENT_SECRET is not None
    MICROSOFT_SSO_ENABLED: bool = MICROSOFT_CLIENT_ID is not None and MICROSOFT_CLIENT_SECRET is not None
    
    # Server Configuration
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8080"))
    
    # AWS Configuration for Claude 4 Sonnet
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # AWS Bedrock Configuration
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
    BEDROCK_REGION: str = os.getenv("BEDROCK_REGION", "us-east-1")
    BEDROCK_MAX_TOKENS: int = int(os.getenv("BEDROCK_MAX_TOKENS", "4096"))
    BEDROCK_TEMPERATURE: float = float(os.getenv("BEDROCK_TEMPERATURE", "0.1"))
    
    # Claude AI Configuration
    CLAUDE_ENABLED: bool = os.getenv("CLAUDE_ENABLED", "true").lower() == "true"
    CLAUDE_CONFIG_PATH: str = os.getenv("CLAUDE_CONFIG_PATH", "config/aws_config.ini")
    
    # UI Configuration
    UI_ENABLED: bool = os.getenv("UI_ENABLED", "true").lower() == "true"
    UI_PORT: int = int(os.getenv("UI_PORT", "3000"))
    UI_HOST: str = os.getenv("UI_HOST", "localhost")
    
    # Enhanced MCP Configuration
    MCP_ENHANCED_TOOLS: bool = os.getenv("MCP_ENHANCED_TOOLS", "true").lower() == "true"
    MCP_AI_INTEGRATION: bool = os.getenv("MCP_AI_INTEGRATION", "true").lower() == "true"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS Configuration
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8000"
    ]
    
    # Email Configuration (optional)
    SMTP_SERVER: Optional[str] = os.getenv("SMTP_SERVER")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    SMTP_FROM_EMAIL: Optional[str] = os.getenv("SMTP_FROM_EMAIL")
    
    # OneDrive/Cloud Configuration (optional)
    ONEDRIVE_CLIENT_ID: Optional[str] = os.getenv("ONEDRIVE_CLIENT_ID")
    ONEDRIVE_CLIENT_SECRET: Optional[str] = os.getenv("ONEDRIVE_CLIENT_SECRET")
    GOOGLE_DRIVE_API_KEY: Optional[str] = os.getenv("GOOGLE_DRIVE_API_KEY")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Session Configuration
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    
    @classmethod
    def validate_oauth_settings(cls) -> tuple:
        """Validate OAuth settings are complete"""
        errors = []
        
        if cls.GOOGLE_CLIENT_ID and not cls.GOOGLE_CLIENT_SECRET:
            errors.append("GOOGLE_CLIENT_SECRET required when GOOGLE_CLIENT_ID is set")
        
        if cls.GOOGLE_CLIENT_SECRET and not cls.GOOGLE_CLIENT_ID:
            errors.append("GOOGLE_CLIENT_ID required when GOOGLE_CLIENT_SECRET is set")
        
        if cls.MICROSOFT_CLIENT_ID and not cls.MICROSOFT_CLIENT_SECRET:
            errors.append("MICROSOFT_CLIENT_SECRET required when MICROSOFT_CLIENT_ID is set")
        
        if cls.MICROSOFT_CLIENT_SECRET and not cls.MICROSOFT_CLIENT_ID:
            errors.append("MICROSOFT_CLIENT_ID required when MICROSOFT_CLIENT_SECRET is set")
        
        return (len(errors) == 0, errors)
