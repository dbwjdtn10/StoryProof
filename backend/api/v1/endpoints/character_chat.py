#HJE#HJE
"""
Character Chatbot API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from backend.db.session import get_db
from backend.db.models import Novel, Analysis, AnalysisType, CharacterChatRoom, CharacterChatMessage
from backend.schemas.character_chat_schema import (
    CharacterChatRoomCreate, CharacterChatRoomResponse,
    CharacterChatMessageCreate, CharacterChatMessageResponse,
    PersonaGenerationRequest, PersonaGenerationResponse
)
from backend.core.config import settings

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
        
    for char in characters_list:
        if char.get("name") == request.character_name:
            character_data = char
            break
            
    if not character_data:
        # Try fuzzy match or partial match
        for char in characters_list:
             if request.character_name in char.get("name", ""):
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
    
    Output ONLY the system prompt text. Do not include introductory text.
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
    # TODO: Get actual user_id from auth. Using novel.author_id for now as fallback or 1
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
    ).order_by(CharacterChatMessage.created_at).all() # Get all for now, maybe limit later
    
    # Format history for Gemini
    # Gemini uses 'user' and 'model' roles
    contents = []
    
    # Add System Instruction logic (Gemini 2.5 supports system_instruction param)
    system_instruction = room.persona_prompt
    
    for msg in history_records:
        role = "user" if msg.role == "user" else "model"
        contents.append(types.Content(
            role=role,
           parts=[types.Part(text=msg.content)]

        ))
        
    # 3. Generate Response
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
        
    # 4. Save AI Message
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
