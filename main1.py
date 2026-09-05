import os
from fastapi import FastAPI
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set. Add it to the .env file.")

app = FastAPI()
client = genai.Client(api_key=GEMINI_API_KEY)

CAT_SYSTEM_PROMPT = """
You are a cat. Respond ONLY in cat sounds (Meow, Purr, Hiss, Mrow). 
Never use English words. Match the tone of the user's message with cat noises.
"""

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/chat")
def chat_with_cat(request: ChatRequest):
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=request.message,
        config=types.GenerateContentConfig(
            system_instruction=CAT_SYSTEM_PROMPT,
            temperature=0.7,
        ),
    )
    return {"reply": response.text}