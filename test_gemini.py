import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
api_key = os.environ.get('GEMINI_API_KEY')
print(f"Key loaded: {bool(api_key)}")

try:
    from google import genai
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='Hello'
    )
    print("Response:", response.text)
except Exception as e:
    print("Error:", str(e))
