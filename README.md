# Clawbot — AI Agent

A general-purpose AI chat agent powered by GPT-4o, monitored by AgentOps, with a clean web UI.

## Run Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
uvicorn main:app --reload --port 8000
```

Then open http://localhost:8000 in your browser.

## Deploy to Railway (Free)

1. Push this project to a GitHub repo
2. Go to https://railway.app and sign up (free)
3. Click **New Project → Deploy from GitHub repo**
4. Select your repo
5. In Railway dashboard → **Variables**, add:
   - `OPENAI_API_KEY` = your OpenAI key
   - `AGENTOPS_API_KEY` = your AgentOps key
6. Railway auto-deploys and gives you a public URL

## Monitor on AgentOps

Every chat session is automatically tracked at https://app.agentops.ai
- View all sessions, LLM calls, token usage, and costs
- Use Time Travel Debugging to replay any conversation

## Project Structure

```
clawbot/
├── main.py          # FastAPI backend + AgentOps integration
├── static/
│   └── index.html   # Web chat UI
├── requirements.txt
├── Procfile         # Railway/Heroku deploy config
├── runtime.txt      # Python version
└── .env             # API keys (never commit this)
```
