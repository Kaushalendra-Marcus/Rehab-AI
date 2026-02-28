FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ pkg-config \
    libgl1 libglib2.0-0 \
    ffmpeg \
    libavformat-dev libavcodec-dev libavdevice-dev \
    libavutil-dev libswscale-dev libswresample-dev libavfilter-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir cython

COPY backend/ .

# Core packages
RUN pip install --no-cache-dir \
    fastapi "uvicorn[standard]" python-dotenv stream-chat \
    deepgram-sdk google-generativeai aiohttp python-multipart \
    websockets opencv-python-headless numpy pillow colorlog \
    pyee pyjwt requests aiofile dataclasses-json httpx marshmallow \
    protobuf pydantic-settings python-dateutil mcp \
    anthropic elevenlabs cartesia stratz

# CPU-only torch FIRST (prevents getstream[webrtc] from pulling CUDA torch)
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# PyAV for WebRTC
RUN pip install --no-cache-dir av

# aiortc
RUN pip install --no-cache-dir "aiortc>=1.13.0"

# getstream with webrtc+telemetry (TURN support)
RUN pip install --no-cache-dir "getstream[telemetry,webrtc]"

# daily-python
RUN pip install --no-cache-dir daily-python

# onnxruntime + ultralytics
RUN pip install --no-cache-dir onnxruntime ultralytics

# vision-agents plugins
RUN pip install --no-cache-dir \
    vision-agents-plugins-deepgram \
    vision-agents-plugins-elevenlabs \
    vision-agents-plugins-anthropic \
    vision-agents-plugins-cartesia \
    vision-agents-plugins-getstream

# vision-agents with deps, remove fal
RUN pip install --no-cache-dir vision-agents && \
    pip uninstall -y vision-agents-plugins-fal 2>/dev/null || true

CMD sh -c 'uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}'