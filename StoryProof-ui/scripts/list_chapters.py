from backend.db.session import SessionLocal
from backend.db.models import Novel, Chapter

db = SessionLocal()
novel_id = 1
chapters = db.query(Chapter).filter(Chapter.novel_id == novel_id).all()

print(f"Novel {novel_id} chapters:")
for ch in chapters:
    print(f"ID: {ch.id}, Num: {ch.chapter_number}, Title: {ch.title}, Status: {ch.storyboard_status}")
    
db.close()
