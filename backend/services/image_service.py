import os
import io
import logging
from typing import Optional
from datetime import datetime
from backend.core.config import settings

# Try to import google-genai, but handle if it's not installed yet
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    print("Warning: google-genai library not found. Image generation will not work.")

logger = logging.getLogger(__name__)

class ImageService:
    """
    Service for generating images using Google's Imagen model.
    """
    
    def __init__(self, api_key: str = None):
        if not api_key:
            api_key = settings.GOOGLE_API_KEY
            
        if not api_key:
            logger.error("GOOGLE_API_KEY is not set.")
            raise ValueError("GOOGLE_API_KEY is required.")
            
        if not genai:
            logger.error("google-genai library is not installed.")
            raise ImportError("google-genai library is required.")
            
        self.client = genai.Client(api_key=api_key)
        self.refine_model = settings.GEMINI_REFINE_MODEL
        self.image_model = settings.IMAGEN_GENERATE_MODEL

    def refine_prompt(self, prompt: str) -> str:
        """
        Refines the user prompt using Gemini to be suitable for Imagen.
        """
        if not prompt:
            return ""
            
        logger.info(f"Refining prompt: {prompt[:50]}...")
        
        system_instruction = (
            "You are a master of visual storytelling and prompt engineering. "
            "Your goal is to transform Korean novel excerpts or character descriptions into vivid, high-quality image prompts for Imagen. "
            "1. STYLISTIC CONSISTENCY: Always use a 'Classic 19th-century storybook illustration' style with rich textures and moody lighting. "
            "2. PRESERVE DETAILS: Don't just summarize. If there's a specific object or emotion, describe its visual appearance. "
            "3. SAFETY & SCALE: Replace 'violent' acts with 'dramatic tension'. "
            "4. NO TEXT: Do not include any text, names, labels, or captions in the image. "
            "5. SINGLE IMAGE: Describe a single, focused scene or character portrait, not a collage or grid."
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.refine_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    safety_settings=[
                         types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_NONE"
                        ),
                    ]
                )
            )
            
            if response.text:
                refined = response.text.strip()
                logger.info(f"Refined prompt: {refined[:50]}...")
                return refined
            return prompt
            
        except Exception as e:
            logger.error(f"Prompt refinement failed: {e}")
            return prompt

    def generate_image(self, prompt: str, output_filename: str) -> Optional[str]:
        """
        Generates an image and saves it to the static directory.
        
        Args:
            prompt: The image prompt
            output_filename: Desired filename (e.g., 'char_123_456.png')
            
        Returns:
            str: The relative path to the saved image (e.g., '/static/images/char_123_456.png')
        """
        if not prompt:
            return None
            
        logger.info(f"Generating image for: {prompt[:50]}...")
        
        # Ensure static/images directory exists
        # Assuming backend is running from c:\myworkfolder\StoryProof
        base_dir = os.getcwd()
        static_dir = os.path.join(base_dir, "backend", "static", "images")
        os.makedirs(static_dir, exist_ok=True)
        
        target_path = os.path.join(static_dir, output_filename)
        
        try:
            response = self.client.models.generate_images(
                model=self.image_model,
                prompt=f"A high-quality digital illustration of: {prompt}. Artistic style, detailed, cinematic lighting. Single image, focused composition. No text, no captions, no labels, no watermark.",
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="1:1",
                    safety_filter_level="block_low_and_above"
                )
            )

            if response.generated_images:
                image_bytes = response.generated_images[0].image.image_bytes
                
                with open(target_path, "wb") as f:
                    f.write(image_bytes)
                    
                logger.info(f"Image saved to: {target_path}")
                
                # Return relative path for frontend
                return f"/static/images/{output_filename}"
            else:
                logger.error("No image generated.")
                return None
                
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None
