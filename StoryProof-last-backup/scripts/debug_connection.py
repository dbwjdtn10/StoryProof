import os
import sys
import psycopg2
import socket
from dotenv import load_dotenv

def check_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        try:
            s.connect((host, port))
            return True
        except:
            return False

def diagnose_connection():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        db_url = db_url.strip()
    
    # localhost -> 127.0.0.1 (Windows reliability)
    if "localhost" in db_url:
        db_url = db_url.replace("localhost", "127.0.0.1")
        
    print(f"Testing connection to: {db_url}")
    
    # Extract host and port
    try:
        parts = db_url.split("@")[1].split("/")[0]
        if ":" in parts:
            host, port = parts.split(":")
            port = int(port)
        else:
            host = parts
            port = 5432
    except:
        host = "127.0.0.1"
        port = 5432

    print(f"\n1. Checking if port {port} on {host} is open...")
    if check_port(host, port):
        print(f"✅ Port {port} is OPEN.")
    else:
        print(f"❌ Port {port} is CLOSED.")
        print("💡 Action: Start your PostgreSQL service (Docker or Local).")
        return

    print("\n2. Attempting to connect to PostgreSQL...")
    try:
        conn = psycopg2.connect(db_url)
        print("✅ Successfully connected!")
        conn.close()
    except Exception as e:
        print("\n❌ Connection Failed!")
        
        # Try to decode the error message manually if it's a UnicodeDecodeError
        try:
            print(f"Error Message: {e}")
        except UnicodeDecodeError:
            print("⚠️ Caught UnicodeDecodeError. This is because the error message is in Korean (CP949).")
            print("The real error is likely one of these:")
            print("- '데이터베이스 storyproof가 존재하지 않습니다' (Database 'storyproof' does not exist)")
            print("- '사용자 postgres의 패스워드 인증에 실패했습니다' (Password authentication failed)")
            
            # TRY TO CONNECT TO DEFAULT 'postgres' DB TO SEE IF PASSWORD IS CORRECT
            print("\n3. Testing connection to default 'postgres' database...")
            try:
                base_url = db_url.rsplit('/', 1)[0] + "/postgres"
                conn = psycopg2.connect(base_url)
                print("✅ Connected to 'postgres' DB. Password is CORRECT.")
                print("💡 Result: The database 'storyproof' (lowercase) does NOT exist.")
                print("\n🚀 ACTION: Please run the following SQL command in your database tool:")
                print("   CREATE DATABASE storyproof;")
                conn.close()
            except Exception as e2:
                print("❌ Failed to connect to 'postgres' DB as well.")
                print("💡 Result: Your password or username in .env is likely INCORRECT.")

if __name__ == "__main__":
    diagnose_connection()
