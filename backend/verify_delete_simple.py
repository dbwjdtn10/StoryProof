
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.db.session import SessionLocal
from backend.db.models import Novel, Chapter

def verify_delete_limit():
    db = SessionLocal()
    try:
        novel_id = 1
        chapter_number = 999
        
        # 1. Check if novel exists
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            print(f"Novel with ID {novel_id} not found. Cannot proceed.")
            return

        print(f"Using Novel ID: {novel.id}")

        # 2. Check if chapter exists (if so, delete it first to start clean)
        chapter = db.query(Chapter).filter(Chapter.novel_id == novel_id, Chapter.chapter_number == chapter_number).first()
        if chapter:
            print(f"Cleaning up existing test chapter {chapter.id}...")
            db.delete(chapter)
            db.commit()

        # 3. Create a test chapter
        print("Creating test chapter...")
        chapter = Chapter(
            novel_id=novel_id,
            chapter_number=chapter_number,
            title="Test Deletion Chapter",
            content="Test Content to be deleted.",
            word_count=5
        )
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
        print(f"Chapter created with ID: {chapter.id}")

        # 4. Delete the chapter
        print(f"Deleting chapter ID: {chapter.id}...")
        db.delete(chapter)
        db.commit()

        # 5. Verify chapter is gone
        # We need a new session or query to be sure
        check_chapter = db.query(Chapter).filter(Chapter.novel_id == novel_id, Chapter.chapter_number == chapter_number).first()
        
        if check_chapter:
             print(f"CRITICAL FAIL: Chapter still exists with ID {check_chapter.id}!")
        else:
             print("SUCCESS: Chapter deleted successfully from DB.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_delete_limit()
