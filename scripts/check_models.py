import sys
import io
from google import genai
from backend.core.config import settings

# Force utf-8 for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def list_models():
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        print("Testing gemini-1.5-flash-001...")
        try:
            client.models.generate_content(model='gemini-1.5-flash-001', contents='Hello')
            print("SUCCESS: gemini-1.5-flash-001 IS available.")
        except Exception as e:
            print(f"FAILED: gemini-1.5-flash-001 failed: {e}")

        print("\nTesting gemini-1.5-flash...")
        try:
            client.models.generate_content(model='gemini-1.5-flash', contents='Hello')
            print("SUCCESS: gemini-1.5-flash IS available.")
        except Exception as e:
            print(f"FAILED: gemini-1.5-flash failed: {e}")

        print("\nTesting gemini-1.5-flash-8b...")
        try:
            client.models.generate_content(model='gemini-1.5-flash-8b', contents='Hello')
            print("SUCCESS: gemini-1.5-flash-8b IS available.")
        except Exception as e:
            print(f"FAILED: gemini-1.5-flash-8b failed: {e}")

    except Exception as e:
        print(f"Error initializing client: {e}")

if __name__ == "__main__":
    list_models()
