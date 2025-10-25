"""Run MCP Server"""
import uvicorn
from config.settings import settings

if __name__ == "__main__":
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║           MCP Server - SSO Gateway                        ║
    ║           Ubuntu Patient Care System                      ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    
    🚀 Starting server...
    📍 URL: http://{settings.MCP_HOST}:{settings.MCP_PORT}
    📚 API Docs: http://{settings.MCP_HOST}:{settings.MCP_PORT}/docs
    🔐 SSO Providers: Google, Microsoft
    
    Press CTRL+C to stop
    """)
    
    uvicorn.run(
        "app.main:app",
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
