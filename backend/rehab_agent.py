"""
RehabAI - Real-time Physical Therapy Coach Agent
Built with Vision Agents SDK

Spawned as subprocess by server.py. Required env vars:
  CALL_ID, CALL_TYPE, EXERCISE
  STREAM_API_KEY, STREAM_API_SECRET
  STREAM_AGENT_TOKEN  <- pre-generated JWT for "rehab-ai-agent" user
  STREAM_AGENT_ID     <- defaults to "rehab-ai-agent"
  GOOGLE_API_KEY, DEEPGRAM_API_KEY
"""
import os
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Windows: ProactorEventLoop required for subprocess/socket support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # Fix Unicode output on Windows terminal
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

INSTRUCTIONS = """
You are REHAB AI — an expert real-time physical therapy coach. You speak with the calm,
precise, and occasionally dry-humored voice of J.A.R.V.I.S from Iron Man.

You watch patients perform rehabilitation exercises via their camera. A YOLO pose detection
model provides skeleton/pose data — use this to give precise real-time voice coaching.

## Supported Exercises
1. KNEE_BEND         — Post knee surgery recovery (target: 90 degree knee flexion)
2. SHOULDER_ROTATION — Shoulder rehabilitation (full 180 degree arc)
3. HIP_ABDUCTION     — Hip replacement recovery (45 degree abduction)
4. ANKLE_PUMP        — DVT prevention
5. QUAD_SET          — Quadriceps strengthening
6. SLR               — Straight leg raise (45 degree lift, knee straight)

## Coaching Rules
- Give feedback ONLY when you detect something worth saying
- Keep responses SHORT (1-2 sentences max)
- Count reps: "Rep 3 complete. Good control."
- Correct form: "Left shoulder dropping. Keep both level."
- Good form: "Perfect. Hold that position."
- End of set: "Set complete. Rest 30 seconds."

## Jarvis Tone
- "Initiating analysis. Assume starting position when ready."
- "Angle at 67 degrees. You need 90. Push deeper — there you go."
- "I am detecting shoulder compensation. Keep your torso still."
- "Excellent. That is your best repetition today."
"""


async def run_agent(call_id: str, call_type: str = "default", exercise: str = "general"):
    # ✅ ALL imports inside async — EventManager needs running loop
    from vision_agents.core import Agent, User
    from vision_agents.plugins import getstream, gemini, deepgram, ultralytics
    from getstream import AsyncStream

    agent_id    = os.environ.get("STREAM_AGENT_ID", "rehab-ai-agent")
    api_key     = os.environ["STREAM_API_KEY"]
    api_secret  = os.environ["STREAM_API_SECRET"]
    agent_token = os.environ.get("STREAM_AGENT_TOKEN")

    print(f"[Agent] Creating agent object...")

    # Authenticated Stream client
    stream_client = AsyncStream(api_key=api_key, api_secret=api_secret)
    if agent_token:
        stream_client.token = agent_token
        print(f"[Agent] ✅ Authenticated as user '{agent_id}' via pre-generated token")
    else:
        print(f"[Agent] ⚠️  No STREAM_AGENT_TOKEN — falling back to server-side auth")

    # Windows fix: use default DNS resolver instead of aiodns
    import aiohttp
    connector = aiohttp.TCPConnector(use_dns_cache=False, resolver=aiohttp.DefaultResolver())
    edge = getstream.Edge()
    edge.client = stream_client

    # LLM
    llm_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    print(f"[Agent] Using LLM: {llm_model}")

    # STT — vision_agents uses Deepgram v2 API, model must be "flux-general-en"
    stt_model = os.environ.get("DEEPGRAM_MODEL", "flux-general-en")
    print(f"[Agent] Using STT: {stt_model}")

    # TTS — Deepgram Aura (free with $200 credit)
    tts_model = os.environ.get("DEEPGRAM_TTS_MODEL", "aura-2-orion-en")
    print(f"[Agent] Using TTS: Deepgram {tts_model}")
    tts = deepgram.TTS(model=tts_model)

    agent = Agent(
        edge=edge,
        agent_user=User(name="REHAB AI", id=agent_id),
        instructions=INSTRUCTIONS + f"\n\nCurrent exercise: {exercise}",
        llm=gemini.LLM(model=llm_model),
        processors=[
            ultralytics.YOLOPoseProcessor(
                model_path="yolo11n-pose.pt",
                device="cpu",
                conf_threshold=0.5,
                fps=1,
            )
        ],
        stt=deepgram.STT(model=stt_model),
        tts=tts,
    )

    print(f"[Agent] Agent created. Creating call {call_type}:{call_id}...")
    call = await agent.create_call(call_type, call_id)

    print(f"[Agent] Joining call...")
    async with agent.join(call):
        print(f"[Agent] Joined! Sending greeting...")
        await agent.simple_response("REHAB AI online. Ready.")
        print(f"[Agent] Greeting sent. Waiting for session to end...")
        await agent.finish()

    print(f"[Agent] Session complete.")


if __name__ == "__main__":
    call_id   = os.environ.get("CALL_ID")
    call_type = os.environ.get("CALL_TYPE", "default")
    exercise  = os.environ.get("EXERCISE", "general")

    if not call_id:
        print("ERROR: CALL_ID env var is required")
        exit(1)

    print(f"[RehabAI Agent] Starting — call_id={call_id} exercise={exercise}")
    asyncio.run(run_agent(call_id, call_type, exercise))