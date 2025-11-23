"""Create admin user for Ubuntu Patient Care system"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models import User, UserContext
import bcrypt

def create_admin():
    """Create admin user"""
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == "admin@hospital.com").first()
        if existing_admin:
            print("❌ Admin user already exists!")
            print(f"Email: {existing_admin.email}")
            print(f"Role: {existing_admin.role}")
            return
        
        # Create admin user
        print("Creating admin user...")
        password = "admin123"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        admin = User(
            email="admin@hospital.com",
            password_hash=password_hash,
            name="System Administrator",
            role="Admin",
            active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        # Create context
        context = UserContext(
            user_id=admin.id,
            language="en-ZA",
            dictation_model="whisper-large-v3"
        )
        db.add(context)
        db.commit()
        
        print("\n✅ Admin user created successfully!")
        print("=" * 50)
        print(f"Email:    {admin.email}")
        print(f"Password: {password}")
        print(f"Role:     {admin.role}")
        print("=" * 50)
        print("\nYou can now login at: http://localhost:8080/login")
        print("\n⚠️  Remember to change the password after first login!")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
