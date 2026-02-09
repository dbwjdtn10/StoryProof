import sys
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

DB_USER = "postgres"
DB_PASS = "1234!@#$"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "my_local_db"

encoded_pass = quote_plus(DB_PASS)
url = f"postgresql://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    engine = create_engine(url)
    with engine.connect() as conn:
        print("=== User List ===")
        result = conn.execute(text("SELECT id, email, username, is_active FROM users"))
        for row in result:
            print(f"ID: {row.id}, Email: {row.email}, Username: {row.username}, Active: {row.is_active}")
            
except Exception as e:
    print(f"Error: {e}")
