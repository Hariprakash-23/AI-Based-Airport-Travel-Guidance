import os
from dotenv import load_dotenv
load_dotenv(r"C:\Users\akila\OneDrive\Desktop\AI Chatbot\.env")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: API key is missing.")
else:
    print(f"API key loaded: {api_key}")
