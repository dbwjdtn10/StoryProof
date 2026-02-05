import sys
import io
from google import genai
from backend.core.config import settings

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_25():
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        print("Testing gemini-2.5-flash...")
        try:
            client.models.generate_content(model='gemini-2.5-flash', contents='Hello')
            print("SUCCESS: gemini-2.5-flash IS available.")
        except Exception as e:
            print(f"FAILED: gemini-2.5-flash failed: {e}")

    except Exception as e:
        print(f"Error initializing client: {e}")

if __name__ == "__main__":
    check_25()
