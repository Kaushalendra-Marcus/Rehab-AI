"""
RehabAI - Debug / diagnostic script
Run: uv run python debug_agent.py
To test a live call: CALL_ID=rehab-XXXX uv run python debug_agent.py
"""
import asyncio
import os
import pkgutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# ---------------------------------------------------------------------------
# STEP 1 — Check .env keys
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 1: Checking .env keys")
print("=" * 60)
for k in [
    "STREAM_API_KEY",
    "STREAM_API_SECRET",
    "GOOGLE_API_KEY",
    "ANTHROPIC_API_KEY",
    "ELEVENLABS_API_KEY",
    "DEEPGRAM_API_KEY",
]:
    v = os.environ.get(k, "")
    if v and not v.startswith("your_"):
        print(f"  ✅ {k} = {v[:10]}...")
    else:
        print(f"  ❌ {k} = MISSING or placeholder!")


# ---------------------------------------------------------------------------
# STEP 2 — Test imports and discover available components
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 2: Testing imports & discovering vision_agents structure")
print("=" * 60)

try:
    from vision_agents.core import Agent, User
    print("  ✅ vision_agents.core: Agent, User")
except Exception as e:
    print(f"  ❌ vision_agents.core: {e}")
    exit(1)

# List available plugins
try:
    import vision_agents.plugins as _p
    plugins = [m.name for m in pkgutil.iter_modules(_p.__path__)]
    print(f"  ✅ Available plugins: {plugins}")
except Exception as e:
    print(f"  ❌ plugins discovery failed: {e}")

# Discover edge classes
try:
    from vision_agents.core import edge as _edge_mod
    edge_members = [x for x in dir(_edge_mod) if not x.startswith("_")]
    print(f"  ✅ core.edge members: {edge_members}")
except Exception as e:
    print(f"  ❌ core.edge: {e}")

# Discover LLM classes
try:
    from vision_agents.core import llm as _llm_mod
    llm_members = [x for x in dir(_llm_mod) if not x.startswith("_")]
    print(f"  ✅ core.llm members: {llm_members}")
except Exception as e:
    print(f"  ❌ core.llm: {e}")

# Available confirmed plugins
try:
    from vision_agents.plugins import deepgram
    print("  ✅ plugins.deepgram imported")
except Exception as e:
    print(f"  ❌ plugins.deepgram: {e}")

try:
    from vision_agents.plugins import elevenlabs
    print("  ✅ plugins.elevenlabs imported")
except Exception as e:
    print(f"  ❌ plugins.elevenlabs: {e}")

try:
    from vision_agents.plugins import anthropic
    print("  ✅ plugins.anthropic imported")
except Exception as e:
    print(f"  ❌ plugins.anthropic: {e}")


# ---------------------------------------------------------------------------
# STEP 3 — Create Agent inside async
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 3: Creating Agent object (inside async)")
print("=" * 60)

async def test_create_agent():
    from vision_agents.core import Agent, User, edge as _edge_mod
    from vision_agents.plugins import deepgram, elevenlabs, anthropic
    from getstream import AsyncStream

    api_key    = os.environ.get("STREAM_API_KEY", "")
    api_secret = os.environ.get("STREAM_API_SECRET", "")
    stream_client = AsyncStream(api_key=api_key, api_secret=api_secret)

    # Find edge
    edge = None
    for cls_name in ["GetStreamEdge", "StreamEdge", "Edge", "GetStream"]:
        cls = getattr(_edge_mod, cls_name, None)
        if cls:
            try:
                edge = cls(client=stream_client)
            except TypeError:
                edge = cls()
                edge.client = stream_client
            print(f"  ✅ Edge: core.edge.{cls_name}")
            break

    if edge is None:
        print(f"  ❌ No edge class found in: {[x for x in dir(_edge_mod) if not x.startswith('_')]}")
        return None

    # Find LLM
    from vision_agents.core import llm as _llm_mod
    llm = None
    for cls_name in ["GeminiLLM", "Gemini", "GoogleLLM", "GoogleGeminiLLM"]:
        cls = getattr(_llm_mod, cls_name, None)
        if cls:
            llm = cls(model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))
            print(f"  ✅ LLM: core.llm.{cls_name}")
            break
    if llm is None:
        llm = anthropic.LLM(model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5"))
        print(f"  ✅ LLM: anthropic (fallback)")

    stt = deepgram.STT(model="nova-2")
    tts = elevenlabs.TTS()
    print(f"  ✅ STT: deepgram nova-2")
    print(f"  ✅ TTS: elevenlabs")

    try:
        agent = Agent(
            edge=edge,
            agent_user=User(name="REHAB AI", id="rehab-ai-agent"),
            instructions="You are a rehab coach.",
            llm=llm,
            stt=stt,
            tts=tts,
        )
        print("  ✅ Agent created successfully!")
        return agent
    except Exception as e:
        import traceback
        print(f"  ❌ Agent creation failed: {e}")
        traceback.print_exc()
        return None

agent = asyncio.run(test_create_agent())
if agent is None:
    exit(1)


# ---------------------------------------------------------------------------
# STEP 4 — Optionally join a live call
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 4: Join live call (optional)")
print("=" * 60)

call_id = os.environ.get("CALL_ID", "")
if not call_id:
    print("  ⚠️  No CALL_ID set — skipping join test.")
    print("  To test: start a session in the browser, copy the call_id from")
    print("  server logs, then run:  CALL_ID=rehab-XXXX uv run python debug_agent.py")
else:
    print(f"  Testing join for call_id={call_id}")

    async def test_join():
        from vision_agents.core import Agent, User, edge as _edge_mod
        from vision_agents.plugins import deepgram, elevenlabs, anthropic
        from vision_agents.core import llm as _llm_mod
        from getstream import AsyncStream

        api_key    = os.environ.get("STREAM_API_KEY", "")
        api_secret = os.environ.get("STREAM_API_SECRET", "")
        stream_client = AsyncStream(api_key=api_key, api_secret=api_secret)

        EdgeCls = next(
            (getattr(_edge_mod, n) for n in ["GetStreamEdge", "StreamEdge", "Edge"] if hasattr(_edge_mod, n)),
            None
        )
        try:
            edge = EdgeCls(client=stream_client)
        except TypeError:
            edge = EdgeCls()
            edge.client = stream_client

        LLMCls = next(
            (getattr(_llm_mod, n) for n in ["GeminiLLM", "Gemini", "GoogleLLM"] if hasattr(_llm_mod, n)),
            None
        )
        llm = LLMCls(model="gemini-2.5-flash") if LLMCls else anthropic.LLM(model="claude-opus-4-5")

        agent = Agent(
            edge=edge,
            agent_user=User(name="REHAB AI", id="rehab-ai-agent"),
            instructions="You are a rehab coach.",
            llm=llm,
            stt=deepgram.STT(model="nova-2"),
            tts=elevenlabs.TTS(),
        )
        try:
            call = await agent.create_call("default", call_id)
            print("  ✅ create_call succeeded")
            async with agent.join(call):
                print("  ✅ Joined call!")
                await agent.simple_response("REHAB AI online. Debug test successful.")
                print("  ✅ simple_response sent!")
                await agent.finish()
        except Exception as e:
            import traceback
            print(f"  ❌ Join failed: {e}")
            traceback.print_exc()

    asyncio.run(test_join())

print("\n✅ Debug complete.")