from backend.db.session import SessionLocal
from backend.db.models import Novel, Chapter

db = SessionLocal()
chapters = db.query(Chapter).all()
novels = db.query(Novel).all()

print(f"Total Novels: {len(novels)}")
for n in novels:
    print(f"Novel ID: {n.id}, Title: {n.title}")

print(f"\nTotal Chapters: {len(chapters)}")
for ch in chapters:
    print(f"ID: {ch.id}, NovelID: {ch.novel_id}, Num: {ch.chapter_number}, Status: {ch.storyboard_status}")
    
db.close()
