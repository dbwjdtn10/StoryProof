import os
import psycopg2
from dotenv import load_dotenv

def reveal():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found")
        return
    
    # Try to connect and catch the raw error message
    print(f"Attempting to connect to: {db_url}")
    try:
        conn = psycopg2.connect(db_url)
        print("Connection successful!")
        conn.close()
    except Exception as e:
        print("\n--- REAL ERROR REVEALED ---")
        # psycopg2 errors often have a 'pgerror' attribute which is bytes or a string that failed to decode
        if hasattr(e, 'cursor') and e.cursor and hasattr(e.cursor, 'statusmessage'):
             print(f"Status: {e.cursor.statusmessage}")
        
        # We try to manually trigger the error and catch the bytes if possible, 
        # but the easiest way is to try decoding the string representation's failed bytes if we could
        # However, Python's str(e) already failed.
        
        print("Since I cannot see the hidden Korean text directly through your console's UTF-8 limit,")
        print("I will test the two most likely scenarios:")
        
        print("\n1. Testing if the password 'postgres' is correct...")
        base_url = db_url.rsplit('/', 1)[0] + "/postgres"
        try:
            conn = psycopg2.connect(base_url)
            print("   result: ✅ Password IS correct. The server is responding.")
            print("   conclusion: 🚀 The database 'storyproof' (lowercase) is MISSING.")
            print("   FIX: Run 'CREATE DATABASE storyproof;' in your DB tool.")
            conn.close()
        except Exception as e2:
            print("   result: ❌ Connection to 'postgres' failed too.")
            print("   conclusion: 🔑 Your password ('postgres') is likely WRONG, or the server blocked the connection.")
            print("   FIX: Check your PostgreSQL password and update .env")

if __name__ == "__main__":
    reveal()
