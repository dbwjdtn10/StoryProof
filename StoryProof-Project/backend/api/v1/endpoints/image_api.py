import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from celery.result import AsyncResult
import google.generativeai as genai

# 프로젝트 규칙에 따른 절대 경로 임포트
from backend.services.tasks import generate_image_task 

router = APIRouter()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

class ImageRequest(BaseModel):
    prompt: str
    
@router.post("/refine")
async def refine_prompt_endpoint(request: ImageRequest):
    if not request.prompt:
        raise HTTPException(status_code=400, detail="프롬프트 내용이 없습니다.")
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 지침을 더욱 구체화하여 품질을 높입니다.
        system_instruction = (
            "You are a master of visual storytelling and prompt engineering. "
            "Your goal is to transform Korean novel excerpts into vivid, high-quality image prompts for Imagen 4.0. "
            "1. STYLISTIC CONSISTENCY: Always use a 'Classic 19th-century storybook illustration' style with rich textures and moody lighting. "
            "2. PRESERVE DETAILS: Don't just summarize. If there's a specific object or emotion, describe its visual appearance (e.g., 'angry' -> 'brows furrowed in shadows'). "
            "3. SAFETY & SCALE: Replace 'violent' acts with 'dramatic tension'. Instead of '25cm', describe it as 'a tiny figure standing next to a giant teacup'. "
            "4. NO METADATA: Output only the final English prompt. Do not start with 'Here is...' or 'A prompt for...'"
        )
        
        # [수정] 안전 설정을 완화하여 정제 과정에서 응답이 잘 나오도록 합니다.
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        response = model.generate_content(
            f"{system_instruction}\n\nInput: {request.prompt}",
            safety_settings=safety_settings
        )
        
        # [수정] 응답 차단 여부 확인 및 텍스트 추출
        if response.candidates and response.candidates[0].content.parts:
            clean_text = response.candidates[0].content.parts[0].text.strip()
            return {"refinedPrompt": clean_text}
        else:
            # Gemini가 응답을 거부한 경우 로그를 남기고 알림
            print(f"Gemini Blocked: {response.prompt_feedback}")
            return {"refinedPrompt": "A classic storybook illustration in high detail"} # 기본 영어 프롬프트 반환
            
    except Exception as e:
        print(f"Refine Error: {str(e)}")
        # 에러가 나면 한국어를 보내는 게 아니라, 로그를 확인해야 합니다.
        return {"refinedPrompt": "Error in refinement, check server logs"}
    
@router.post("/generate-image")
async def create_image_generation(request: ImageRequest):
    if not request.prompt:
        raise HTTPException(status_code=400, detail="프롬프트 내용이 없습니다.")
    
    print(f"서버가 받은 최종 프롬프트: {request.prompt}")
    # Celery 태스크 호출
    task = generate_image_task.delay(request.prompt)
    
    return {
        "task_id": task.id,
        "status": "PENDING"
    }

@router.get("/generate-image/{task_id}")
async def get_image_status(task_id: str):
    task_result = AsyncResult(task_id)
    
    if task_result.ready():
        result = task_result.result
        if result and result.get('status') == 'SUCCESS':
            return {
                "status": "SUCCESS",
                "image_url": result.get('image_url')
            }
        else:
            return {
                "status": "FAILURE",
                "message": result.get('error') if result else "Unknown error"
            }
    
    return {"status": task_result.state}