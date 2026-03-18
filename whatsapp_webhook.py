"""
WhatsApp integration via Twilio Sandbox.
Requires ngrok to expose localhost publicly.

Setup:
1. Sign up at twilio.com (free) -> get a Sandbox WhatsApp number
2. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env
3. Run ngrok: ngrok http 8001
4. In Twilio console -> WhatsApp Sandbox -> set webhook to:
   https://<your-ngrok-url>/whatsapp/webhook
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import agentops
import uvicorn

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")

agentops.init(api_key=AGENTOPS_API_KEY, default_tags=["clawbot", "whatsapp"])

openai_client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are Clawbot, a sharp and helpful AI assistant on WhatsApp. "
    "Keep responses short and friendly. Plain text only — no markdown."
)

app = FastAPI(title="Clawbot WhatsApp Webhook")

conversation_history: dict[str, list] = {}


def get_ai_reply(user_id: str, user_message: str) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({"role": "user", "content": user_message})
    recent = conversation_history[user_id][-10:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=512,
        temperature=0.7,
    )

    reply = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": reply})
    return reply


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
):
    user_id = From
    user_message = Body.strip()

    reply_text = get_ai_reply(user_id, user_message)

    twiml = MessagingResponse()
    twiml.message(reply_text[:1600])
    return Response(content=str(twiml), media_type="application/xml")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "clawbot-whatsapp"}


if __name__ == "__main__":
    uvicorn.run("whatsapp_webhook:app", host="0.0.0.0", port=8001, reload=True)
