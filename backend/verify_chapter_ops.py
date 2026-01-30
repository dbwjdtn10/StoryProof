
import requests
import os

BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_EMAIL = "test_ops@example.com"
TEST_PASSWORD = "password123"

def verify_chapter_ops():
    # 1. Login/Signup
    print("1. Authenticating...")
    auth_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    try:
        # Try login first
        resp = requests.post(f"{BASE_URL}/auth/login", json=auth_data)
        if resp.status_code != 200:
            # Try register if login fails
            register_data = {**auth_data, "username": "TestOpsUser"}
            resp = requests.post(f"{BASE_URL}/auth/register", json=register_data)
            assert resp.status_code == 201, f"Registration failed: {resp.text}"
            # Login again
            resp = requests.post(f"{BASE_URL}/auth/login", json=auth_data)
            
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("   Authentication successful.")
        
        # 2. Get/Create Novel
        print("2. Getting Novel...")
        resp = requests.get(f"{BASE_URL}/novels/", headers=headers)
        assert resp.status_code == 200
        novels = resp.json()["novels"]
        
        if not novels:
            print("   Creating new novel...")
            novel_data = {"title": "Test Ops Novel", "description": "For testing chapter ops"}
            resp = requests.post(f"{BASE_URL}/novels/", json=novel_data, headers=headers)
            assert resp.status_code == 201
            novel_id = resp.json()["id"]
        else:
            novel_id = novels[0]["id"]
        print(f"   Novel ID: {novel_id}")
            
        # 3. Upload Chapter
        print("3. Uploading Chapter...")
        content = "This is the content of the testing chapter used for verification."
        files = {
            'file': ('test_chapter.txt', content, 'text/plain')
        }
        data = {
            'chapter_number': 999,
            'title': 'Test Verification Chapter'
        }
        
        # Upload
        resp = requests.post(f"{BASE_URL}/novels/{novel_id}/chapters/upload", headers=headers, files=files, data=data)
        
        # If conflicts, maybe delete it first? Or expect error?
        if resp.status_code == 400 and "이미 존재하는" in resp.text:
            print("   Chapter 999 already exists. Finding its ID...")
            # Fetch chapters to find it
            resp = requests.get(f"{BASE_URL}/novels/{novel_id}/chapters", headers=headers)
            chapters = resp.json()
            target_chapter = next((c for c in chapters if c['chapter_number'] == 999), None)
            if target_chapter:
                chapter_id = target_chapter['id']
                print(f"   Found existing chapter ID: {chapter_id}")
                # Delete it to start clean
                del_resp = requests.delete(f"{BASE_URL}/novels/{novel_id}/chapters/{chapter_id}", headers=headers)
                print(f"   Delete request status: {del_resp.status_code}")
                assert del_resp.status_code == 204, f"Delete failed during cleanup: {del_resp.text}"
                print("   Deleted existing chapter to verify clean slate.")
                # Retry upload
                resp = requests.post(f"{BASE_URL}/novels/{novel_id}/chapters/upload", headers=headers, files={'file': ('test_chapter.txt', content, 'text/plain')}, data=data)
        
        assert resp.status_code == 201, f"Upload failed: {resp.text}"
        chapter_id = resp.json()["id"]
        print(f"   Chapter uploaded. ID: {chapter_id}")
        
        # 4. Get Chapter Content (Verify Fix)
        print("4. Verifying Get Chapter (Content retrieval)...")
        resp = requests.get(f"{BASE_URL}/novels/{novel_id}/chapters/{chapter_id}", headers=headers)
        assert resp.status_code == 200, f"Get chapter failed: {resp.text}"
        fetched_content = resp.json()["content"]
        assert fetched_content == content, "Content mismatch!"
        print("   Success! fetching chapter content works.")
        
        # 5. Delete Chapter (Verify User Request)
        print("5. Verifying Delete Chapter...")
        resp = requests.delete(f"{BASE_URL}/novels/{novel_id}/chapters/{chapter_id}", headers=headers)
        assert resp.status_code == 204, f"Delete failed: {resp.text}"
        print("   Delete request successful (204).")
        
        # 6. Verify Deletion
        print("6. Confirming Deletion...")
        resp = requests.get(f"{BASE_URL}/novels/{novel_id}/chapters/{chapter_id}", headers=headers)
        assert resp.status_code == 404, "Chapter should be 404 after deletion"
        print("   Success! Chapter is gone.")
        
        print("\nALL VERIFICATION CHECKS PASSED.")
        
    except Exception as e:
        print(f"\nFAILED: {str(e)}")
        # Print full traceback if needed
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_chapter_ops()
