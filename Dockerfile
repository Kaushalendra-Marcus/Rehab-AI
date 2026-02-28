FROM python:3.12-slim

WORKDIR /app

# System dependencies including FFmpeg for PyAV / aiortc
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir cython

COPY backend/ .

# Core packages
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    python-dotenv \
    stream-chat \
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
    cartesia \
    stratz

# av (PyAV) must be installed before aiortc/getstream
RUN pip install --no-cache-dir av

# aiortc and getstream with webrtc/telemetry
RUN pip install --no-cache-dir \
    "aiortc>=1.13.0" \
    "getstream[telemetry,webrtc]"

# daily-python separately
RUN pip install --no-cache-dir daily-python

# Ultralytics + onnxruntime
RUN pip install --no-cache-dir \
    onnxruntime \
    ultralytics

# Vision agents plugins
RUN pip install --no-cache-dir \
    vision-agents-plugins-deepgram \
    vision-agents-plugins-elevenlabs \
    vision-agents-plugins-anthropic \
    vision-agents-plugins-cartesia

RUN pip install --no-cache-dir --no-deps vision-agents

CMD uvicorn server:app --host 0.0.0.0 --port $PORT