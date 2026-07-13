
import sys
import os
from unittest.mock import MagicMock, patch

# Add path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# 참고: 예전에는 여기서 sys.modules['sqlalchemy.dialects.postgresql']와
# sys.modules['backend.db.session']을 이 파일의 import 시점에 영구 교체했음.
# 이는 pytest 프로세스 전역에 남아 이후 로드되는 다른 테스트 파일의
# get_db 의존성 주입을 깨뜨리는 테스트 오염 버그였다 (2026-07-13 발견).
# Analysis.result 컬럼이 이미 JSONB().with_variant(JSON(), "sqlite")로
# SQLite를 지원하고, backend.db.session import 자체는 실제 DB에 연결하지
# 않으므로(지연 연결) 두 mock 모두 더 이상 필요하지 않아 제거함.

# 모델과 엔드포인트 임포트
from backend.db.models import Base, CharacterChatRoom, User, Novel
from backend.api.v1.endpoints.character_chat import list_rooms, send_message, CharacterChatMessageCreate

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestFileScopedChat(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Setup in-memory SQLite DB
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        
        # Create Dummy Data
        # User needs to be consistent with auth dependency if strictly enforced, 
        # but for unit testing internal functions we just need DB data.
        self.user = User(email="test@test.com", username="test", hashed_password="pw", user_mode="writer")
        self.db.add(self.user)
        self.novel = Novel(title="Test Novel", author_id=1)
        self.db.add(self.novel)
        self.chapter1 = MagicMock(id=1) # Models might not need actual Chapter persistence if valid foreign keys not enforced by sqlite default
        self.chapter2 = MagicMock(id=2)
        
        self.db.commit()
        
        # Create Rooms
        self.room1 = CharacterChatRoom(
            user_id=1, novel_id=1, chapter_id=1, character_name="Alice", persona_prompt="You are Alice"
        )
        self.room2 = CharacterChatRoom(
            user_id=1, novel_id=1, chapter_id=2, character_name="Peter", persona_prompt="You are Peter"
        )
        self.room3 = CharacterChatRoom(
            user_id=1, novel_id=1, chapter_id=None, character_name="Narrator", persona_prompt="You are Narrator"
        )
        self.db.add_all([self.room1, self.room2, self.room3])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    async def test_list_rooms_filtering(self):
        # Test 1: Filter by Chapter 1
        rooms_ch1 = await list_rooms(novel_id=1, chapter_id=1, db=self.db)
        self.assertEqual(len(rooms_ch1), 1)
        self.assertEqual(rooms_ch1[0].character_name, "Alice")
        
        # Test 2: Filter by Chapter 2
        rooms_ch2 = await list_rooms(novel_id=1, chapter_id=2, db=self.db)
        self.assertEqual(len(rooms_ch2), 1)
        self.assertEqual(rooms_ch2[0].character_name, "Peter")
        
        # Test 3: No Filter (should return all? OR depending on logic)
        # Current logic: query = ...
        # if chapter_id: query = query.filter(...)
        # So filter(None) does nothing, returns all
        rooms_all = await list_rooms(novel_id=1, chapter_id=None, db=self.db)
        self.assertEqual(len(rooms_all), 3)

    @patch('backend.api.v1.endpoints.character_chat.get_chatbot_service')
    # @patch('backend.api.v1.endpoints.character_chat.client') # We mocked session, but client is imported from elsewhere?
    # In endpoint: `from backend.services.chatbot_service import get_chatbot_service`
    async def test_send_message_context(self, mock_get_service):
        # Setup Mock Service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.find_similar_chunks.return_value = []
        mock_service.ask.return_value = {
            "answer": "Hello there!", 
            "source": None, 
            "similarity": 0.0, 
            "found_context": False
        }
        
        # We need to patch the `client` in chatbot service or mock `ask` method.
        # Since endpoint calls `chatbot_service.ask` (wait, does it?), let's check.
        # The endpoint code calls `chatbot_service.find_similar_chunks` explicitly in my previous view? 
        # Or does it use `chatbot_service.ask`?
        # Let's check `character_chat.py` content again.
        # It calls `chatbot_service.find_similar_chunks` and then `chatbot_service.generate_answer` OR generic logic.
        # In my view of `character_chat.py`, it had:
        # chunks = chatbot_service.find_similar_chunks(...)
        # So mocking find_similar_chunks is correct.
        
        # Act: Send message to Room 1 (Chapter 1)
        # 주의: 5자 이하 단순 메시지는 RAG를 건너뛰므로 (_is_simple_message)
        # 검색이 실제로 수행되도록 충분히 긴 질문을 사용한다.
        msg_create = CharacterChatMessageCreate(content="What happened in the forest yesterday?")
        await send_message(room_id=self.room1.id, message=msg_create, db=self.db)
        
        # Assert: Check if chapter_id was passed to finding chunks
        call_args = mock_service.find_similar_chunks.call_args
        self.assertIsNotNone(call_args)
        _, kwargs = call_args
        self.assertEqual(kwargs.get('chapter_id'), 1)

        # Act: Send message to Room 2 (Chapter 2)
        await send_message(room_id=self.room2.id, message=msg_create, db=self.db)
        
        # Assert: Check if chapter_id=2 was passed
        call_args = mock_service.find_similar_chunks.call_args
        _, kwargs = call_args
        self.assertEqual(kwargs.get('chapter_id'), 2)

if __name__ == '__main__':
    unittest.main()
