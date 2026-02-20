"""캐릭터 채팅 API 엔드포인트"""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import logging
from functools import partial
from datetime import datetime

from backend.db.session import get_db
from backend.db.models import Novel, Analysis, AnalysisType, CharacterChatRoom, CharacterChatMessage, VectorDocument
from backend.core.config import settings
from backend.services.chatbot_service import get_chatbot_service
from backend.services.character_chat_service import CharacterChatService
from backend.schemas.character_chat_schema import (
    CharacterChatRoomCreate, CharacterChatRoomUpdate, CharacterChatRoomResponse,
    CharacterChatMessageCreate, CharacterChatMessageResponse,
    PersonaGenerationRequest, PersonaGenerationResponse,
)

# Setup logger (must be before genai import attempt)
logger = logging.getLogger(__name__)

# Initialize Gemini Client
try:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
except ImportError:
    client = None
    logger.warning("Warning: google-genai not installed or configured.")



# --- Helper Functions ---

def extract_character_dialogues(analysis_data: dict, character_name: str, max_dialogues: int = 50) -> list:
    """
    Extract actual dialogue lines spoken by the character from scene data.
    Returns list of dialogue strings (up to max_dialogues).
    """
    dialogues = []
    scenes = analysis_data.get("scenes", [])

    logger.info(f"[DIALOGUE EXTRACTION] Extracting dialogues for character: {character_name}")
    logger.info(f"[DIALOGUE EXTRACTION] Total scenes to check: {len(scenes)}")

    for scene_idx, scene in enumerate(scenes):
        characters_in_scene = scene.get("characters", [])
        if character_name not in characters_in_scene:
            continue

        logger.debug(f"[DIALOGUE EXTRACTION] Scene {scene_idx}: Character found, extracting...")

        text = scene.get("original_text", "")
        if not text:
            continue

        lines = text.split('\n')
        for line in lines:
            stripped = line.strip()
            is_dialogue = (
                stripped.startswith('"') or
                stripped.startswith("'") or
                stripped.startswith('\u201c') or  # Korean opening quote
                stripped.startswith('\u300c') or
                stripped.startswith('\u2014')  # Em-dash dialogue
            )
            if is_dialogue and len(stripped) > 3:
                cleaned = stripped.strip('\u2014').strip()
                dialogues.append(cleaned)
                logger.debug(f"[DIALOGUE EXTRACTION] Found: {cleaned[:50]}...")
                if len(dialogues) >= max_dialogues:
                    logger.info(f"[DIALOGUE EXTRACTION] Reached max dialogues ({max_dialogues})")
                    return dialogues

    logger.info(f"[DIALOGUE EXTRACTION] Extracted {len(dialogues)} dialogues for {character_name}")
    return dialogues


def _fetch_analysis_for_character(
    db: Session, novel_id: int, chapter_id: Optional[int], character_name: str
):
    """분석 데이터 조회. 챕터별 분석 → 벡터 메타데이터 집계 → 글로벌 분석 순으로 시도."""
    query = db.query(Analysis).filter(
        Analysis.novel_id == novel_id,
        Analysis.status == "completed"
    )
    if chapter_id:
        query = query.filter(Analysis.chapter_id == chapter_id)

    analysis = query.order_by(desc(Analysis.created_at)).first()

    if not analysis and chapter_id:
        logger.info(f"[Persona] No Analysis found for chapter {chapter_id}. Aggregating from VectorDocument metadata...")
        vectors = db.query(VectorDocument).filter(
            VectorDocument.novel_id == novel_id,
            VectorDocument.chapter_id == chapter_id
        ).all()

        if vectors:
            aggregated_char = None
            for vec in vectors:
                meta = vec.metadata_json or {}
                for char in meta.get('characters', []):
                    c_name = char.get('name') if isinstance(char, dict) else char
                    if c_name != character_name:
                        continue
                    if not aggregated_char:
                        aggregated_char = {
                            "name": c_name,
                            "description": char.get('description', '') if isinstance(char, dict) else '',
                            "traits": char.get('traits', []) if isinstance(char, dict) else []
                        }
                    else:
                        new_traits = char.get('traits', []) if isinstance(char, dict) else []
                        for t in new_traits:
                            if t not in aggregated_char['traits']:
                                aggregated_char['traits'].append(t)
                        new_desc = char.get('description', '') if isinstance(char, dict) else ''
                        if len(new_desc) > len(aggregated_char['description']):
                            aggregated_char['description'] = new_desc

            if aggregated_char:
                class MockAnalysis:
                    def __init__(self, data, nid):
                        self.result = data
                        self.id = "mock_vector_aggregation"
                        self.novel_id = nid
                        self.analysis_type = "vector_aggregation"

                analysis = MockAnalysis({
                    "characters": [aggregated_char],
                    "summary": "Generated from Vector Metadata",
                    "mood": "Unknown"
                }, novel_id)
                logger.info(f"[Persona] Successfully aggregated data for '{character_name}' from {len(vectors)} scenes.")
            else:
                logger.warning(f"[Persona] Character '{character_name}' not found in chapter {chapter_id} vectors.")

    if not analysis or not getattr(analysis, 'result', None):
        if chapter_id:
            logger.warning(f"[Persona] Strict mode: No analysis found for chapter {chapter_id}. Aborting.")
            raise HTTPException(
                status_code=404,
                detail=f"No analysis or character data found for '{character_name}' in this chapter."
            )
        # Legacy fallback (Global)
        analysis = db.query(Analysis).filter(
            Analysis.novel_id == novel_id,
            Analysis.analysis_type == AnalysisType.CHARACTER,
            Analysis.status == "completed"
        ).order_by(desc(Analysis.created_at)).first()

    if analysis:
        logger.debug(f"[Persona] Found analysis ID: {analysis.id}, type: {analysis.analysis_type}")
    else:
        logger.warning(f"[Persona] NO ANALYSIS FOUND for novel_id={novel_id}")

    if not analysis or not analysis.result:
        raise HTTPException(
            status_code=404,
            detail="Analysis data not found for this novel. Please run analysis first."
        )

    return analysis


def _find_character_in_analysis(analysis, character_name: str) -> dict:
    """분석 결과에서 캐릭터 데이터 찾기 (정확 매칭 → 부분 매칭)."""
    data = analysis.result
    logger.debug(f"[Persona] Analysis type: {analysis.analysis_type}, data type: {type(data)}")

    characters_list = []
    if isinstance(data, dict):
        characters_list = data.get("characters", []) or data.get("character_analysis", []) or []
        logger.debug(f"[Persona] Characters list length: {len(characters_list)}")
    elif isinstance(data, list):
        characters_list = data

    def normalize_name(name: str) -> str:
        return name.replace(" ", "").lower() if name else ""

    target_norm = normalize_name(character_name)
    logger.debug(f"[Persona] Looking for normalized name: '{target_norm}'")

    # First pass: Exact match
    for char in characters_list:
        if not isinstance(char, dict):
            continue
        char_name = char.get("name") or char.get("character_name")
        if normalize_name(char_name) == target_norm:
            return char

    # Second pass: Partial match
    for char in characters_list:
        if not isinstance(char, dict):
            continue
        char_name = char.get("name") or char.get("character_name")
        char_name_norm = normalize_name(char_name)
        if target_norm in char_name_norm or char_name_norm in target_norm:
            logger.debug(f"[Persona] Found partial match: '{char_name}'")
            return char

    available_names = [
        char.get("name") or char.get("character_name")
        for char in characters_list[:10]
        if isinstance(char, dict) and (char.get("name") or char.get("character_name"))
    ]
    error_detail = f"Character '{character_name}' not found in analysis."
    if available_names:
        error_detail += f" Available characters: {', '.join(available_names)}"
    else:
        error_detail += " No characters found in analysis data."
    raise HTTPException(status_code=404, detail=error_detail)


def _build_persona_meta_prompt(
    character_data: dict, character_name: str, analysis_result: dict, dialogues: list
) -> str:
    """페르소나 생성을 위한 메타 프롬프트 구축."""
    relations_text = ""
    if "relationships" in analysis_result:
        rels = analysis_result["relationships"]
        char_rels = [
            r for r in rels
            if character_name in r.get("source", "") or character_name in r.get("target", "")
        ]
        if char_rels:
            relations_text = "\n" + "\n".join([
                f"- {r.get('target' if r.get('source') == character_name else 'source')}: "
                f"{r.get('relation')} ({r.get('description')})"
                for r in char_rels
            ])

    has_dialogues = bool(dialogues)
    if has_dialogues:
        dialogue_count = len(dialogues)
        dialogue_examples = f"\n\n[실제 대사 예시 (총 {dialogue_count}개)]"
        dialogue_examples += "\n" + "\n".join([f"{i+1}. {d}" for i, d in enumerate(dialogues)])
        dialogue_examples += (
            f"\n\n⚠️ 중요: 위 {dialogue_count}개의 실제 대사를 반드시 분석하라. "
            f"말투 패턴, 어미 사용 빈도, 문장 길이, 반복 표현을 통계적으로 추출하라."
        )
    else:
        logger.warning(f"[PERSONA] No dialogues found for {character_name}. Using general analysis only.")
        dialogue_examples = (
            "\n\n[알림: 이 캐릭터의 직접적인 대사를 찾을 수 없습니다. "
            "성격 설명과 특징만으로 말투를 추론하세요.]"
        )

    meta_prompt = f"""
너는 세계 최고의 캐릭터 프롬프트 엔지니어이다.
아래 웹소설 캐릭터의 데이터를 분석하여, 이 캐릭터가 되어 실시간 대화를 수행할 AI의 **'시스템 지침(System Instruction)'**을 작성하라.

[데이터 베이스]
- 이름: {character_data.get('name')}
- 핵심 성격: {character_data.get('description')}
- 주요 특징/태그: {', '.join(character_data.get('traits', []))}{relations_text}{dialogue_examples}

[시스템 지침 작성 가이드라인]
1. **1인칭 정체성**: "너는 ~이다"라고 정의하라. 캐릭터의 내면 심리와 가치관을 포함하라.

2. **말투의 물리적 규칙**:
   {'   - 🎯 위에 제공된 [실제 대사 예시]를 한 줄 한 줄 꼼꼼히 분석하라' if has_dialogues else '   - 성격 설명과 특징을 바탕으로 말투를 추론하라'}
   {'   - 대사에서 가장 자주 사용하는 어미를 추출하고 빈도를 계산 (예: ~어요 30%, ~다 20%)' if has_dialogues else '   - 캐릭터 성격에 맞는 어미를 설정 (예: 권위적이면 ~라/~다)'}
   {'   - 실제 대사의 평균 문장 길이를 측정 (짧음/중간/긺)' if has_dialogues else '   - 성격에 맞는 문장 길이 결정'}
   {'   - 대사에서 반복되는 감탄사, 접속사, 말버릇을 구체적으로 추출 (예: "그래", "음...")' if has_dialogues else '   - 캐릭터 특성에 맞는 감탄사/버릇 설정'}
   {'   - 대사에서 높임말/반말 비율을 정확히 계산하라' if has_dialogues else '   - 성격과 설정에 맞는 높임말/반말 비율 설정'}
   - 특정 문장 구조나 패턴이 있으면 기록하라

3. **대화 태도**:
   {'   - 실제 대사에서 나타나는 평균 감정 톤 분석 (공격적/친근함/무뚝뚝함/장난기/권위적)' if has_dialogues else '   - 성격 설명을 바탕으로 감정 톤 설정'}
   {'   - 대사의 질문 vs 진술 비율을 계산하라' if has_dialogues else '   - 캐릭터 특성에 맞는 질문/진술 비율 설정'}
   - 관계 데이터와 {'대사 톤' if has_dialogues else '성격 특징'}을 종합해 사용자 대하는 태도를 설정하라

4. **구어체 변환**: 소설 속 딱딱한 문어체가 아닌, 실제 대화나 메신저에서 쓸법한 자연스러운 어투를 명령하라. 실제 대사의 스타일을 그대로 반영하라.

5. **금기 사항**: 절대 기계적인 "무엇을 도와드릴까요?" 식의 답변을 하지 말고, 캐릭터답지 않은 친절함이나 비속어를 제한하라.

[출력 형식]
지침 내용만 출력할 것.
    """

    if has_dialogues:
        meta_prompt += """

6. **🎯 중요: 실제 대사 포함 필수**:
   - 위 [실제 대사 예시] 중에서 캐릭터의 말투를 가장 잘 보여주는 **10-15개를 선별**하여 생성할 시스템 지침에 포함시켜라
   - 생성하는 시스템 지침의 말투 규칙 설명 후에 반드시 다음 형식으로 추가하라:

   예시 형식:
   [참고할 실제 대사 예시]
   1. "대사 내용..."
   2. "대사 내용..."
   ...(10-15개)

   위 대사를 참고하여 대화할 때 유사한 어투와 패턴을 사용하라.
    """

    meta_prompt += """

[필수 포함 규칙]
생성된 시스템 프롬프트에는 반드시 다음 규칙들을 포함해야 한다:
"1. 너는 소설 설정에 기반한 캐릭터 역할극을 수행한다.
2. 사용자가 네 기억이나 제공된 맥락에 없는 것을 물으면, 모른다고 하거나 애매하게 피하라. 절대 사실을 지어내지 마라.
3. 사용자가 소설의 사실과 모순되는 말을 하면, 네 기억을 바탕으로 캐릭터답게 교정하라.
4. 답변은 자연스러운 대화를 위해 간결하게 유지하라. 특별히 긴 설명을 요청받지 않는 한, 장황하게 설명하거나 정보를 늘어놓지 마라. 일반적인 답변은 1~3문장을 목표로 하라."
    """

    return meta_prompt


def _fetch_character_bible(
    db: Session, novel_id: int, chapter_id: Optional[int], character_name: str
) -> str:
    """특정 캐릭터의 설정 정보(관계 포함)를 Analysis DB에서 추출."""
    query = db.query(Analysis).filter(
        Analysis.novel_id == novel_id,
        Analysis.analysis_type == AnalysisType.CHARACTER
    )
    if chapter_id:
        query = query.filter(Analysis.chapter_id == chapter_id)
    analysis = query.order_by(Analysis.updated_at.desc()).first()

    if not analysis or not analysis.result:
        return ""

    result = analysis.result
    parts = []

    # 해당 캐릭터 정보 추출
    for c in result.get('characters', []):
        if c.get('name') == character_name:
            traits = ", ".join(c.get('traits', [])[:5])
            desc = c.get('description', '')[:150]
            parts.append(f"[{character_name} 설정]\n성격/특징: {desc}\n주요 특성: {traits}")
            break

    # 해당 캐릭터 관련 관계 추출
    rel_lines = []
    for r in result.get('relationships', []):
        if character_name in (r.get('character1', ''), r.get('character2', '')):
            other = r.get('character2', '') if r.get('character1', '') == character_name else r.get('character1', '')
            rel_lines.append(f"- {other}: {r.get('description', '')[:80]}")
    if rel_lines:
        parts.append("[관계]\n" + "\n".join(rel_lines[:5]))

    return "\n\n".join(parts)[:400]


async def _perform_rag_search(
    db: Session, chatbot_service, room: CharacterChatRoom, message_content: str
) -> str:
    """RAG 검색으로 소설 관련 컨텍스트를 조회. 검색 실패 시 빈 문자열 반환."""
    if not chatbot_service or not chatbot_service.engine:
        return ""

    try:
        loop = asyncio.get_running_loop()
        chunks = await loop.run_in_executor(
            None,
            partial(
                chatbot_service.find_similar_chunks,
                question=message_content,
                top_k=3,
                novel_id=room.novel_id,   # novel_id를 직접 전달 (title 우회 조회 불필요)
                chapter_id=room.chapter_id
            )
        )
        if not chunks:
            return ""
        rag_context = "\n\n[Reference Scenes from Novel]:\n"
        for chunk in chunks:
            rag_context += f"Scene {chunk.get('scene_index', '?')}: {chunk['text'][:500]}...\n"
        return rag_context
    except Exception as e:
        logger.error(f"RAG Search failed: {e}")
        return ""


def _parse_self_check_response(ai_reply: str, room_id: int, character_name: str) -> str:
    """AI 응답에서 SELF_CHECK 파싱 및 로깅 후 정제된 메시지 반환."""
    logger.info(f"{'='*70}")
    logger.info(f"[AI RESPONSE DEBUG] Room {room_id} | Character: {character_name}")
    logger.info(f"Full response length: {len(ai_reply)} chars")
    logger.info(f"Contains [SELF_CHECK]: {'[SELF_CHECK]' in ai_reply}")
    logger.info(f"{'='*70}")

    if "[SELF_CHECK]" in ai_reply:
        parts = ai_reply.split("[SELF_CHECK]", 1)
        user_message = parts[0].strip()
        self_check_log = parts[1].strip()
        logger.info(f"[SELF-CHECK] Room {room_id} | Character: {character_name}")
        logger.info(f"[SELF-CHECK] {self_check_log}")
        return user_message

    logger.warning(f"[SELF-CHECK] ⚠️ LLM did not include self-check for Room {room_id}")
    logger.warning(f"[SELF-CHECK] Response length: {len(ai_reply)} chars")
    logger.warning(f"[SELF-CHECK] First 200 chars: {ai_reply[:200]}...")
    logger.warning(f"[SELF-CHECK] Tip: Check prompt or try regenerating persona")
    return ai_reply


# 캐릭터 챗 공통 프로토콜 지침 (send_message + send_message_stream 공유)
_CHAT_PROTOCOL = """

[채팅 프로토콜: 실시간 메신저 모드]
1. **간결성**: 한 번의 답장은 1~3문장 이내로 제한한다.
2. **기억 활용**: [기억 데이터]는 너의 실제 기억이다. "소설에 따르면" 같은 표현을 절대 쓰지 말고, 자신의 경험처럼 자연스럽게 언급하라.
3. **몰입 유지**: 사용자가 소설 설정과 맞지 않는 말을 하면, 캐릭터답게 반응하라.
4. **현장감**: 질문에만 답하지 말고, 가끔은 캐릭터의 현재 감정이나 상황을 툭 던져라.
5. **금지**: 설명조의 말투, 긴 문단, AI다운 정중함을 모두 버려라.
6. **절대 금지 — 사실 날조**: 소설 속 사건, 인물 관계, 장소, 대화 내용 등 구체적인 사실은 [기억 데이터]에 있는 내용만 말하라. [기억 데이터]에 "찾지 못했습니다"라고 나오거나 관련 내용이 없으면, 그 사실에 대해서는 반드시 "잘 기억이 안 나" 또는 화제 전환으로 대응하라. 네 학습 데이터나 상상으로 소설 내용을 지어내는 것은 절대 금지다.

[필수 출력 형식]
모든 답변은 다음 형식을 EXACTLY 따라야 한다:

<답변 내용을 그냥 여기에 쓴다. 태그 없이 그냥 문장만.>

[SELF_CHECK]
Checklist: X/5 | Confidence: Y.Y/5.0 | Notes: 간단 메모

중요:
- 답변에 [CHARACTER_MESSAGE]나 다른 태그를 절대 쓰지 마라
- 그냥 평범한 문장으로만 답변하라
- [SELF_CHECK] 이전에는 일반 텍스트만 있어야 한다
- [SELF_CHECK] 태그는 반드시 포함해야 한다

실제 출력 예시:
그래, 뭔가 필요해?

[SELF_CHECK]
Checklist: 5/5 | Confidence: 4.5/5.0 | Notes: 짧고 캐릭터답게

체크리스트 항목: (1)페르소나 유지 (2)말투 일관성 (3)설정 준수 (4)길이 적절 (5)RAG 자연 활용
    """


# --- Router ---
router = APIRouter()


@router.post("/generate-persona", response_model=PersonaGenerationResponse)
async def generate_persona(
    request: PersonaGenerationRequest,
    db: Session = Depends(get_db)
):
    """Generate a persona system prompt for a character using analysis data."""
    if not client:
        raise HTTPException(
            status_code=500,
            detail="LLM client not initialized. Check GOOGLE_API_KEY."
        )

    logger.info(f"===== GENERATE PERSONA REQUEST =====")
    logger.info(f"novel_id: {request.novel_id}, character_name: {request.character_name}")

    analysis = _fetch_analysis_for_character(db, request.novel_id, request.chapter_id, request.character_name)
    character_data = _find_character_in_analysis(analysis, request.character_name)
    dialogues = extract_character_dialogues(analysis.result, request.character_name, max_dialogues=50)
    meta_prompt = _build_persona_meta_prompt(character_data, request.character_name, analysis.result, dialogues)

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            partial(client.models.generate_content, model='gemini-2.5-flash', contents=meta_prompt)
        )
        persona_prompt = response.text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate persona: {str(e)}")

    return PersonaGenerationResponse(
        character_name=request.character_name,
        persona_prompt=persona_prompt
    )


@router.put("/rooms/{room_id}", response_model=CharacterChatRoomResponse)
async def update_room(
    room_id: int,
    room_update: CharacterChatRoomUpdate,
    db: Session = Depends(get_db)
):
    """Update a character chat room (e.g. persona prompt)."""
    return CharacterChatService.update_room(db, room_id, room_update.persona_prompt)


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    db: Session = Depends(get_db)
):
    """Delete a character chat room."""
    CharacterChatService.delete_room(db, room_id)


@router.post("/rooms", response_model=CharacterChatRoomResponse)
async def create_room(
    room_data: CharacterChatRoomCreate,
    db: Session = Depends(get_db)
):
    """Create a new character chat room."""
    return CharacterChatService.create_room(
        db,
        novel_id=room_data.novel_id,
        chapter_id=room_data.chapter_id,
        character_name=room_data.character_name,
        persona_prompt=room_data.persona_prompt,
    )


@router.get("/rooms", response_model=List[CharacterChatRoomResponse])
async def list_rooms(
    novel_id: int,
    chapter_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List chat rooms for a novel."""
    return CharacterChatService.list_rooms(db, novel_id, chapter_id)


@router.post("/rooms/{room_id}/messages", response_model=List[CharacterChatMessageResponse])
async def send_message(
    room_id: int,
    message: CharacterChatMessageCreate,
    db: Session = Depends(get_db)
):
    """Send a message to the character and get a response."""
    room = CharacterChatService.get_room(db, room_id)

    if not client:
        raise HTTPException(status_code=500, detail="LLM client not initialized")

    # 1. Save User Message
    user_msg = CharacterChatMessage(room_id=room.id, role="user", content=message.content)
    db.add(user_msg)
    db.commit()

    # 2. Fetch chat history
    history_records = db.query(CharacterChatMessage).filter(
        CharacterChatMessage.room_id == room.id
    ).order_by(CharacterChatMessage.created_at).all()

    # 3. RAG: Retrieve Context
    chatbot_service = get_chatbot_service()
    rag_context = await _perform_rag_search(db, chatbot_service, room, message.content)

    # 4. Build input with optional RAG context
    # 캐릭터 설정 바이블 조회 (Method C - 캐릭터 슬라이스)
    char_bible = _fetch_character_bible(db, room.novel_id, room.chapter_id, room.character_name)
    bible_prefix = f"### [캐릭터 설정] ###\n{char_bible}\n\n" if char_bible else ""

    # RAG 결과가 없어도 [기억 데이터] 블록을 항상 포함시켜,
    # LLM이 관련 소설 장면이 없다는 사실을 인지하도록 한다.
    memory_block = rag_context if rag_context else "[이 질문과 관련된 소설 장면을 찾지 못했습니다.]"
    input_text = f"""{bible_prefix}### [기억 데이터] ###
{memory_block}

### [사용자의 메시지] ###
{message.content}"""

    # Build system instruction
    system_instruction = room.persona_prompt + _CHAT_PROTOCOL

    # Build conversation history
    contents = []
    for msg in history_records:
        if msg.id == user_msg.id:
            continue  # 현재 메시지는 RAG 컨텍스트와 함께 아래서 추가
        role = "user" if msg.role == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))
    contents.append(types.Content(role="user", parts=[types.Part(text=input_text)]))

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            partial(
                client.models.generate_content,
                model='gemini-2.5-flash',
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=system_instruction)
            )
        )
        ai_reply = _parse_self_check_response(response.text.strip(), room_id, room.character_name)
    except Exception as e:
        ai_reply = "..."
        logger.error(f"Error generating chat response: {e}")

    # 5. Save AI Message
    ai_msg = CharacterChatMessage(room_id=room.id, role="assistant", content=ai_reply)
    db.add(ai_msg)
    room.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user_msg)
    db.refresh(ai_msg)

    return [user_msg, ai_msg]


@router.get("/rooms/{room_id}/messages", response_model=List[CharacterChatMessageResponse])
async def get_messages(
    room_id: int,
    db: Session = Depends(get_db)
):
    """Get message history for a room."""
    return CharacterChatService.get_messages(db, room_id)


@router.post("/rooms/{room_id}/messages/stream")
async def send_message_stream(
    room_id: int,
    message: CharacterChatMessageCreate,
    db: Session = Depends(get_db)
):
    """
    캐릭터 챗 스트리밍 응답 (SSE)

    이벤트 형식:
      data: {"type": "user_saved", "id": ..., "content": "...", "created_at": "..."}
      data: {"type": "token", "text": "..."}
      data: {"type": "done", "ai_id": ..., "ai_content": "...", "created_at": "..."}
    """
    room = CharacterChatService.get_room(db, room_id)

    if not client:
        raise HTTPException(status_code=500, detail="LLM client not initialized")

    # 1. Save User Message
    user_msg = CharacterChatMessage(room_id=room.id, role="user", content=message.content)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 2. Fetch chat history
    history_records = db.query(CharacterChatMessage).filter(
        CharacterChatMessage.room_id == room.id
    ).order_by(CharacterChatMessage.created_at).all()

    # 3. RAG + 바이블
    chatbot_service = get_chatbot_service()
    rag_context = await _perform_rag_search(db, chatbot_service, room, message.content)
    char_bible = _fetch_character_bible(db, room.novel_id, room.chapter_id, room.character_name)
    bible_prefix = f"### [캐릭터 설정] ###\n{char_bible}\n\n" if char_bible else ""
    memory_block = rag_context if rag_context else "[이 질문과 관련된 소설 장면을 찾지 못했습니다.]"
    input_text = f"""{bible_prefix}### [기억 데이터] ###
{memory_block}

### [사용자의 메시지] ###
{message.content}"""

    system_instruction = room.persona_prompt + _CHAT_PROTOCOL

    # 4. Build conversation history
    contents = []
    for msg in history_records:
        if msg.id == user_msg.id:
            continue
        role = "user" if msg.role == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))
    contents.append(types.Content(role="user", parts=[types.Part(text=input_text)]))

    loop = asyncio.get_running_loop()

    async def generate():
        # 유저 메시지 저장 완료 알림
        yield f"data: {json.dumps({'type': 'user_saved', 'id': user_msg.id, 'content': user_msg.content, 'created_at': user_msg.created_at.isoformat()})}\n\n"

        # Gemini 스트리밍: 동기 → 비동기 변환
        queue: asyncio.Queue = asyncio.Queue()

        def _run_stream():
            try:
                for chunk in client.models.generate_content_stream(
                    model='gemini-2.5-flash',
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=system_instruction)
                ):
                    if chunk.text:
                        asyncio.run_coroutine_threadsafe(queue.put(chunk.text), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(e), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop.run_in_executor(None, _run_stream)

        # [SELF_CHECK] 필터링하며 스트리밍
        full_text = ""
        sent_chars = 0

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                yield f"data: {json.dumps({'type': 'error', 'text': str(item)})}\n\n"
                break

            full_text += item
            check_pos = full_text.find("[SELF_CHECK]")

            if check_pos >= 0:
                # [SELF_CHECK] 발견: 그 이전 텍스트만 전송
                visible = full_text[:check_pos].rstrip()
                if len(visible) > sent_chars:
                    new_text = visible[sent_chars:]
                    if new_text:
                        yield f"data: {json.dumps({'type': 'token', 'text': new_text})}\n\n"
                break
            else:
                new_text = full_text[sent_chars:]
                if new_text:
                    yield f"data: {json.dumps({'type': 'token', 'text': new_text})}\n\n"
                sent_chars = len(full_text)

        # AI 메시지 저장
        parsed_reply = _parse_self_check_response(full_text.strip(), room_id, room.character_name)
        ai_msg = CharacterChatMessage(room_id=room.id, role="assistant", content=parsed_reply)
        db.add(ai_msg)
        room.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ai_msg)

        yield f"data: {json.dumps({'type': 'done', 'ai_id': ai_msg.id, 'ai_content': ai_msg.content, 'created_at': ai_msg.created_at.isoformat()})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
