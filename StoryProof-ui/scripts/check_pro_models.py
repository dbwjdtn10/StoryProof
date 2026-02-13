import sys
import io
from google import genai
from backend.core.config import settings

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_pro():
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        print("Testing gemini-1.5-pro...")
        try:
            client.models.generate_content(model='gemini-1.5-pro', contents='Hello')
            print("SUCCESS: gemini-1.5-pro IS available.")
        except Exception as e:
            print(f"FAILED: gemini-1.5-pro failed: {e}")

        print("\nTesting gemini-1.5-pro-001...")
        try:
            client.models.generate_content(model='gemini-1.5-pro-001', contents='Hello')
            print("SUCCESS: gemini-1.5-pro-001 IS available.")
        except Exception as e:
            print(f"FAILED: gemini-1.5-pro-001 failed: {e}")

    except Exception as e:
        print(f"Error initializing client: {e}")

if __name__ == "__main__":
    check_pro()
