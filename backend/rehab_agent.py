"""
RehabAI - Real-time Physical Therapy Coach Agent
Built with Vision Agents SDK

Spawned as subprocess by server.py. Required env vars:
  CALL_ID, CALL_TYPE, EXERCISE
  STREAM_API_KEY, STREAM_API_SECRET
  STREAM_AGENT_TOKEN  <- pre-generated JWT for "rehab-ai-agent" user
  STREAM_AGENT_ID     <- defaults to "rehab-ai-agent"
  ANTHROPIC_API_KEY (or GOOGLE_API_KEY), DEEPGRAM_API_KEY, ELEVENLABS_API_KEY
"""
import os
import asyncio
import sys
import pkgutil
import importlib
from pathlib import Path
from dotenv import load_dotenv

# Windows: ProactorEventLoop required for subprocess/socket support
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


def _find_edge(stream_client):
    """Find the correct GetStream edge class in vision_agents.core.edge."""
    from vision_agents.core import edge as _edge_mod

    members = [x for x in dir(_edge_mod) if not x.startswith("_")]
    print(f"[Agent] vision_agents.core.edge members: {members}")

    # Try known class names
    for cls_name in ["GetStreamEdge", "StreamEdge", "Edge", "GetStream", "VideoEdge"]:
        cls = getattr(_edge_mod, cls_name, None)
        if cls is not None:
            print(f"[Agent] ✅ Found edge class: vision_agents.core.edge.{cls_name}")
            try:
                return cls(client=stream_client)
            except TypeError:
                edge = cls()
                edge.client = stream_client
                return edge

    # EdgeTransport is the correct edge class for GetStream
    for cls_name in ["EdgeTransport", "Call"]:
        cls = getattr(_edge_mod, cls_name, None)
        if cls is not None:
            print(f"[Agent] ✅ Found edge class: vision_agents.core.edge.{cls_name}")
            try:
                return cls(client=stream_client)
            except TypeError:
                try:
                    inst = cls()
                    inst.client = stream_client
                    return inst
                except Exception as e2:
                    print(f"[Agent] {cls_name} init failed: {e2}")

    raise RuntimeError(f"No edge class found. Available: {members}")


def _find_llm():
    """Find Gemini LLM in vision_agents.core.llm, fallback to anthropic plugin."""
    from vision_agents.core import llm as _llm_mod

    members = [x for x in dir(_llm_mod) if not x.startswith("_")]
    print(f"[Agent] vision_agents.core.llm members: {members}")

    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    for cls_name in ["GeminiLLM", "Gemini", "GoogleLLM", "GoogleGeminiLLM", "GeminiFlash"]:
        cls = getattr(_llm_mod, cls_name, None)
        if cls is not None:
            print(f"[Agent] ✅ Using LLM: core.llm.{cls_name}(model={gemini_model})")
            return cls(model=gemini_model)

    # Fallback: anthropic plugin (confirmed available)
    print("[Agent] ⚠️  No Gemini in core.llm — using anthropic plugin fallback")
    from vision_agents.plugins import anthropic
    model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5")
    print(f"[Agent] ✅ Using anthropic.LLM(model={model})")
    return anthropic.LLM(model=model)


def _get_stt():
    from vision_agents.plugins import deepgram
    model = os.environ.get("DEEPGRAM_MODEL", "nova-2")
    print(f"[Agent] ✅ STT: deepgram {model}")
    return deepgram.STT(model=model)


def _get_tts():
    try:
        from vision_agents.plugins import elevenlabs
        tts = elevenlabs.TTS()
        print("[Agent] ✅ TTS: elevenlabs")
        return tts
    except Exception as e:
        print(f"[Agent] elevenlabs TTS failed ({e}) — trying deepgram TTS")

    from vision_agents.plugins import deepgram
    model = os.environ.get("DEEPGRAM_TTS_MODEL", "aura-2-orion-en")
    print(f"[Agent] ✅ TTS: deepgram {model}")
    return deepgram.TTS(model=model)


def _get_processors():
    """YOLO pose processor — optional."""
    try:
        from vision_agents.core import processors as _proc_mod
        members = [x for x in dir(_proc_mod) if not x.startswith("_")]
        print(f"[Agent] processors members: {members}")
        for cls_name in ["YOLOPoseProcessor", "UltralyticsProcessor", "PoseProcessor"]:
            cls = getattr(_proc_mod, cls_name, None)
            if cls is not None:
                proc = cls(model_path="yolo11n-pose.pt", device="cpu", conf_threshold=0.5, fps=1)
                print(f"[Agent] ✅ Processor: {cls_name}")
                return [proc]
    except Exception as e:
        print(f"[Agent] ⚠️  No processor available ({e}) — running without YOLO")
    return []


async def run_agent(call_id: str, call_type: str = "default", exercise: str = "general"):
    from vision_agents.core import Agent, User

    # Log available plugins for debugging
    import vision_agents.plugins as _p
    print("[Agent] Available plugins:", [m.name for m in pkgutil.iter_modules(_p.__path__)])

    agent_id    = os.environ.get("STREAM_AGENT_ID", "rehab-ai-agent")
    api_key     = os.environ["STREAM_API_KEY"]
    api_secret  = os.environ["STREAM_API_SECRET"]
    agent_token = os.environ.get("STREAM_AGENT_TOKEN")

    from getstream import AsyncStream
    stream_client = AsyncStream(api_key=api_key, api_secret=api_secret)
    if agent_token:
        stream_client.token = agent_token
        print(f"[Agent] ✅ Authenticated as '{agent_id}'")
    else:
        print(f"[Agent] ⚠️  No STREAM_AGENT_TOKEN")

    edge       = _find_edge(stream_client)
    llm        = _find_llm()
    stt        = _get_stt()
    tts        = _get_tts()
    processors = _get_processors()

    agent = Agent(
        edge=edge,
        agent_user=User(name="REHAB AI", id=agent_id),
        instructions=INSTRUCTIONS + f"\n\nCurrent exercise: {exercise}",
        llm=llm,
        processors=processors,
        stt=stt,
        tts=tts,
    )

    print(f"[Agent] ✅ Agent created. Joining {call_type}:{call_id}...")
    call = await agent.create_call(call_type, call_id)

    async with agent.join(call):
        print(f"[Agent] ✅ Joined! Sending greeting...")
        await agent.simple_response(
            f"REHAB AI online. {exercise.replace('_', ' ').title()} protocol loaded. "
            "Initiating analysis. Assume starting position when ready."
        )
        print(f"[Agent] Greeting sent. Monitoring session...")
        await agent.finish()

    print(f"[Agent] ✅ Session complete.")


if __name__ == "__main__":
    call_id   = os.environ.get("CALL_ID")
    call_type = os.environ.get("CALL_TYPE", "default")
    exercise  = os.environ.get("EXERCISE", "general")

    if not call_id:
        print("ERROR: CALL_ID env var is required")
        exit(1)

    print(f"[RehabAI Agent] Starting — call_id={call_id} exercise={exercise}")
    asyncio.run(run_agent(call_id, call_type, exercise))
