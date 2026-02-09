import os
import psycopg2
from dotenv import load_dotenv

def ensure_db():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in .env")
        return

    # Extract connection info to connect to default 'postgres' database
    # Expected format: postgresql://user:pass@host:port/dbname
    try:
        base_url, db_name = db_url.rsplit('/', 1)
        postgres_url = f"{base_url}/postgres"
    except Exception as e:
        print(f"❌ Error parsing DATABASE_URL: {e}")
        return

    print(f"Connecting to 'postgres' database to check/create '{db_name}'...")
    
    conn = None
    try:
        # Connect to default postgres DB
        conn = psycopg2.connect(postgres_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cur.fetchone()
        
        if not exists:
            print(f"Creating database '{db_name}'...")
            cur.execute(f"CREATE DATABASE {db_name}")
            print(f"✅ Database '{db_name}' created successfully!")
        else:
            print(f"✅ Database '{db_name}' already exists.")
            
        cur.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 If you get a 'UnicodeDecodeError' or 'Connection Refused', please check your PostgreSQL password and service status.")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    ensure_db()
