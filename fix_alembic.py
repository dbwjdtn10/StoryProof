from backend.db.session import engine
from sqlalchemy import text
from backend.core.config import settings

def fix_version():
    target_version = 'e15b603034e3'
    print(f"Forcing alembic_version to {target_version}...")
    
    with engine.connect() as conn:
        conn.execute(text(f"UPDATE alembic_version SET version_num = '{target_version}'"))
        conn.commit()
    
    print("Done.")

if __name__ == "__main__":
    fix_version()
