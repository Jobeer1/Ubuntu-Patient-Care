"""
SDOH Chat - Main Integration Entry Point
Use this to setup SDOH Chat in your FastAPI application
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

def integrate_sdoh_chat(app: FastAPI):
    """
    Complete SDOH Chat integration in one function
    
    Usage in main.py:
    ```python
    from RIS-1.SDOH_chat.backend import integrate_sdoh_chat
    
    # After creating FastAPI app
    integrate_sdoh_chat(app)
    ```
    """
    
    print("\n" + "="*50)
    print("  SDOH Chat - Integration Started")
    print("="*50 + "\n")
    
    # 1. Initialize database
    print("✓ Initializing database...")
    from RIS-1.SDOH_chat.backend.db import init_db
    init_db()
    
    # 2. Setup routes
    print("✓ Setting up API routes...")
    from RIS-1.SDOH_chat.backend.routes.sdoh_auth import router as auth_router
    from RIS-1.SDOH_chat.backend.routes.sdoh_messages import router as messages_router
    from RIS-1.SDOH_chat.backend.routes.sdoh_contacts import router as contacts_router
    from RIS-1.SDOH_chat.backend.routes.sdoh_groups import router as groups_router
    
    app.include_router(auth_router)
    app.include_router(messages_router)
    app.include_router(contacts_router)
    app.include_router(groups_router)
    
    # 3. Mount frontend
    print("✓ Mounting frontend files...")
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    app.mount('/sdoh', StaticFiles(directory=frontend_path, html=True), name='sdoh')
    
    # 4. CORS (if not already configured)
    print("✓ Ensuring CORS is configured...")
    # Note: You should already have CORS middleware from existing app
    # This is just for reference
    try:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    except:
        pass  # CORS likely already configured
    
    print("\n" + "="*50)
    print("  SDOH Chat Ready!")
    print("  "
    print("  Access at: http://localhost:5000/sdoh/index.html")
    print("="*50 + "\n")


if __name__ == '__main__':
    # Test integration
    from fastapi import FastAPI
    
    app = FastAPI()
    integrate_sdoh_chat(app)
    
    print("\n✓ Integration test successful!")
    print("Ready to deploy in main application.")
