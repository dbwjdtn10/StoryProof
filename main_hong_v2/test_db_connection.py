import psycopg2
import os
from urllib.parse import quote_plus

# Manual DSN construction based on .env
# DATABASE_URL=postgresql://postgres:1234%21%40%23%24@localhost:5432/novels
# Password in .env is already URL encoded: 1234%21%40%23%24 which decodes to 1234!@#$
# psycopg2.connect expects a DSN string or keywords.

dsn = "postgresql://postgres:1234%21%40%23%24@localhost:5432/novels"

print(f"Attempting connection with DSN: {dsn}")

try:
    conn = psycopg2.connect(dsn)
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
    import traceback
    traceback.print_exc()

# Also try with explicit keywords to see if it changes anything
print("\nAttempting connection with keywords:")
try:
    conn = psycopg2.connect(
        dbname="novels",
        user="postgres",
        password="1234!@#$",
        host="localhost",
        port="5432"
    )
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection with keywords failed: {e}")
    traceback.print_exc()
