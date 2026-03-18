"""
Start all Clawbot services:
  - Web chat UI   -> http://localhost:8000
  - WhatsApp bot  -> http://localhost:8001  (needs ngrok + Twilio)
  - Discord bot   -> runs in background thread

Usage:  python run.py
"""

import os
import threading
import subprocess
import sys

PYTHON = sys.executable


def run_web():
    subprocess.run([PYTHON, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"])


def run_whatsapp():
    subprocess.run([PYTHON, "-m", "uvicorn", "whatsapp_webhook:app", "--host", "0.0.0.0", "--port", "8001"])


def run_discord():
    subprocess.run([PYTHON, "discord_bot.py"])


if __name__ == "__main__":
    print("Starting Clawbot services...")
    print("  Web chat   -> http://localhost:8000")
    print("  WhatsApp   -> http://localhost:8001 (expose with ngrok)")
    print("  Discord    -> connecting to Discord gateway")
    print()

    threads = [
        threading.Thread(target=run_web, daemon=True),
        threading.Thread(target=run_whatsapp, daemon=True),
        threading.Thread(target=run_discord, daemon=True),
    ]

    for t in threads:
        t.start()

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nShutting down Clawbot.")
