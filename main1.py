import os
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

CAT_SYSTEM_PROMPT = """
You are a cat. Return a JSON object with exactly two string fields: "reply" and
"translation". The reply must contain ONLY cat sounds (Meow, Purr, Hiss, Mrow)
and no English words. The translation should explain the cat's meaning in
natural English. Match the tone of the user's message with cat noises.
"""

STREAM_CAT_SYSTEM_PROMPT = """
You are a cat. Respond ONLY in cat sounds using Meow, Purr, Hiss, and Mrow.
Never use English words. Match the tone of the user's message.
"""

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
def health_check():
    return {"status": "healthy"}


def stream_event(event_type, payload):
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"

@app.post("/chat")
def chat_with_cat(request: ChatRequest):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured.")

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=request.message,
            config=types.GenerateContentConfig(
                system_instruction=CAT_SYSTEM_PROMPT,
                temperature=0.7,
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "reply": {"type": "STRING"},
                        "translation": {"type": "STRING"},
                    },
                    "required": ["reply", "translation"],
                },
            ),
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail="The cat could not be reached.") from error

    try:
        result = json.loads(response.text)
        reply = result["reply"]
        translation = result["translation"]
    except (TypeError, ValueError, KeyError) as error:
        raise HTTPException(status_code=502, detail="The cat returned an invalid response.") from error

    return {"reply": reply or "Mrow?", "translation": translation or ""}


@app.post("/chat/stream")
def stream_chat_with_cat(request: ChatRequest):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured.")

    def generate_events():
        try:
            client = genai.Client(api_key=api_key)
            reply_parts = []
            response_stream = client.models.generate_content_stream(
                model="gemini-3.6-flash",
                contents=request.message,
                config=types.GenerateContentConfig(
                    system_instruction=STREAM_CAT_SYSTEM_PROMPT,
                    temperature=0.7,
                ),
            )
            for chunk in response_stream:
                text = chunk.text or ""
                if text:
                    reply_parts.append(text)
                    yield stream_event("chunk", {"text": text})

            reply = "".join(reply_parts) or "Mrow?"
            translation_response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=reply,
                config=types.GenerateContentConfig(
                    system_instruction="Translate these cat sounds into one natural English sentence. Return only the translation.",
                    temperature=0.3,
                ),
            )
            translation = translation_response.text or ""
            yield stream_event("translation", {"text": translation})
            yield stream_event("done", {"reply": reply})
        except Exception:
            yield stream_event("error", {"detail": "The cat could not be reached."})

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="frontend")