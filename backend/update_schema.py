from sqlalchemy import create_engine, text
from backend.core.config import settings

def add_column():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='character_chat_rooms' AND column_name='chapter_id'"))
            if result.fetchone():
                print("Column 'chapter_id' already exists.")
                return

            print("Adding 'chapter_id' column to 'character_chat_rooms' table...")
            conn.execute(text("ALTER TABLE character_chat_rooms ADD COLUMN chapter_id INTEGER REFERENCES chapters(id)"))
            conn.commit()
            print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")

if __name__ == "__main__":
    add_column()
