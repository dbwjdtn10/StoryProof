import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.security import hash_password
from backend.db.models import User
from backend.core.config import settings

# Force the DB URL if needed, or rely on settings
# settings.DATABASE_URL might be loaded from .env
# For this script we will try to use the loaded settings first.

def reset_user_password(email, new_password):
    print(f"Connecting to DB at: {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"[FAIL] User with email {email} not found.")
            return

        print(f"User found: {user.username} (ID: {user.id})")
        
        # Hash the new password
        hashed_pw = hash_password(new_password)
        
        # Update user
        user.hashed_password = hashed_pw
        db.commit()
        print(f"[SUCCESS] Password for {email} has been reset to '{new_password}'.")
        
    except Exception as e:
        print(f"[ERROR] Error during password reset: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    target_email = "wndh8968@naver.com"
    target_password = "12341234"
    reset_user_password(target_email, target_password)
