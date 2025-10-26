import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load .env so it gets your GEMINI_API_KEY
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("✅ Listing available Gemini models...\n")

for model in genai.list_models():
    print(model.name)