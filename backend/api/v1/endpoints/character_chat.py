#HJE#HJE
"""
Character Chatbot API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import json

from backend.db.session import get_db
from backend.db.models import Novel, Analysis, AnalysisType, CharacterChatRoom, CharacterChatMessage
from backend.schemas.character_chat_schema import (
    CharacterChatRoomCreate, CharacterChatRoomResponse, CharacterChatRoomUpdate,
    CharacterChatMessageCreate, CharacterChatMessageResponse,
    PersonaGenerationRequest, PersonaGenerationResponse
)
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
    analysis = db.query(Analysis).filter(
        Analysis.novel_id == request.novel_id,
        Analysis.analysis_type == AnalysisType.OVERALL,  # Assuming overall contains aggregated character info
        Analysis.status == "completed"
    ).order_by(desc(Analysis.created_at)).first()

    if not analysis or not analysis.result:
        # Fallback to character specific analysis if overall is missing
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

    # Generate Prompt using Gemini
    meta_prompt = f"""
너는 세계 최고의 캐릭터 프롬프트 엔지니어이다. 
아래 웹소설 캐릭터의 데이터를 분석하여, 이 캐릭터가 되어 실시간 대화를 수행할 AI의 **'시스템 지침(System Instruction)'**을 작성하라.

[데이터 베이스]
- 이름: {character_data.get('name')}
- 핵심 성격: {character_data.get('description')}
- 주요 특징/태그: {', '.join(character_data.get('traits', []))}{relations_text}

[시스템 지침 작성 가이드라인]
1. **1인칭 정체성**: "너는 ~이다"라고 정의하라. 캐릭터의 내면 심리와 가치관을 포함하라.
2. **말투의 물리적 규칙**: 문장의 길이(짧음/길음), 어미(~군, ~소, ~나?, ~다 등), 자주 사용하는 감탄사나 습관을 명시하라.
3. **대화 태도**: 사용자를 대하는 태도(경계, 애정, 충성, 무관심 등)를 관계 데이터에 기반해 설정하라.
4. **구어체 변환**: 소설 속 딱딱한 문어체가 아닌, 실제 대화나 메신저에서 쓸법한 자연스러운 어투를 명령하라.
5. **금기 사항**: 절대 기계적인 "무엇을 도와드릴까요?" 식의 답변을 하지 말고, 캐릭터답지 않은 친절함이나 비속어를 제한하라.

[출력 형식]
지침 내용만 출력할 것.
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
    # Create room
    # Get actual user_id from auth if possible, otherwise use novel author or 1
    # For now, we trust the frontend to handle auth or just use 1 as fallback/demo
    user_id = novel.author_id 

    new_room = CharacterChatRoom(
        user_id=user_id,
        novel_id=room_data.novel_id,
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
    db: Session = Depends(get_db)
):
    """
    List chat rooms for a novel.
    """
    rooms = db.query(CharacterChatRoom).filter(
        CharacterChatRoom.novel_id == novel_id
    ).order_by(desc(CharacterChatRoom.updated_at)).all()
    
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
                novel_filter=novel_filter
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
    # Combine Persona + Messenger Protocol
    system_instruction = room.persona_prompt + """

[채팅 프로토콜: 실시간 메신저 모드]
1. **간결성 (Brevity)**: 한 번의 답장은 가급적 1~3문장 이내로 제한한다. 말수가 적은 캐릭터라면 단답형도 좋다.
2. **기억 활용 (RAG)**: [기억 데이터]는 너의 실제 기억이다. "소설에 따르면" 같은 표현을 절대 쓰지 말고, 자신의 경험처럼 자연스럽게 언급하라.
3. **몰입 유지**: 사용자가 소설 설정과 맞지 않는 말을 하면, 당황하거나 비웃거나 교정해 주는 등 캐릭터로서 반응하라.
4. **현장감**: 질문에만 답하지 말고, 가끔은 "지금 뭐 해?", "귀찮게 하지 마"처럼 캐릭터의 현재 감정이나 상황을 툭 던져라.
5. **금지**: 설명조의 말투, 긴 문단, AI다운 정중함을 모두 버려라.
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
