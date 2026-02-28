import os, asyncio, sys, pkgutil
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

async def run_agent(call_id: str, call_type: str = "default", exercise: str = "general"):
    from vision_agents.core import llm as _llm, edge as _edge, stt as _stt, tts as _tts

    print("[Agent] llm members:", [x for x in dir(_llm) if not x.startswith("_")])
    print("[Agent] edge submodules:", [m.name for m in pkgutil.iter_modules(_edge.__path__)])
    print("[Agent] edge members:", [x for x in dir(_edge) if not x.startswith("_")])
    print("[Agent] stt members:", [x for x in dir(_stt) if not x.startswith("_")])
    print("[Agent] tts members:", [x for x in dir(_tts) if not x.startswith("_")])

if __name__ == "__main__":
    call_id = os.environ.get("CALL_ID")
    call_type = os.environ.get("CALL_TYPE", "default")
    exercise = os.environ.get("EXERCISE", "general")
    if not call_id:
        print("ERROR: CALL_ID missing"); exit(1)
    print(f"[RehabAI Agent] Starting — call_id={call_id} exercise={exercise}")
    asyncio.run(run_agent(call_id, call_type, exercise))
