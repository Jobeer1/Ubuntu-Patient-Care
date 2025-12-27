"""
SDOH Chat - FastAPI Integration
Add SDOH Chat routes to main FastAPI app
"""

from fastapi import FastAPI
from RIS-1.SDOH-chat.backend.routes.sdoh_auth import router as auth_router
from RIS-1.SDOH-chat.backend.routes.sdoh_messages import router as messages_router
from RIS-1.SDOH-chat.backend.routes.sdoh_contacts import router as contacts_router
from RIS-1.SDOH-chat.backend.routes.sdoh_groups import router as groups_router

def setup_sdoh_routes(app: FastAPI):
    """
    Setup SDOH Chat routes in FastAPI app
    
    Call this in main.py after creating the FastAPI app:
    
    from RIS-1.SDOH-chat.backend.integration import setup_sdoh_routes
    ...
    setup_sdoh_routes(app)
    """
    
    app.include_router(auth_router)
    app.include_router(messages_router)
    app.include_router(contacts_router)
    app.include_router(groups_router)
    
    print("✓ SDOH Chat routes registered")

# Static file mounting for frontend
def setup_sdoh_static(app: FastAPI):
    """
    Setup static files for SDOH Chat frontend
    
    Call this in main.py:
    
    from fastapi.staticfiles import StaticFiles
    from RIS-1.SDOH-chat.backend.integration import setup_sdoh_static
    ...
    setup_sdoh_static(app)
    """
    
    from fastapi.staticfiles import StaticFiles
    import os
    
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    
    # Mount at /sdoh
    app.mount('/sdoh', StaticFiles(directory=frontend_path, html=True), name='sdoh')
    
    print(f"✓ SDOH Chat frontend mounted at /sdoh")
