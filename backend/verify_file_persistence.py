import requests
import sys
import os
import random
import string
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.session import SessionLocal
from backend.db.models import User, Novel
from backend.core.security import create_access_token, hash_password

BASE_URL = "http://localhost:8001/api/v1"

def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters, k=length))

def setup_test_data():
    db = SessionLocal()
    try:
        # Create unique user/novel for this test run
        email = f"test_{random_string()}@example.com"
        username = f"user_{random_string()}"
        
        user = User(
            email=email,
            username=username,
            hashed_password=hash_password("password123"),
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        novel = Novel(
            title=f"Test Novel {random_string()}",
            description="Test novel for persistence check",
            genre="Fantasy",
            author_id=user.id
        )
        db.add(novel)
        db.commit()
        db.refresh(novel)
        
        return user.id, novel.id
    finally:
        db.close()

def verify_persistence():
    print("Starting persistence verification...")
    user_id, novel_id = setup_test_data()
    print(f"Setup complete. UserID: {user_id}, NovelID: {novel_id}")
    
    # Generate Token
    token = create_access_token({"sub": str(user_id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Verify empty chapters initially
    print("1. Verifying initial state...")
    try:
        response = requests.get(f"{BASE_URL}/novels/{novel_id}/chapters", headers=headers)
        if response.status_code != 200:
            print(f"FAILED: Could not fetch chapters. {response.status_code}")
            return
        chapters = response.json()
        if len(chapters) > 0:
            print(f"FAILED: Expected 0 chapters, found {len(chapters)}")
            return
        print("SUCCESS: Initial state correct (0 chapters).")
    except Exception as e:
        print(f"FAILED: Request error - {e}")
        return

    # 2. Upload a file
    print("2. Uploading file...")
    filename = "persist_test.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("This is content for persistence verification.")
        
    try:
        url = f"{BASE_URL}/novels/{novel_id}/chapters/upload"
        files = {"file": (filename, open(filename, "rb"), "text/plain")}
        data = {"chapter_number": 1, "title": "Persistence Chapter"}
        
        response = requests.post(url, headers=headers, files=files, data=data)
        if response.status_code != 201:
            print(f"FAILED: Upload failed. {response.status_code} {response.text}")
            return
        print("SUCCESS: File uploaded.")
    except Exception as e:
        print(f"FAILED: Upload exception - {e}")
        return
    finally:
        if os.path.exists(filename):
            try:
                # Close file handle usually handled by with open... but requests might hold it?
                # Actually 'files' argument in requests opens it.
                # Better to remove it.
                os.remove(filename)
            except:
                pass


    # 3. Verify persistence (fetch again)
    print("3. Verifying persistence (fetching chapters)...")
    try:
        response = requests.get(f"{BASE_URL}/novels/{novel_id}/chapters", headers=headers)
        if response.status_code != 200:
            print(f"FAILED: Could not fetch chapters. {response.status_code}")
            return
            
        chapters = response.json()
        if len(chapters) != 1:
            print(f"FAILED: Expected 1 chapter, found {len(chapters)}")
            print(chapters)
            return
            
        chapter = chapters[0]
        if chapter['title'] != "Persistence Chapter":
            print(f"FAILED: Chapter title mismatch. Got {chapter['title']}")
            return
            
        print(f"SUCCESS: Chapter '{chapter['title']}' persisted and retrieved.")
        print("VERIFICATION PASSED!")
        
    except Exception as e:
        print(f"FAILED: Verification exception - {e}")

if __name__ == "__main__":
    verify_persistence()
