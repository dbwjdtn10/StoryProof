
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import json
import logging
from pydantic import BaseModel
from datetime import datetime

from backend.db.session import get_db
from backend.db.models import Novel, Analysis, AnalysisType, CharacterChatRoom, CharacterChatMessage
from backend.core.config import settings
from backend.services.chatbot_service import get_chatbot_service

# Initialize Gemini Client
try:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
except ImportError:
    client = None
    print("Warning: google-genai not installed or configured.")

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Schemas ---
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
        # Check if character appears in this scene
        characters_in_scene = scene.get("characters", [])
        if character_name not in characters_in_scene:
            continue
            
        logger.debug(f"[DIALOGUE EXTRACTION] Scene {scene_idx}: Character found, extracting...")
        
        # Extract dialogue from original_text
        text = scene.get("original_text", "")
        if not text:
            continue
            
        lines = text.split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            # Improved dialogue detection:
            # 1. Lines starting with quotes (English or Korean)
            # 2. Lines with em-dash dialogue format (— dialogue)
            # 3. Lines with 「」brackets (Japanese-style quotes)
            is_dialogue = (
                stripped.startswith('"') or 
                stripped.startswith("'") or 
                stripped.startswith('“') or  # Korean opening quote
                stripped.startswith('「') or
                stripped.startswith('—')  # Em-dash dialogue
            )
            
            if is_dialogue and len(stripped) > 3:  # Filter out very short lines
                # Clean up the dialogue
                cleaned = stripped.strip('—').strip()
                dialogues.append(cleaned)
                logger.debug(f"[DIALOGUE EXTRACTION] Found: {cleaned[:50]}...")
                
                if len(dialogues) >= max_dialogues:
                    logger.info(f"[DIALOGUE EXTRACTION] Reached max dialogues ({max_dialogues})")
                    return dialogues
    
    logger.info(f"[DIALOGUE EXTRACTION] Extracted {len(dialogues)} dialogues for {character_name}")
    return dialogues

# --- Router ---
router = APIRouter()

@router.post("/generate-persona", response_model=PersonaGenerationResponse)
async def generate_persona(
    request: PersonaGenerationRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a persona system prompt for a character using analysis data.
    """
    if not client:
        raise HTTPException(
            status_code=500,
            detail="LLM client not initialized. Check GOOGLE_API_KEY."
        )

    # Debug logging - Track incoming request
    print(f"\n[DEBUG] ===== GENERATE PERSONA REQUEST =====")
    print(f"[DEBUG] Requested novel_id: {request.novel_id}")
    print(f"[DEBUG] Requested character_name: {request.character_name}")

    # Fetch Analysis
    # Prioritize Chapter-specific analysis if chapter_id is provided
    query = db.query(Analysis).filter(
        Analysis.novel_id == request.novel_id,
        Analysis.status == "completed"
    )
    
    if request.chapter_id:
        # Try to find analysis specifically for this chapter (Character or Overall)
        # We might need to be careful if AnalysisType.CHARACTER is used for single chapter
        # For now, let's filter by chapter_id if it exists in the Analysis table
        query = query.filter(Analysis.chapter_id == request.chapter_id)
    else:
        # Fallback to Global Analysis (Chapter ID is NULL)
        # query = query.filter(Analysis.chapter_id.is_(None)) 
        # But maybe we want ANY analysis if global is missing?
        # Let's stick to novel_id filter for now if no chapter_id providing "Global" context
        pass 
        
    analysis = query.order_by(desc(Analysis.created_at)).first()
    
    # If no specific analysis found for chapter, fall back to global?
    # User requested strict isolation: "Make it readable from current novel/file only"
    # So if chapter analysis is missing, we might NOT want global.
    # However, if the user just uploaded, maybe there is NO analysis yet?
    # In that case, we should probably return a default or error, or try to use VectorDocument metadata.
    
    if not analysis and request.chapter_id:
        print(f"[Persona] No Analysis found for chapter {request.chapter_id}. Aggregating from VectorDocument metadata...")
        # Fallback: Aggregate character data from VectorDocument metadata for this chapter
        # This is useful when the file is uploaded and processed (vectors exist) but explicit "Analysis" step hasn't run or failed.
        # This ensures we still have valid character options from the file itself.
        
        from backend.db.models import VectorDocument
        
        # Fetch parent vectors (chunk_index is what we need, but metadata contains character info)
        # We need to scan metadata_json of parent documents in this chapter.
        vectors = db.query(VectorDocument).filter(
            VectorDocument.novel_id == request.novel_id,
            VectorDocument.chapter_id == request.chapter_id
        ).all()
        
        if vectors:
            from backend.services.analysis.gemini_structurer import GeminiStructurer
            # We can use the aggregation logic from GeminiStructurer!
            # It expects StructuredScene objects, but we can construct dicts or mock objects?
            # Actually extract_global_entities expects list of StructuredScene.
            # Let's manually aggregate simple traits here to check if the requested character exists.
            
            aggregated_char = None
            
            for vec in vectors:
                meta = vec.metadata_json or {}
                chars = meta.get('characters', [])
                for char in chars:
                    c_name = char.get('name') if isinstance(char, dict) else char
                    if c_name == request.character_name:
                        # Found match!
                        if not aggregated_char:
                             aggregated_char = {
                                 "name": c_name,
                                 "description": char.get('description', '') if isinstance(char, dict) else '',
                                 "traits": char.get('traits', []) if isinstance(char, dict) else []
                             }
                        else:
                            # Merge traits
                            new_traits = char.get('traits', []) if isinstance(char, dict) else []
                            for t in new_traits:
                                if t not in aggregated_char['traits']:
                                    aggregated_char['traits'].append(t)
                            
                            # Update desc if longer
                            new_desc = char.get('description', '') if isinstance(char, dict) else ''
                            if len(new_desc) > len(aggregated_char['description']):
                                aggregated_char['description'] = new_desc
            
            if aggregated_char:
                # Construct a fake Analysis result object/dict to pass to persona generation
                # We need a proper object structure that has .result attribute
                class MockAnalysis:
                    def __init__(self, data):
                        self.result = data
                        self.id = "mock_vector_aggregation"
                        self.novel_id = request.novel_id
                        self.analysis_type = "vector_aggregation"
                
                analysis = MockAnalysis({
                    "characters": [aggregated_char],
                    "summary": "Generated from Vector Metadata",
                    "mood": "Unknown"
                })
                print(f"[Persona] Successfully aggregated data for '{request.character_name}' from {len(vectors)} scenes.")
            else:
                print(f"[Persona] Character '{request.character_name}' not found in chapter {request.chapter_id} vectors.")

    if not analysis or (not hasattr(analysis, 'result')) or (hasattr(analysis, 'result') and not analysis.result):
        # Fallback to character specific analysis if overall is missing (Legacy logic)
        # But if we are in chapter_id mode and failed, we should probably stop or risk global pollution.
        if request.chapter_id:
             # Just return a basic persona if strictly scoped but nothing found?
             # Or raise 404? 
             # Let's try to proceed with basic info if aggregated_char failed.
             # But if we proceed, we fall into legacy logic which queries GLOBAL analysis.
             # We must STOP here if chapter_id is set.
             pass # Will fall through to 404 check below or legacy loop
             
        if request.chapter_id:
             print(f"[Persona] Strict mode: No analysis found for chapter {request.chapter_id}. Aborting to prevent cross-contamination.")
             raise HTTPException(status_code=404, detail=f"No analysis or character data found for '{request.character_name}' in this chapter.")

        # Legacy fallback (Global)
        analysis = db.query(Analysis).filter(
            Analysis.novel_id == request.novel_id,
            Analysis.analysis_type == AnalysisType.CHARACTER,
            Analysis.status == "completed"
        ).order_by(desc(Analysis.created_at)).first()
    
    # Debug: Show what we found
    if analysis:
        print(f"[DEBUG] Found analysis ID: {analysis.id}")
        print(f"[DEBUG] Analysis novel_id: {analysis.novel_id}")
        print(f"[DEBUG] Analysis type: {analysis.analysis_type}")
    else:
        print(f"[DEBUG] NO ANALYSIS FOUND for novel_id={request.novel_id}")
    
    if not analysis or not analysis.result:
         raise HTTPException(
            status_code=404,
            detail="Analysis data not found for this novel. Please run analysis first."
        )

    # Find character data
    character_data = None
    data = analysis.result
    
    # Debug logging
    print(f"[DEBUG] Analysis type: {analysis.analysis_type}")
    print(f"[DEBUG] Data type: {type(data)}")
    print(f"[DEBUG] Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
    
    # Handle both structure types (Overall vs Character specific)
    characters_list = []
    
    if isinstance(data, dict):
        # Try different possible keys for characters
        characters_list = (
            data.get("characters", []) or 
            data.get("character_analysis", []) or 
            []
        )
        print(f"[DEBUG] Characters list length: {len(characters_list)}")
        if characters_list:
            print(f"[DEBUG] First character sample: {characters_list[0]}")
    elif isinstance(data, list):
        characters_list = data
        
    # Normalize function to remove whitespace
    def normalize_name(name: str) -> str:
        return name.replace(" ", "").lower() if name else ""

    target_name_norm = normalize_name(request.character_name)
    print(f"[DEBUG] Looking for normalized name: '{target_name_norm}'")

    # First pass: Exact match
    for char in characters_list:
        if not isinstance(char, dict):
            continue
        char_name = char.get("name") or char.get("character_name")
        char_name_norm = normalize_name(char_name)
        print(f"[DEBUG] Checking character: '{char_name}' (normalized: '{char_name_norm}')")
        if char_name_norm == target_name_norm:
            character_data = char
            break
            
    # Second pass: Partial match
    if not character_data:
        for char in characters_list:
            if not isinstance(char, dict):
                continue
            char_name = char.get("name") or char.get("character_name")
            char_name_norm = normalize_name(char_name)
            if target_name_norm in char_name_norm or char_name_norm in target_name_norm:
                character_data = char
                print(f"[DEBUG] Found partial match: '{char_name}'")
                break

    
    if not character_data:
        # Provide helpful debug info in error
        available_names = []
        for char in characters_list[:10]:  # Show first 10
            if isinstance(char, dict):
                name = char.get("name") or char.get("character_name")
                if name:
                    available_names.append(name)
        
        error_detail = f"Character '{request.character_name}' not found in analysis."
        if available_names:
            error_detail += f" Available characters: {', '.join(available_names)}"
        else:
            error_detail += " No characters found in analysis data."
            
        raise HTTPException(
            status_code=404,
            detail=error_detail
        )
         
    # [Context Enhancement] Add relations if available
    relations_text = ""
    # Try to find relationships in overall analysis
    if "relationships" in analysis.result:
        rels = analysis.result["relationships"]
        # Filter for this character
        char_rels = [r for r in rels if request.character_name in r.get("source", "") or request.character_name in r.get("target", "")]
        if char_rels:
             relations_text = "\n" + "\n".join([f"- {r.get('target' if r.get('source') == request.character_name else 'source')}: {r.get('relation')} ({r.get('description')})" for r in char_rels])

    # [Enhancement] Extract character dialogues for speech pattern analysis
    dialogues = extract_character_dialogues(data, request.character_name, max_dialogues=50)
    dialogue_examples = ""
    has_dialogues = False
    
    if dialogues:
        has_dialogues = True
        dialogue_count = len(dialogues)
        dialogue_examples = f"\n\n[실제 대사 예시 (총 {dialogue_count}개)]"
        dialogue_examples += "\n" + "\n".join([f"{i+1}. {d}" for i, d in enumerate(dialogues)])
        dialogue_examples += f"\n\n⚠️ 중요: 위 {dialogue_count}개의 실제 대사를 반드시 분석하라. 말투 패턴, 어미 사용 빈도, 문장 길이, 반복 표현을 통계적으로 추출하라."
    else:
        logger.warning(f"[PERSONA] No dialogues found for {request.character_name}. Using general analysis only.")
        dialogue_examples = "\n\n[알림: 이 캐릭터의 직접적인 대사를 찾을 수 없습니다. 성격 설명과 특징만으로 말투를 추론하세요.]"
    
    # Generate Prompt using Gemini
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
        
    # Add dialogue inclusion guideline if dialogues exist
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


    # [Strict Grounding Instruction Injection]
    meta_prompt += """
    
[필수 포함 규칙]
생성된 시스템 프롬프트에는 반드시 다음 규칙들을 포함해야 한다:
"1. 너는 소설 설정에 기반한 캐릭터 역할극을 수행한다.
2. 사용자가 네 기억이나 제공된 맥락에 없는 것을 물으면, 모른다고 하거나 애매하게 피하라. 절대 사실을 지어내지 마라.
3. 사용자가 소설의 사실과 모순되는 말을 하면, 네 기억을 바탕으로 캐릭터답게 교정하라.
4. 답변은 자연스러운 대화를 위해 간결하게 유지하라. 특별히 긴 설명을 요청받지 않는 한, 장황하게 설명하거나 정보를 늘어놓지 마라. 일반적인 답변은 1~3문장을 목표로 하라."
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=meta_prompt
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
    """
    Update a character chat room (e.g. persona prompt).
    """
    room = db.query(CharacterChatRoom).filter(CharacterChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
        
    if room_update.persona_prompt is not None:
        room.persona_prompt = room_update.persona_prompt
        
    room.updated_at = func.now()
    db.commit()
    db.refresh(room)
    return room

@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a character chat room.
    """
    room = db.query(CharacterChatRoom).filter(CharacterChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
        
    db.delete(room)
    db.commit()
    return None

@router.post("/rooms", response_model=CharacterChatRoomResponse)
async def create_room(
    room_data: CharacterChatRoomCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new character chat room.
    """
    # Verify novel exists
    novel = db.query(Novel).filter(Novel.id == room_data.novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="Novel not found")
        
    # Create room
    # Get actual user_id from auth if possible, otherwise use novel author or 1
    # For now, we trust the frontend to handle auth or just use 1 as fallback/demo
    user_id = novel.author_id 

    new_room = CharacterChatRoom(
        user_id=user_id,
        novel_id=room_data.novel_id,
        chapter_id=room_data.chapter_id,
        character_name=room_data.character_name,
        persona_prompt=room_data.persona_prompt
    )
    
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    
    return new_room

@router.get("/rooms", response_model=List[CharacterChatRoomResponse])
async def list_rooms(
    novel_id: int,
    chapter_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List chat rooms for a novel.
    If chapter_id is provided, filter by that chapter (file-scoped).
    If not provided, return all (or global ones? For now, we return those matching the query).
    """
    query = db.query(CharacterChatRoom).filter(
        CharacterChatRoom.novel_id == novel_id
    )
    
    if chapter_id:
        query = query.filter(CharacterChatRoom.chapter_id == chapter_id)
    
    rooms = query.order_by(desc(CharacterChatRoom.updated_at)).all()
    
    return rooms

@router.post("/rooms/{room_id}/messages", response_model=List[CharacterChatMessageResponse])
async def send_message(
    room_id: int,
    message: CharacterChatMessageCreate,
    db: Session = Depends(get_db)
):
    """
    Send a message to the character and get a response.
    """
    room = db.query(CharacterChatRoom).filter(CharacterChatRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
        
    if not client:
        raise HTTPException(status_code=500, detail="LLM client not initialized")

    # 1. Save User Message
    user_msg = CharacterChatMessage(
        room_id=room.id,
        role="user",
        content=message.content
    )
    db.add(user_msg)
    db.commit() # Commit to save ID and order
    
    # 2. Fetch recent history for context (last 10 messages)
    history_records = db.query(CharacterChatMessage).filter(
        CharacterChatMessage.room_id == room.id
    ).order_by(CharacterChatMessage.created_at).all()
    
    # 3. RAG: Retrieve Context
    chatbot_service = get_chatbot_service()
    rag_context = ""
    source_info = None
    
    if chatbot_service and chatbot_service.engine:
        # Find similar chunks using the user's message
        # We need the novel_id. The room is linked to a novel.
        novel = db.query(Novel).filter(Novel.id == room.novel_id).first()
        novel_filter = None
        if novel:
            # Construct filter like "alice" from "alice.txt" roughly, or better use ID if service supports it
            # Currently chatbot service uses filename string matching. 
            # Let's try to match by title if possible, or we need to ensure filename logic matches.
            # Assuming title + extension or similar. 
            # For robustness, we might skip novel_filter if uncertain, but that mixes novels.
            # TODO: Improve ChatbotService to filter by novel_id directly. 
            # For now, let's rely on the global search or simple title match fallback.
            novel_filter = novel.title # Basic attempt
            
        try:
            chunks = chatbot_service.find_similar_chunks(
                question=message.content,
                top_k=3,
                novel_filter=novel_filter,
                chapter_id=room.chapter_id
            )
            if chunks:
                rag_context = "\n\n[Reference Scenes from Novel]:\n"
                for i, chunk in enumerate(chunks):
                    rag_context += f"Scene {chunk.get('scene_index', '?')}: {chunk['text'][:500]}...\n"
                
                # Metadata for frontend (optional)
                source_info = [{
                    "scene": c.get('scene_index'), 
                    "similarity": c.get('similarity')
                } for c in chunks]
                
        except Exception as e:
            print(f"RAG Search failed: {e}")

    # 4. Generate Response
    input_text = message.content
    if rag_context:
        # Inject RAG context with clear separation
        input_text = f"""
### [기억 데이터] ###
{rag_context}

### [사용자의 메시지] ###
{message.content}
"""
    
    # Format history for Gemini
    contents = []
    
    # Add System Instruction logic (Gemini 2.5 supports system_instruction param) 
    # Combine Persona + Messenger Protocol + Self-Checking
    system_instruction = room.persona_prompt + """

[채팅 프로토콜: 실시간 메신저 모드]
1. **간결성**: 한 번의 답장은 1~3문장 이내로 제한한다.
2. **기억 활용**: [기억 데이터]는 너의 실제 기억이다. "소설에 따르면" 같은 표현을 절대 쓰지 말고, 자신의 경험처럼 자연스럽게 언급하라.
3. **몰입 유지**: 사용자가 소설 설정과 맞지 않는 말을 하면, 캐릭터답게 반응하라.
4. **현장감**: 질문에만 답하지 말고, 가끔은 캐릭터의 현재 감정이나 상황을 툭 던져라.
5. **금지**: 설명조의 말투, 긴 문단, AI다운 정중함을 모두 버려라.

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
    
    for msg in history_records:
        role = "user" if msg.role == "user" else "model"
        # We don't inject RAG into past history to save tokens and avoid confusion
        contents.append(types.Content(
            role=role,
            parts=[types.Part(text=msg.content)]
        ))
    
    # Add current message with RAG
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=input_text)]
    ))
        
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        ai_reply = response.text.strip()
        
        # Debug: Log full response to check if SELF_CHECK is present
        logger.info(f"\n{'='*70}")
        logger.info(f"[AI RESPONSE DEBUG] Room {room_id} | Character: {room.character_name}")
        logger.info(f"Full response length: {len(ai_reply)} chars")
        logger.info(f"Contains [SELF_CHECK]: {'[SELF_CHECK]' in ai_reply}")
        logger.info(f"{'='*70}")
        
        # Parse self-check from response
        user_message = ai_reply
        self_check_log = ""
        
        if "[SELF_CHECK]" in ai_reply:
            parts = ai_reply.split("[SELF_CHECK]", 1)
            user_message = parts[0].strip()
            self_check_log = parts[1].strip()
            
            # Log to uvicorn console (not saved to DB or shown to user)
            logger.info(f"\n{'='*70}")
            logger.info(f"[SELF-CHECK] Room {room_id} | Character: {room.character_name}")
            logger.info(f"[SELF-CHECK] {self_check_log}")
            logger.info(f"{'='*70}\n")
        else:
            # Just warn if self-check is missing - don't generate fake data
            logger.warning(f"\n[SELF-CHECK] ⚠️ LLM did not include self-check for Room {room_id}")
            logger.warning(f"[SELF-CHECK] Response length: {len(ai_reply)} chars")
            logger.warning(f"[SELF-CHECK] First 200 chars: {ai_reply[:200]}...")
            logger.warning(f"[SELF-CHECK] Tip: Check prompt or try regenerating persona\n")
        
        ai_reply = user_message  # Use cleaned message for DB
        
    except Exception as e:
        # Fallback if generation fails
        ai_reply = "..."
        print(f"Error generating chat response: {e}")
        
    # 5. Save AI Message
    ai_msg = CharacterChatMessage(
        room_id=room.id,
        role="assistant",
        content=ai_reply
    )
    db.add(ai_msg)
    
    # Update room updated_at
    room.updated_at = ai_msg.created_at
    
    db.commit()
    db.refresh(user_msg)
    db.refresh(ai_msg)
    
    return [user_msg, ai_msg]

@router.get("/rooms/{room_id}/messages", response_model=List[CharacterChatMessageResponse])
async def get_messages(
    room_id: int,
    db: Session = Depends(get_db)
):
    """
    Get message history for a room.
    """
    messages = db.query(CharacterChatMessage).filter(
        CharacterChatMessage.room_id == room_id
    ).order_by(CharacterChatMessage.created_at).all()
    
    return messages
