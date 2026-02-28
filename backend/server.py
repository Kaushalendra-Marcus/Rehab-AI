"""
RehabAI Backend API Server
"""
import os
import sys
import asyncio
import threading
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from stream_chat import StreamChat

app = FastAPI(title="RehabAI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AGENT_USER_ID = "rehab-ai-agent"


def _get_chat_client() -> StreamChat:
    key = os.environ.get("STREAM_API_KEY")
    secret = os.environ.get("STREAM_API_SECRET")
    if not key or not secret:
        raise HTTPException(status_code=500, detail="STREAM keys missing")
    return StreamChat(api_key=key, api_secret=secret)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "env": {
            k: ("SET" if os.environ.get(k) else "MISSING")
            for k in [
                "STREAM_API_KEY", "STREAM_API_SECRET",
                "GOOGLE_API_KEY", "ELEVENLABS_API_KEY",
                "DEEPGRAM_API_KEY", "ANTHROPIC_API_KEY",
            ]
        },
    }


@app.get("/token")
async def get_token(user_id: str = "patient-001"):
    try:
        chat = _get_chat_client()
        chat.upsert_users([
            {"id": user_id,       "name": "Patient",  "role": "user"},
            {"id": AGENT_USER_ID, "name": "REHAB AI", "role": "admin"},
        ])
        token = chat.create_token(user_id)
        print(f"[RehabAI] ✅ Token issued for user '{user_id}'")
        return {"token": token, "api_key": os.environ["STREAM_API_KEY"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class StartAgentRequest(BaseModel):
    call_id: str
    exercise: str = "general"


@app.post("/start-agent")
async def start_agent(req: StartAgentRequest):
    key    = os.environ.get("STREAM_API_KEY")
    secret = os.environ.get("STREAM_API_SECRET")
    if not key or not secret:
        raise HTTPException(status_code=500, detail="Stream keys missing")

    try:
        chat = StreamChat(api_key=key, api_secret=secret)
        chat.upsert_user({"id": AGENT_USER_ID, "name": "REHAB AI", "role": "admin"})
        agent_token = chat.create_token(AGENT_USER_ID)
        print(f"[RehabAI] ✅ Agent token generated for '{AGENT_USER_ID}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream setup failed: {e}")

    print(f"\n{'='*50}")
    print(f"[RehabAI] Starting agent: call_id={req.call_id} exercise={req.exercise}")

    _launch_agent_thread(req.call_id, req.exercise, agent_token)

    return {"status": "agent_launching", "call_id": req.call_id}


def _launch_agent_thread(call_id: str, exercise: str, agent_token: str):
    agent_script = Path(__file__).parent / "rehab_agent.py"

    env = {
        **os.environ,
        "CALL_ID":            call_id,
        "CALL_TYPE":          "default",
        "EXERCISE":           exercise,
        "STREAM_AGENT_TOKEN": agent_token,
        "STREAM_AGENT_ID":    AGENT_USER_ID,
    }

    def run_in_thread():
        # Wait 4 seconds for patient to fully join the call first
        print(f"[RehabAI] Waiting 4s for patient to join call...")
        time.sleep(4)
        try:
            proc = subprocess.Popen(
                [sys.executable, str(agent_script)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            for line in proc.stdout:
                print(f"[AGENT] {line.decode(errors='replace').rstrip()}", flush=True)
            proc.wait()
            code = proc.returncode
            if code == 0:
                print(f"[RehabAI] ✅ Agent finished cleanly")
            else:
                print(f"[RehabAI] ❌ Agent exited with code {code}")
        except Exception as e:
            print(f"[RehabAI] ❌ Launch failed: {e}")
            import traceback
            traceback.print_exc()

    t = threading.Thread(target=run_in_thread, daemon=True)
    t.start()
    print(f"[RehabAI] ✅ Agent thread launched")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)