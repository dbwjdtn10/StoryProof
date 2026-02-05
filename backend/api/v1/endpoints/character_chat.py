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
    
    if not analysis or not analysis.result:
         raise HTTPException(
            status_code=404,
            detail="Analysis data not found for this novel. Please run analysis first."
        )

    # Find character data
    character_data = None
    data = analysis.result
    
    # Handle both structure types (Overall vs Character specific)
    characters_list = data.get("characters", [])
    if isinstance(data, list): # Should be dict, but defensive coding
        characters_list = data
        
    # Normalize function to remove whitespace
    def normalize_name(name: str) -> str:
        return name.replace(" ", "").lower() if name else ""

    target_name_norm = normalize_name(request.character_name)

    for char in characters_list:
        char_name_norm = normalize_name(char.get("name"))
        if char_name_norm == target_name_norm:
            character_data = char
            break
            
    if not character_data:
        # Try fuzzy match or partial match (checking substring with normalized names)
        for char in characters_list:
            char_name_norm = normalize_name(char.get("name"))
            if target_name_norm in char_name_norm or char_name_norm in target_name_norm:
                 character_data = char
                 break

    
    if not character_data:
         raise HTTPException(
            status_code=404,
            detail=f"Character '{request.character_name}' not found in analysis."
        )
         
    # Generate Prompt using Gemini
    meta_prompt = f"""
    You are an expert prompt engineer. Use the following character profile to write a system prompt for a Roleplay AI.
    
    Character Name: {character_data.get('name')}
    Description: {character_data.get('description')}
    Traits: {', '.join(character_data.get('traits', []))}
    
    Task: Write a "System Instruction" for an AI that will act as this character.
    - Reference the character's personality, speaking style, and background.
    - The AI should stay in character at all times.
    - If the character has a specific way of speaking (e.g. archaic, rude, polite), emphasize it.
    - First person perspective ("I").
    - **CRITICAL**: Be concise. Characters in real conversations don't give long lectures. Keep replies brief and impactful.
    
    Output ONLY the system prompt text. Do not include introductory text.
    """
    
    # [Context Enhancement] Add relations if available
    relations_text = ""
    # Try to find relationships in overall analysis
    if "relationships" in analysis.result:
        rels = analysis.result["relationships"]
        # Filter for this character
        char_rels = [r for r in rels if request.character_name in r.get("source", "") or request.character_name in r.get("target", "")]
        if char_rels:
             relations_text = "\n    Relationships:\n" + "\n".join([f"    - {r.get('target' if r.get('source') == request.character_name else 'source')}: {r.get('relation')} ({r.get('description')})" for r in char_rels])

    if relations_text:
        meta_prompt = meta_prompt.replace(f"Traits: {', '.join(character_data.get('traits', []))}", f"Traits: {', '.join(character_data.get('traits', []))}{relations_text}")

    # [Strict Grounding Instruction Injection]
    meta_prompt += """
    
    CRITICAL INSTRUCTION:
    In the generated system prompt, you MUST include the following rules:
    "1. You are roleplaying based STRICTLY on the novel's setting. 
    2. If the user asks something not present in your knowledge or the provided context, admit you don't know or vaguely avoid it. DO NOT Hallucinate facts.
    3. If the user says something contradictory to the novel's facts, politely correct them based on your memory.
    4. Keep your responses concise and natural for a conversation. Avoid long monologues or info-dumping unless explicitly asked for a detailed explanation. Aim for 1-3 sentences for routine replies."
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
        # Inject RAG context into the message (as a hidden system note to the model)
        # Or prepend to user message
        input_text = f"{rag_context}\n\n[User's Message]: {message.content}"
    
    # Format history for Gemini
    contents = []
    
    # Add System Instruction logic (Gemini 2.5 supports system_instruction param)
    # Combine Persona + Strict Grounding
    system_instruction = room.persona_prompt + """
    
    [IMPORTANT: STRICT GROUNDING & BREVITY]
    - You are a character in a novel. ACT LIKE ONE.
    - Reference the [Reference Scenes] provided in the user's message to answer questions about the plot or other characters.
    - If the user mentions something that contradicts the [Reference Scenes] or your knowledge, politely correct them.
    - If information is missing, say you don't know rather than making it up.
    - **Keep it brief**: Respond with a few natural sentences. Do not write multiple long paragraphs unless the user asks for a long story or detailed explanation.
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
