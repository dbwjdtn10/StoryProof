"""
캐릭터 채팅 서비스 모듈
채팅방 및 메시지 CRUD 로직을 담당합니다.
"""

import logging
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.models import Novel, CharacterChatRoom, CharacterChatMessage

logger = logging.getLogger(__name__)


class CharacterChatService:
    """캐릭터 채팅방 및 메시지 관리 서비스"""

    @staticmethod
    def create_room(
        db: Session,
        novel_id: int,
        chapter_id: Optional[int],
        character_name: str,
        persona_prompt: str,
    ) -> CharacterChatRoom:
        """캐릭터 채팅방 생성"""
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="소설을 찾을 수 없습니다.")

        new_room = CharacterChatRoom(
            user_id=novel.author_id,
            novel_id=novel_id,
            chapter_id=chapter_id,
            character_name=character_name,
            persona_prompt=persona_prompt,
        )
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        return new_room

    @staticmethod
    def update_room(
        db: Session,
        room_id: int,
        persona_prompt: Optional[str],
    ) -> CharacterChatRoom:
        """채팅방 페르소나 프롬프트 수정"""
        room = db.query(CharacterChatRoom).filter(CharacterChatRoom.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")

        if persona_prompt is not None:
            room.persona_prompt = persona_prompt

        db.commit()
        db.refresh(room)
        return room

    @staticmethod
    def delete_room(db: Session, room_id: int) -> None:
        """채팅방 삭제"""
        room = db.query(CharacterChatRoom).filter(CharacterChatRoom.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")

        db.delete(room)
        db.commit()

    @staticmethod
    def list_rooms(
        db: Session,
        novel_id: int,
        chapter_id: Optional[int] = None,
    ) -> List[CharacterChatRoom]:
        """소설의 채팅방 목록 조회"""
        query = db.query(CharacterChatRoom).filter(CharacterChatRoom.novel_id == novel_id)
        if chapter_id:
            query = query.filter(CharacterChatRoom.chapter_id == chapter_id)
        return query.order_by(desc(CharacterChatRoom.updated_at)).all()

    @staticmethod
    def get_messages(db: Session, room_id: int) -> List[CharacterChatMessage]:
        """채팅방 메시지 목록 조회"""
        return (
            db.query(CharacterChatMessage)
            .filter(CharacterChatMessage.room_id == room_id)
            .order_by(CharacterChatMessage.created_at)
            .all()
        )

    @staticmethod
    def get_room(db: Session, room_id: int) -> CharacterChatRoom:
        """채팅방 단건 조회 (없으면 404)"""
        room = db.query(CharacterChatRoom).filter(CharacterChatRoom.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")
        return room
