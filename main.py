import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import agentops
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set.")

agentops.init(api_key=AGENTOPS_API_KEY, default_tags=["clawbot"])

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Clawbot Agent")

SYSTEM_PROMPT = (
    "You are Clawbot, a sharp and helpful AI assistant. "
    "You answer questions clearly and concisely, help with tasks, "
    "writing, research, code, and general knowledge. "
    "Be friendly but direct."
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]


class ChatResponse(BaseModel):
    reply: str


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
            {"role": m.role, "content": m.content} for m in request.messages
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )

        reply = response.choices[0].message.content
        return ChatResponse(reply=reply)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "clawbot"}
