"""
파트너(B2B) API 스키마
- 원고 접수, 분석 요청, Q&A, 사용량 조회
- 파트너/API 키 관리 (관리자용)
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ===== 파트너 API (고객사용) =====

class ManuscriptChapterIn(BaseModel):
    """접수 원고의 개별 회차"""
    chapter_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class ManuscriptCreateRequest(BaseModel):
    """원고 접수 요청"""
    title: str = Field(..., min_length=1, max_length=255)
    genre: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    external_id: Optional[str] = Field(
        None, max_length=255,
        description="파트너 측 작품 식별자 (콜백/조회 시 매핑용)",
    )
    chapters: List[ManuscriptChapterIn] = Field(..., min_length=1)


class ManuscriptCreateResponse(BaseModel):
    manuscript_id: int
    external_id: Optional[str] = None
    chapter_ids: List[int]
    status: str = "processing"


class ChapterStatusOut(BaseModel):
    chapter_id: int
    chapter_number: int
    status: str
    progress: int
    error: Optional[str] = None


class ManuscriptStatusResponse(BaseModel):
    manuscript_id: int
    title: str
    ready: bool
    chapters: List[ChapterStatusOut]


class PartnerQARequest(BaseModel):
    """작품 내용 기반 Q&A (독자용 챗봇 등)"""
    question: str = Field(..., min_length=1, max_length=2000)
    chapter_id: Optional[int] = Field(
        None, description="지정 시 해당 회차까지의 내용만 사용 (스포일러 방지)"
    )


class PartnerQAResponse(BaseModel):
    answer: str
    found_context: bool
    similarity: float


class ConsistencyCheckRequest(BaseModel):
    """설정 일관성 검증 요청 (신규 회차 원고 vs 기존 설정)"""
    chapter_id: Optional[int] = Field(None, description="기존 회차 검증 시 지정")
    text: Optional[str] = Field(None, description="아직 등록 전인 신규 원고 텍스트")


class AsyncTaskResponse(BaseModel):
    task_id: str
    status: str = "PENDING"


class WidgetSessionRequest(BaseModel):
    """위젯 세션 토큰 발급 요청 (파트너 서버에서 호출)"""
    manuscript_id: int
    chapter_id: Optional[int] = Field(
        None, description="독자가 읽은 회차 — 지정 시 위젯이 이 회차까지만 답변 (스포일러 방지)"
    )
    ttl_minutes: int = Field(30, ge=1, le=1440, description="토큰 유효 시간 (분)")


class WidgetSessionResponse(BaseModel):
    token: str
    expires_in: int = Field(..., description="유효 시간 (초)")
    manuscript_id: int
    chapter_id: Optional[int] = None


class WidgetQARequest(BaseModel):
    """위젯 Q&A 요청 (브라우저에서 세션 토큰으로 호출)"""
    question: str = Field(..., min_length=1, max_length=2000)


class WidgetQAResponse(BaseModel):
    answer: str
    found_context: bool
    similarity: float


class WebhookConfigRequest(BaseModel):
    """웹훅 URL 등록 요청 (등록 시 서명용 secret이 새로 발급됨)"""
    url: str = Field(..., max_length=500, pattern=r"^https?://.+")


class WebhookConfigResponse(BaseModel):
    url: str
    secret: str = Field(..., description="HMAC-SHA256 서명 검증용 secret — 이 응답에서만 확인 가능")


class WebhookInfoResponse(BaseModel):
    url: Optional[str] = None
    configured: bool


class UsageSummaryResponse(BaseModel):
    partner_name: str
    plan: str
    monthly_quota: int
    used_this_month: int
    remaining: int


# ===== 파트너 관리 (관리자용) =====

class PartnerCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    contact_email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    plan: str = Field("starter", pattern="^(starter|pro|enterprise)$")
    monthly_quota: int = Field(10000, ge=1)
    rate_limit_per_minute: int = Field(60, ge=1)
    content_retention_mode: str = Field(
        "full", pattern="^(full|minimal)$",
        description="minimal: 원고 처리 완료 직후 원문 전체를 삭제하고 벡터+청크만 보관 (콘텐츠 보안 계약용)",
    )


class ApiKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PartnerOut(BaseModel):
    id: int
    name: str
    contact_email: str
    plan: str
    monthly_quota: int
    rate_limit_per_minute: int
    content_retention_mode: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PartnerCreateResponse(BaseModel):
    partner: PartnerOut
    api_key: str = Field(..., description="원본 API 키 — 이 응답에서만 확인 가능")


class ApiKeyIssueResponse(BaseModel):
    key_info: ApiKeyOut
    api_key: str = Field(..., description="원본 API 키 — 이 응답에서만 확인 가능")
