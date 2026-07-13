"""
데이터베이스 모델 정의
- SQLAlchemy ORM 모델
- User, Novel, Chapter, Analysis, ChatHistory 테이블
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Enum, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum


Base = declarative_base()


# ===== Enum 정의 =====

class AnalysisStatus(str, enum.Enum):
    """분석 상태"""
    PENDING = "pending"      # 대기 중
    PROCESSING = "processing"  # 처리 중
    COMPLETED = "completed"   # 완료
    FAILED = "failed"        # 실패


class StoryboardStatus(str, enum.Enum):
    """스토리보드 처리 상태"""
    PENDING = "pending"         # 대기 중
    PROCESSING = "processing"   # 처리 중 (청킹, 구조화, 임베딩)
    COMPLETED = "completed"     # 완료
    FAILED = "failed"           # 실패


class AnalysisType(str, enum.Enum):
    """분석 유형"""
    CHARACTER = "character"       # 캐릭터 분석
    PLOT = "plot"                # 플롯 분석
    STYLE = "style"              # 문체 분석
    OVERALL = "overall"          # 종합 분석
    CONSISTENCY = "consistency"  # 설정 파괴 분석
    PREDICTION = "prediction"    # 스토리 예측


# ===== 모델 정의 =====

class User(Base):
    """사용자 모델"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    user_mode = Column(String(50), default="writer", nullable=False)  # 'reader' or 'writer'
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # 관계
    novels = relationship("Novel", back_populates="author", cascade="all, delete-orphan")
    chat_histories = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"


class Novel(Base):
    """소설 모델"""
    __tablename__ = "novels"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    genre = Column(String(100), nullable=True)
    custom_prompt = Column(Text, nullable=True) # 사용자 정의 분석 프롬프트
    
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    is_public = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계
    author = relationship("User", back_populates="novels")
    chapters = relationship("Chapter", back_populates="novel", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="novel", cascade="all, delete-orphan")
    vector_documents = relationship("VectorDocument", back_populates="novel", cascade="all, delete-orphan")
    chat_histories = relationship("ChatHistory", back_populates="novel", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Novel(id={self.id}, title={self.title}, author_id={self.author_id})>"


class Chapter(Base):
    # ... (No changes needed for Chapter)
    __tablename__ = "chapters"
    
    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)

    chapter_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    
    word_count = Column(Integer, default=0)
    
    # 스토리보드 처리 상태
    storyboard_status = Column(String(50), default="PENDING")  # VARCHAR로 저장
    storyboard_progress = Column(Integer, default=0)  # 0-100
    storyboard_message = Column(String(255), nullable=True)  # 진행 메시지
    storyboard_error = Column(Text, nullable=True)    # 에러 메시지
    storyboard_completed_at = Column(DateTime(timezone=True), nullable=True)
    # 마지막 성공 처리 시점의 content SHA-256 해시. 재분석 요청 시 내용이
    # 바뀌지 않았으면 LLM 파이프라인 전체를 건너뛰기 위한 캐시 키 (비용 절감)
    storyboard_content_hash = Column(String(64), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계
    novel = relationship("Novel", back_populates="chapters")
    analyses = relationship("Analysis", back_populates="chapter", cascade="all, delete-orphan")
    vector_documents = relationship("VectorDocument", back_populates="chapter", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Chapter(id={self.id}, novel_id={self.novel_id}, chapter_number={self.chapter_number})>"


class Analysis(Base):
    """분석 결과 모델"""
    __tablename__ = "analyses"
    __table_args__ = (
        Index('ix_analysis_novel_chapter_type_status', 'novel_id', 'chapter_id', 'analysis_type', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True, index=True)

    analysis_type = Column(Enum(AnalysisType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    status = Column(Enum(AnalysisStatus, values_callable=lambda obj: [e.value for e in obj]), default=AnalysisStatus.PENDING)
    
    # 분석 결과 (JSONB 형태로 저장하여 유연한 쿼리 지원, SQLite 테스트 환경에서는 JSON)
    result = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # 분석에 사용된 입력 텍스트의 SHA-256 해시. 동일 텍스트 재분석 요청 시
    # 기존 COMPLETED 결과를 재사용하기 위한 캐시 키 (LLM 재호출 비용 절감)
    content_hash = Column(String(64), nullable=True, index=True)

    # 에러 정보
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 관계
    novel = relationship("Novel", back_populates="analyses")
    chapter = relationship("Chapter", back_populates="analyses")
    
    def __repr__(self):
        return f"<Analysis(id={self.id}, type={self.analysis_type}, status={self.status})>"


class ChatHistory(Base):
    """채팅 히스토리 모델"""
    __tablename__ = "chat_histories"
    __table_args__ = (
        Index('ix_chat_user_session', 'user_id', 'session_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=True)
    
    # 채팅방 ID (같은 세션의 대화를 그룹화)
    session_id = Column(String(100), index=True, nullable=False)
    
    # 메시지 내용
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    
    # 메타데이터
    meta_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    user = relationship("User", back_populates="chat_histories")
    novel = relationship("Novel", back_populates="chat_histories")
    
    def __repr__(self):
        return f"<ChatHistory(id={self.id}, session_id={self.session_id}, role={self.role})>"


class VectorDocument(Base):
    """벡터 문서 메타데이터 모델 (Pinecone과 연동)"""
    __tablename__ = "vector_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True, index=True)

    # Pinecone 벡터 ID
    vector_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # 문서 메타데이터
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    
    # 관계
    novel = relationship("Novel", back_populates="vector_documents")
    chapter = relationship("Chapter", back_populates="vector_documents")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<VectorDocument(id={self.id}, vector_id={self.vector_id})>"


class CharacterChatRoom(Base):
    """캐릭터 챗봇 채팅방 모델"""
    __tablename__ = "character_chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True, index=True)
    
    character_name = Column(String(100), nullable=False)
    persona_prompt = Column(Text, nullable=False) # 페르소나 시스템 프롬프트
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계
    user = relationship("User", backref="character_chat_rooms")
    novel = relationship("Novel", backref="character_chat_rooms")
    messages = relationship("CharacterChatMessage", back_populates="room", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CharacterChatRoom(id={self.id}, character={self.character_name})>"


class Partner(Base):
    """B2B 파트너 모델 (인터넷서점/웹소설 플랫폼 등 API 고객사)

    각 파트너는 전용 서비스 계정(User)을 가지며, 파트너 API로 생성된
    소설/분석 데이터는 모두 해당 서비스 계정 소유로 격리된다.
    """
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    contact_email = Column(String(255), nullable=False)

    plan = Column(String(50), default="starter", nullable=False)  # starter / pro / enterprise
    monthly_quota = Column(Integer, default=10000, nullable=False)  # 월간 API 호출 한도
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)

    # 콘텐츠 보안 계약 대응: "minimal"이면 원고 처리 완료 직후 원문 전체
    # (Chapter.content)를 삭제하고 벡터+청크 메타데이터만 보관한다.
    # "full"(기본값)은 기존과 동일하게 원문을 그대로 보관.
    content_retention_mode = Column(String(20), default="full", nullable=False)

    # 멀티 리전/전용 인스턴스(enterprise 플랜): "shared"(기본값)는 공용
    # 멀티테넌트 스택. 그 외 값은 이 파트너 전용으로 별도 프로비저닝된
    # 스택의 리전 식별자(예: "ap-northeast-2-dedicated")를 기록하는 메타데이터일
    # 뿐 — 실제 격리 배포는 docs/DEDICATED_DEPLOYMENT.md 런북에 따라 운영진이
    # 별도로 수행한다 (이 앱이 스스로 여러 리전에 자동 배포하지는 않음)
    deployment_region = Column(String(50), default="shared", nullable=False)
    dedicated_instance_url = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    # 웹훅 설정 (처리 완료 이벤트를 파트너 서버로 push, HMAC-SHA256 서명)
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(64), nullable=True)

    # 파트너 전용 서비스 계정 (기존 소유권 모델 재사용을 위한 테넌트 경계)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="partner")
    api_keys = relationship("PartnerApiKey", back_populates="partner", cascade="all, delete-orphan")
    usage_logs = relationship("ApiUsageLog", back_populates="partner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Partner(id={self.id}, name={self.name}, plan={self.plan})>"


class PartnerApiKey(Base):
    """파트너 API 키 모델 (원본 키는 저장하지 않고 SHA-256 해시만 저장)"""
    __tablename__ = "partner_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False, default="default")
    key_prefix = Column(String(20), nullable=False)  # 표시용 앞부분 (예: sp_live_a1b2)
    key_hash = Column(String(64), unique=True, index=True, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    partner = relationship("Partner", back_populates="api_keys")

    def __repr__(self):
        return f"<PartnerApiKey(id={self.id}, partner_id={self.partner_id}, prefix={self.key_prefix})>"


class ApiUsageLog(Base):
    """파트너 API 사용량 로그 (과금/정산 근거 데이터)"""
    __tablename__ = "api_usage_logs"
    __table_args__ = (
        Index('ix_usage_partner_created', 'partner_id', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False, index=True)
    api_key_id = Column(Integer, ForeignKey("partner_api_keys.id"), nullable=True)

    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False, default="POST")
    units = Column(Integer, nullable=False, default=1)  # 과금 단위 (예: 분석 챕터 수)
    status_code = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    partner = relationship("Partner", back_populates="usage_logs")

    def __repr__(self):
        return f"<ApiUsageLog(id={self.id}, partner_id={self.partner_id}, endpoint={self.endpoint})>"


class Invoice(Base):
    """파트너 월별 정산 인보이스 (api_usage_logs 집계 기반)"""
    __tablename__ = "invoices"
    __table_args__ = (
        Index('ix_invoice_partner_period', 'partner_id', 'period_year', 'period_month', unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False, index=True)

    period_year = Column(Integer, nullable=False)
    period_month = Column(Integer, nullable=False)  # 1-12

    plan = Column(String(50), nullable=False)  # 정산 시점의 플랜 (추후 플랜 변경과 무관하게 보존)
    total_units = Column(Integer, nullable=False, default=0)
    included_units = Column(Integer, nullable=False, default=0)  # 정산 시점의 monthly_quota
    overage_units = Column(Integer, nullable=False, default=0)

    base_fee_krw = Column(Integer, nullable=False, default=0)
    overage_unit_price_krw = Column(Integer, nullable=False, default=0)
    overage_amount_krw = Column(Integer, nullable=False, default=0)
    total_amount_krw = Column(Integer, nullable=False, default=0)

    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    partner = relationship("Partner", backref="invoices")

    def __repr__(self):
        return (f"<Invoice(id={self.id}, partner_id={self.partner_id}, "
                f"period={self.period_year}-{self.period_month:02d}, total={self.total_amount_krw})>")


class CharacterChatMessage(Base):
    """캐릭터 챗봇 메시지 모델"""
    __tablename__ = "character_chat_messages"
    __table_args__ = (
        Index('ix_char_msg_room_created', 'room_id', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("character_chat_rooms.id"), nullable=False, index=True)

    role = Column(String(20), nullable=False) # 'user', 'assistant'
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    room = relationship("CharacterChatRoom", back_populates="messages")
    
    def __repr__(self):
        return f"<CharacterChatMessage(id={self.id}, role={self.role})>"
