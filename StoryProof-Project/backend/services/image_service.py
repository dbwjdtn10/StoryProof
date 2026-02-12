import os
import base64
from google import genai
from google.genai import types
from dotenv import load_dotenv

# .env 파일 로드 강화
load_dotenv()

def generate_image_from_text(prompt: str) -> str:
    """
    Google Imagen 4.0을 사용하여 이미지를 생성하고 Base64 문자열로 반환합니다.
    """
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

    try:
        client = genai.Client(api_key=google_key)
        model_name = "imagen-4.0-generate-001" # 모델명 유지
        
        # 이미지 생성 요청
        response = client.models.generate_images(
            model=model_name,
            prompt=f"A high-quality digital illustration of: {prompt}. Artistic style, detailed, cinematic lighting.",
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
                safety_filter_level="block_low_and_above"
            )
        )

        if response.generated_images:
            # 바이너리 데이터를 프론트엔드에서 바로 보여줄 수 있도록 base64 인코딩
            img_data = response.generated_images[0].image.image_bytes
            base64_img = base64.b64encode(img_data).decode('utf-8')
            print(f"[SUCCESS] Imagen 4.0 이미지 생성 완료")
            return f"data:image/png;base64,{base64_img}" 
            
        raise Exception("이미지 생성 결과가 없습니다.")

    except Exception as e:
        print(f"[ERROR] Google Imagen 호출 실패: {e}")
        raise e