import requests
import sys
import os
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.session import SessionLocal
from backend.db.models import User, Novel
from backend.core.security import create_access_token, hash_password

BASE_URL = "http://localhost:8000/api/v1"

def setup_test_data():
    db = SessionLocal()
    try:
        # 1. Create User
        email = "upload_test@example.com"
        username = "uploaduser"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                username=username,
                hashed_password=hash_password("password123"),
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created user: {user.email} (ID: {user.id})")
        else:
            print(f"User exists: {user.email} (ID: {user.id})")
            
        # 2. Create Novel
        novel = db.query(Novel).filter(Novel.author_id == user.id).first()
        if not novel:
            novel = Novel(
                title="Test Novel for Upload",
                description="This is a test novel.",
                genre="Fantasy",
                author_id=user.id
            )
            db.add(novel)
            db.commit()
            db.refresh(novel)
            print(f"Created novel: {novel.title} (ID: {novel.id})")
        else:
            print(f"Novel exists: {novel.title} (ID: {novel.id})")
            
        return user.id, novel.id
    finally:
        db.close()

def verify_file_upload():
    user_id, novel_id = setup_test_data()
    
    # 3. Generate Token
    token = create_access_token({"sub": str(user_id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    # 4. Create dummy file
    file_content = "This is a test chapter content uploaded via backend verification."
    with open("test_chapter.txt", "w", encoding="utf-8") as f:
        f.write(file_content)
        
    # 5. Upload File
    url = f"{BASE_URL}/novels/{novel_id}/chapters/upload"
    files = {"file": ("test_chapter.txt", open("test_chapter.txt", "rb"), "text/plain")}
    data = {"chapter_number": 1, "title": "First Upload"}
    
    print(f"Uploading file to {url}...")
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 201:
            print("SUCCESS: File upload successful")
        elif response.status_code == 400 and "already exists" in response.text:
             print("SUCCESS: Chapter already exists request handled")
        else:
            print(f"FAILURE: File upload failed")
            # If 400 bad request, it might be due to existing chapter number, which is fine for verification if handled
            
    except Exception as e:
        print(f"FAILURE: Request error - {e}")
    finally:
        if os.path.exists("test_chapter.txt"):
            os.remove("test_chapter.txt")

if __name__ == "__main__":
    verify_file_upload()
