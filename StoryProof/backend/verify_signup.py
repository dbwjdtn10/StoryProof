import requests
import time
import sys

BASE_URL = "http://localhost:8000/api/v1"

def verify_signup():
    print("Checking server health...")
    # Wait for server
    server_up = False
    for i in range(30):
        try:
            resp = requests.get("http://localhost:8000/health")
            if resp.status_code == 200:
                server_up = True
                print("Server is up!")
                break
        except:
            pass
        time.sleep(1)
        print("Waiting for server...")
    
    if not server_up:
        print("FAILURE: Server did not start")
        sys.exit(1)
    
    # Register
    print("Attempting to register user...")
    payload = {
        "email": "test_signup@example.com",
        "username": "testsignupuser",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 201:
            print("SUCCESS: Signup successful")
        elif response.status_code == 400 and "already registered" in response.text:
            print("SUCCESS: User already exists (idempotent check)")
        else:
            print("FAILURE: Signup failed with unexpected status code")
            sys.exit(1)
            
    except Exception as e:
        print(f"FAILURE: Request failed - {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_signup()
