"""
RehabAI - Debug / diagnostic script
Run: uv run python debug_agent.py
To test a live call: CALL_ID=rehab-XXXX uv run python debug_agent.py
"""
import asyncio
import os
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
    "ELEVENLABS_API_KEY",
    "DEEPGRAM_API_KEY",
]:
    v = os.environ.get(k, "")
    if v and not v.startswith("your_"):
        print(f"  ✅ {k} = {v[:10]}...")
    else:
        print(f"  ❌ {k} = MISSING or placeholder!")


# ---------------------------------------------------------------------------
# STEP 2 — Test imports
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 2: Testing imports")
print("=" * 60)
try:
    from vision_agents.core import Agent, User
    print("  ✅ vision_agents.core")
    from vision_agents.plugins import getstream, gemini, deepgram, elevenlabs, ultralytics
    print("  ✅ all plugins imported")
except Exception as e:
    import traceback
    print(f"  ❌ Import error: {e}")
    traceback.print_exc()
    exit(1)


# ---------------------------------------------------------------------------
# STEP 3 — Create Agent inside async (required — EventManager needs event loop)
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 3: Creating Agent object (inside async)")
print("=" * 60)

async def test_create_agent():
    try:
        agent = Agent(
            # ✅ Edge() MUST be created inside an async function
            edge=getstream.Edge(),
            agent_user=User(name="REHAB AI", id="rehab-ai-agent"),
            instructions="You are a rehab coach.",
            llm=gemini.LLM(model="gemini-2.5-flash"),
            processors=[
                ultralytics.YOLOPoseProcessor(
                    model_path="yolo11n-pose.pt",
                    device="cpu",
                    conf_threshold=0.5,
                    # draw_skeleton removed — not a valid param
                )
            ],
            stt=deepgram.STT(model="nova-3"),
            tts=elevenlabs.TTS(
                voice_id="onwK4e9ZLuTAKqWW03F9",
                model_id="eleven_turbo_v2_5",
            ),
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
        # Must re-create agent inside this async context
        from vision_agents.plugins import getstream, gemini, deepgram, elevenlabs, ultralytics
        from vision_agents.core import Agent, User

        agent = Agent(
            edge=getstream.Edge(),
            agent_user=User(name="REHAB AI", id="rehab-ai-agent"),
            instructions="You are a rehab coach.",
            llm=gemini.LLM(model="gemini-2.5-flash"),
            processors=[
                ultralytics.YOLOPoseProcessor(
                    model_path="yolo11n-pose.pt",
                    device="cpu",
                    conf_threshold=0.5,
                )
            ],
            stt=deepgram.STT(model="nova-3"),
            tts=elevenlabs.TTS(
                voice_id="onwK4e9ZLuTAKqWW03F9",
                model_id="eleven_turbo_v2_5",
            ),
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