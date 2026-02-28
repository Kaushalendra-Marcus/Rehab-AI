FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    pkg-config \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/ .

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    python-dotenv \
    stream-chat \
    "getstream[telemetry,webrtc]" \
    deepgram-sdk \
    google-generativeai \
    ultralytics \
    aiohttp \
    python-multipart \
    websockets \
    "aiortc>=1.13.0" \
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
    onnxruntime \
    mcp \
    daily-python \
    stratz \
    anthropic \
    elevenlabs \
    cartesia

RUN pip install --no-cache-dir \
    vision-agents-plugins-deepgram \
    vision-agents-plugins-elevenlabs \
    vision-agents-plugins-anthropic \
    vision-agents-plugins-cartesia

RUN pip install --no-cache-dir --no-deps vision-agents

CMD uvicorn server:app --host 0.0.0.0 --port $PORT