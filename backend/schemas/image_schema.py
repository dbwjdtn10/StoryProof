"""이미지 생성 관련 Pydantic 스키마"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class ImageGenerationRequest(BaseModel):
    novel_id: int
    chapter_id: Optional[int] = None
    entity_type: Literal['character', 'item', 'location']
    entity_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    force_regenerate: bool = False


class ImageGenerationResponse(BaseModel):
    image_url: str
    refined_prompt: str
