"""Setup database with initial data"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine, SessionLocal
from app.models import Base, User, Role, UserContext
import json

def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created")

def seed_roles():
    """Seed default roles using RBAC service"""
    db = SessionLocal()
    try:
        print("Seeding roles...")
        from app.services.rbac_service import RBACService
        RBACService.initialize_default_roles(db)
        print("✓ Roles seeded")
    finally:
        db.close()

def seed_users():
    """Seed default users"""
    db = SessionLocal()
    try:
        print("Seeding default users...")
        
        users_data = [
            {
                "email": "admin@clinic.org",
                "name": "System Administrator",
                "role": "Admin",
                "hpcsa_number": None
            },
            {
                "email": "radiologist@clinic.org",
                "name": "Dr. John Smith",
                "role": "Radiologist",
                "hpcsa_number": "MP0123456"
            },
            {
                "email": "tech@clinic.org",
                "name": "Jane Technician",
                "role": "Technician",
                "hpcsa_number": None
            }
        ]
        
        for user_data in users_data:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing:
                user = User(**user_data)
                db.add(user)
                db.flush()
                
                # Create default context
                context = UserContext(
                    user_id=user.id,
                    language="en-ZA",
                    dictation_model="whisper-large-v3"
                )
                db.add(context)
        
        db.commit()
        print("✓ Default users created")
        print("\nDefault users:")
        print("  - admin@clinic.org (Admin)")
        print("  - radiologist@clinic.org (Radiologist)")
        print("  - tech@clinic.org (Technician)")
    finally:
        db.close()

def main():
    """Main setup function"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║           MCP Server Database Setup                       ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    create_tables()
    seed_roles()
    seed_users()
    
    print("""
    ✓ Database setup complete!
    
    Next steps:
    1. Configure .env file with OAuth credentials
    2. Run: python run.py
    3. Access: http://localhost:8080
    """)

if __name__ == "__main__":
    main()
