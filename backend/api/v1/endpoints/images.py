import asyncio
import logging
import os
import time
from functools import partial

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import Any, Dict

logger = logging.getLogger(__name__)

from backend.db.session import get_db
from backend.db.models import User, Analysis, AnalysisType
from backend.core.security import get_current_user
from backend.services.image_service import ImageService
from backend.services.novel_service import NovelService
from backend.schemas.image_schema import ImageGenerationRequest, ImageGenerationResponse

router = APIRouter()

@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_entity_image(
    request: ImageGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate an image for a specific entity (character, item, location) and update the analysis record.
    """
    logger.info(f"Image Generation Request: novel_id={request.novel_id}, chapter_id={request.chapter_id}, type={request.entity_type}, name={request.entity_name}")
    
    # 1. Verify ownership/permission
    # Using NovelService to check permissions (it raises HTTPException if not allowed)
    try:
        novel = NovelService.get_novel(db, request.novel_id, current_user.id)
    except HTTPException as e:
        # Re-raise with correct context if needed, or let it bubble up
        raise e
        
    # 2. Find the Analysis record
    # We are looking for the 'characters' (global entities) analysis usually attached to the novel or latest chapter.
    # However, global entities are usually stored in an Analysis record with type CHARACTER (or OVERALL).
    # Logic in standard structurer seems to store global entities in AnalysisType.CHARACTER attached to a chapter?
    # Let's check how `tasks.py` stores it: 
    # analysis = db.query(Analysis).filter(Analysis.chapter_id == chapter_id, Analysis.analysis_type == AnalysisType.CHARACTER).first()
    # It seems currently it's per chapter? Or maybe the user wants to update the "Bible" which might be a consolidated view.
    # For now, let's allow updating a specific analysis record if chapter_id is provided, 
    # OR search for the latest analysis if not.
    
    # Check if we have an analysis record to update
    analysis_query = db.query(Analysis).filter(
        Analysis.novel_id == request.novel_id,
        Analysis.analysis_type == AnalysisType.CHARACTER # Assuming this holds characters/items/locations
    )
    
    if request.chapter_id:
        analysis_query = analysis_query.filter(Analysis.chapter_id == request.chapter_id)
        
    # Get the most recent one if multiple (though usually one per chapter)
    analysis = analysis_query.order_by(Analysis.updated_at.desc()).first()
    
    if not analysis:
        logger.warning(f"Analysis record not found for query: novel_id={request.novel_id}, chapter_id={request.chapter_id}")
        raise HTTPException(status_code=404, detail="Analysis record not found. Please analyze the chapter first.")

    logger.info(f"Analysis record found: id={analysis.id}")

    # 3. Initialize Image Service
    try:
        image_service = ImageService()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image service not available: {str(e)}")
        
    # 4. Refine Prompt
    # If description is provided, use it. Otherwise try to find it in the analysis result.
    prompt_text = request.description
    
    if not prompt_text:
        # Try to find the entity description in the JSON
        # Structure: result = {'characters': [...], 'items': [...], 'locations': [...]}
        # Map singular to plural if needed
        key_map = {
            'character': 'characters',
            'item': 'items',
            'location': 'locations'
        }
        json_key = key_map.get(request.entity_type, request.entity_type)
        
        entity_list = analysis.result.get(json_key, [])
        for entity in entity_list:
            if entity.get('name') == request.entity_name:
                # 캐시 확인: 이미 생성된 이미지가 있고 force_regenerate가 아니면 즉시 반환
                existing_image = entity.get('image')
                if existing_image and not request.force_regenerate:
                    image_file_path = os.path.join("backend", existing_image.lstrip('/'))
                    if os.path.exists(image_file_path):
                        logger.info(f"Image cache hit: {existing_image} for {request.entity_name}")
                        return ImageGenerationResponse(image_url=existing_image, refined_prompt="(cached)")

                # visual_description만 사용 (이미지 생성 전용 외모/시각 묘사)
                visual_desc = entity.get('visual_description', '')
                if visual_desc:
                    prompt_text = f"{request.entity_name}. {visual_desc}"
                else:
                    # visual_description이 없는 경우 (구버전 데이터) description 사용
                    desc = entity.get('description', '')
                    traits = ", ".join(entity.get('traits', []))
                    prompt_text = f"{request.entity_name}. {desc} {traits}"
                break
                
    if not prompt_text:
        raise HTTPException(status_code=400, detail=f"Description for '{request.entity_name}' not found. Please provide a description.")
        
    loop = asyncio.get_running_loop()
    refined_prompt = await loop.run_in_executor(
        None, partial(image_service.refine_prompt, prompt_text)
    )

    # 5. Generate Image
    # Filename: novel_{id}_{type}_{name}_{timestamp}.png
    safe_name = "".join(c for c in request.entity_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    timestamp = int(time.time())
    filename = f"novel_{request.novel_id}_{request.entity_type}_{safe_name}_{timestamp}.png"

    image_path = await loop.run_in_executor(
        None, partial(image_service.generate_image, refined_prompt, filename)
    )
    
    if not image_path:
        raise HTTPException(status_code=500, detail="Failed to generate image.")
        
    # 6. Update Analysis Record (Save image path to JSON)
    # We need to update the specific item in the list.
    # Note: modifying valid JSONB in SQLAlchemy requires care (often need to re-assign the whole dict)
    
    updated_result = dict(analysis.result)
    # Map singular to plural again for saving
    key_map = {
        'character': 'characters',
        'item': 'items',
        'location': 'locations'
    }
    json_key = key_map.get(request.entity_type, request.entity_type)
    
    entity_list = updated_result.get(json_key, [])
    
    found = False
    for entity in entity_list:
        if entity.get('name') == request.entity_name:
            entity['image'] = image_path # Add/Update image field
            found = True
            break
            
    if not found:
        # If the entity wasn't found in the list but we generated an image (e.g. user provided custom name/desc),
        # maybe we should add it? Or just warn?
        # For now, let's assume valid entities. If not found, we can't save the URL to the entity.
        # But we return the URL anyway.
        pass
    else:
        updated_result[json_key] = entity_list
        analysis.result = updated_result
        # Force update flag if needed for some ORMs, but re-assigning usually works
        flag_modified(analysis, "result")
        
        db.commit()
        
    return ImageGenerationResponse(image_url=image_path, refined_prompt=refined_prompt)
