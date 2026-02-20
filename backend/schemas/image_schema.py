"""이미지 생성 관련 Pydantic 스키마"""

from pydantic import BaseModel
from typing import Optional


class ImageGenerationRequest(BaseModel):
    novel_id: int
    chapter_id: Optional[int] = None
    entity_type: str  # 'characters', 'items', 'locations'
    entity_name: str
    description: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    image_url: str
    refined_prompt: str
