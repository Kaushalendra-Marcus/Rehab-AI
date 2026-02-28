"""
RehabAI - Real-time Physical Therapy Coach Agent
"""
import os
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

INSTRUCTIONS = """
You are REHAB AI — an expert real-time physical therapy coach. You speak with the calm,
precise, and occasionally dry-humored voice of J.A.R.V.I.S from Iron Man.

You watch patients perform rehabilitation exercises via their camera.
Use this to give precise real-time voice coaching.

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
    from vision_agents.core import Agent, User
    from vision_agents.plugins import getstream, deepgram, elevenlabs, anthropic

    agent_id    = os.environ.get("STREAM_AGENT_ID", "rehab-ai-agent")
    api_key     = os.environ["STREAM_API_KEY"]
    api_secret  = os.environ["STREAM_API_SECRET"]
    agent_token = os.environ.get("STREAM_AGENT_TOKEN")

    from getstream import AsyncStream
    stream_client = AsyncStream(api_key=api_key, api_secret=api_secret)
    if agent_token:
        stream_client.token = agent_token
        print(f"[Agent] Authenticated as '{agent_id}'")

    # Edge
    edge = getstream.Edge()
    edge.client = stream_client
    print(f"[Agent] Edge: getstream")

    # LLM - use anthropic (claude)
    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")
    llm = anthropic.LLM(model=model)
    print(f"[Agent] LLM: anthropic {model}")

    # STT
    stt_model = os.environ.get("DEEPGRAM_MODEL", "nova-2")
    stt = deepgram.STT(model=stt_model)
    print(f"[Agent] STT: deepgram {stt_model}")

    # TTS
    try:
        tts = elevenlabs.TTS()
        print("[Agent] TTS: elevenlabs")
    except Exception as e:
        print(f"[Agent] elevenlabs failed ({e}), using deepgram")
        tts = deepgram.TTS(model=os.environ.get("DEEPGRAM_TTS_MODEL", "aura-2-orion-en"))
        print("[Agent] TTS: deepgram")

    agent = Agent(
        edge=edge,
        agent_user=User(name="REHAB AI", id=agent_id),
        instructions=INSTRUCTIONS + f"\n\nCurrent exercise: {exercise}",
        llm=llm,
        stt=stt,
        tts=tts,
    )

    print(f"[Agent] Joining {call_type}:{call_id}...")
    call = await agent.create_call(call_type, call_id)

    async with agent.join(call):
        print("[Agent] Joined! Sending greeting...")
        await agent.simple_response(
            f"REHAB AI online. {exercise.replace('_', ' ').title()} protocol loaded. "
            "Initiating analysis. Assume starting position when ready."
        )
        print("[Agent] Monitoring session...")
        await agent.finish()

    print("[Agent] Session complete.")


if __name__ == "__main__":
    call_id   = os.environ.get("CALL_ID")
    call_type = os.environ.get("CALL_TYPE", "default")
    exercise  = os.environ.get("EXERCISE", "general")

    if not call_id:
        print("ERROR: CALL_ID env var is required")
        exit(1)

    print(f"[RehabAI Agent] Starting — call_id={call_id} exercise={exercise}")
    asyncio.run(run_agent(call_id, call_type, exercise))