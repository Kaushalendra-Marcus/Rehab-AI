FROM python:3.12-slim

WORKDIR /app

# System dependencies - minimal
RUN apt-get update && apt-get install -y \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/ .

# Core packages first (fast)
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    python-dotenv \
    stream-chat \
    getstream \
    deepgram-sdk \
    google-generativeai \
    aiohttp \
    python-multipart \
    websockets \
    opencv-python-headless \
    numpy \
    pillow \
    colorlog \
    pyee \
    pyjwt \
    requests \
    aiofile \
    dataclasses-json \
    httpx \
    marshmallow \
    protobuf \
    pydantic-settings \
    python-dateutil \
    mcp \
    anthropic \
    elevenlabs \
    cartesia

# Heavy packages separately (so cache works if above didn't change)
RUN pip install --no-cache-dir \
    "aiortc>=1.13.0" \
    daily-python \
    stratz

# ultralytics without full torch (much smaller)
RUN pip install --no-cache-dir \
    onnxruntime \
    ultralytics --extra-index-url https://download.pytorch.org/whl/cpu

# Vision agents plugins
RUN pip install --no-cache-dir \
    vision-agents-plugins-deepgram \
    vision-agents-plugins-elevenlabs \
    vision-agents-plugins-anthropic \
    vision-agents-plugins-cartesia

RUN pip install --no-cache-dir --no-deps vision-agents

CMD uvicorn server:app --host 0.0.0.0 --port $PORT