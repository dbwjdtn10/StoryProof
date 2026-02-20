"""캐릭터 채팅 관련 Pydantic 스키마"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CharacterChatRoomCreate(BaseModel):
    novel_id: int
    chapter_id: Optional[int] = None
    character_name: str
    persona_prompt: str


class CharacterChatRoomUpdate(BaseModel):
    persona_prompt: Optional[str] = None


class CharacterChatRoomResponse(BaseModel):
    id: int
    user_id: int
    novel_id: int
    chapter_id: Optional[int]
    character_name: str
    persona_prompt: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CharacterChatMessageCreate(BaseModel):
    content: str


class CharacterChatMessageResponse(BaseModel):
    id: int
    room_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class PersonaGenerationRequest(BaseModel):
    novel_id: int
    chapter_id: Optional[int] = None
    character_name: str


class PersonaGenerationResponse(BaseModel):
    character_name: str
    persona_prompt: str
