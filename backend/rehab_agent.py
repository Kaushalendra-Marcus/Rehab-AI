"""
RehabAI Agent - uses only available vision_agents plugins:
anthropic (LLM), deepgram (STT), elevenlabs (TTS)
"""
import os, asyncio, sys
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

INSTRUCTIONS = """
You are REHAB AI — an expert real-time physical therapy coach speaking like J.A.R.V.I.S.
Keep responses SHORT (1-2 sentences). Count reps, correct form, encourage the patient.
"""

async def run_agent(call_id: str, call_type: str = "default", exercise: str = "general"):
    from vision_agents.core import Agent, User
    from vision_agents.plugins import anthropic, deepgram, elevenlabs

    # Debug
    import vision_agents.plugins as _p, pkgutil
    print("[Agent] Available plugins:", [m.name for m in pkgutil.iter_modules(_p.__path__)])

    # Check what Edge classes are available
    import vision_agents.core as _c
    print("[Agent] vision_agents.core members:", [x for x in dir(_c) if not x.startswith("_")])

    agent_id    = os.environ.get("STREAM_AGENT_ID", "rehab-ai-agent")
    api_key     = os.environ["STREAM_API_KEY"]
    api_secret  = os.environ["STREAM_API_SECRET"]
    agent_token = os.environ.get("STREAM_AGENT_TOKEN")

    from getstream import AsyncStream
    stream_client = AsyncStream(api_key=api_key, api_secret=api_secret)
    if agent_token:
        stream_client.token = agent_token

    # Find correct Edge class
    print("[Agent] getstream module members:", [x for x in dir(stream_client) if not x.startswith("_")])

    tts = elevenlabs.TTS()
    stt = deepgram.STT()
    llm = anthropic.LLM()

    print("[Agent] LLM/STT/TTS created. Trying to create agent...")

    # Try vision_agents native getstream edge via getstream package
    try:
        from vision_agents.edges.getstream import GetStreamEdge
        edge = GetStreamEdge(client=stream_client)
        print("[Agent] Using GetStreamEdge")
    except ImportError as e:
        print(f"[Agent] GetStreamEdge not found: {e}")
        # List all vision_agents submodules
        import vision_agents as va
        print("[Agent] vision_agents path:", va.__file__)
        import pkgutil
        print("[Agent] All vision_agents modules:", [m.name for m in pkgutil.walk_packages(va.__path__, va.__name__ + ".")])
        return

    agent = Agent(
        edge=edge,
        agent_user=User(name="REHAB AI", id=agent_id),
        instructions=INSTRUCTIONS + f"\n\nCurrent exercise: {exercise}",
        llm=llm,
        stt=stt,
        tts=tts,
    )

    call = await agent.create_call(call_type, call_id)
    async with agent.join(call):
        await agent.simple_response("REHAB AI online. Ready.")
        await agent.finish()

if __name__ == "__main__":
    call_id   = os.environ.get("CALL_ID")
    call_type = os.environ.get("CALL_TYPE", "default")
    exercise  = os.environ.get("EXERCISE", "general")
    if not call_id:
        print("ERROR: CALL_ID missing"); exit(1)
    print(f"[RehabAI Agent] Starting — call_id={call_id} exercise={exercise}")
    asyncio.run(run_agent(call_id, call_type, exercise))
