import sys
import os
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# Try to connect using the configured URL with decoded password
# Original: postgres://postgres:1234%21%40%23%24@localhost:5432/my_local_db
# Decoded password: 1234!@#$

DB_USER = "postgres"
DB_PASS = "1234!@#$"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME_CONFIG = "my_local_db"
DB_NAME_DOCKER = "StoryProof"

encoded_pass = quote_plus(DB_PASS)

def check_connection(db_name):
    url = f"postgresql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{db_name}"
    print(f"Testing connection to: {db_name}...")
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"[OK] Success! Connected to {db_name}")
            
            # Check for users table
            try:
                result = conn.execute(text("SELECT count(*) FROM users"))
                count = result.scalar()
                print(f"   Found 'users' table with {count} records.")
            except Exception as e:
                print(f"   [WARN] Could not query 'users' table: {e}")
                
    except Exception as e:
        print(f"[FAIL] Failed to connect to {db_name}: {e}")

print("=== Database Connection Check ===")
check_connection(DB_NAME_CONFIG)
check_connection(DB_NAME_DOCKER)
check_connection("postgres") # Default DB
