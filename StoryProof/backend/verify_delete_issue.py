
import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.getcwd())

from backend.db.session import SessionLocal
from backend.db.models import Novel, Chapter, User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_delete_issue():
    db = SessionLocal()
    try:
        # 1. Create a test user if not exists
        user = db.query(User).filter(User.email == "test_delete@example.com").first()
        if not user:
            user = User(
                email="test_delete@example.com",
                username="test_delete",
                hashed_password=pwd_context.hash("password")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        print(f"User ID: {user.id}")

        # 2. Create a test novel
        novel = db.query(Novel).filter(Novel.title == "Delete Test Novel").first()
        if not novel:
            novel = Novel(
                title="Delete Test Novel",
                author_id=user.id
            )
            db.add(novel)
            db.commit()
            db.refresh(novel)
        print(f"Novel ID: {novel.id}")

        # 3. Create a chapter (simulating upload)
        chapter_num = 999
        chapter = db.query(Chapter).filter(Chapter.novel_id == novel.id, Chapter.chapter_number == chapter_num).first()
        if not chapter:
            chapter = Chapter(
                novel_id=novel.id,
                chapter_number=chapter_num,
                title="Test Chapter",
                content="Test Content",
                word_count=10
            )
            db.add(chapter)
            db.commit()
            db.refresh(chapter)
            print("Chapter created.")
        else:
            print("Chapter already exists.")

        # 4. Verify chapter exists
        exists = db.query(Chapter).filter(Chapter.novel_id == novel.id, Chapter.chapter_number == chapter_num).first()
        if not exists:
            print("Error: Chapter should exist.")
            return

        # 5. Delete the chapter
        print(f"Deleting chapter ID: {exists.id}")
        db.delete(exists)
        db.commit()

        # 6. Verify chapter is gone
        # Accessing exists.id might fail if we don't handle session correctly, but db.delete removes it from session.
        # check db again
        check = db.query(Chapter).filter(Chapter.novel_id == novel.id, Chapter.chapter_number == chapter_num).first()
        if check:
            print("CRITICAL FAIL: Chapter still exists after deletion!")
        else:
            print("SUCCESS: Chapter deleted from DB.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_delete_issue()
