FROM python:3.12-slim

WORKDIR /app

# Minimal system deps - only runtime libs, no dev headers
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

# Core packages (no torch yet)
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

# Install getstream WITHOUT [telemetry,webrtc] extras — avoids torch + torchaudio (~3GB saved)
RUN pip install --no-cache-dir getstream

# av (PyAV) then aiortc
RUN pip install --no-cache-dir av
RUN pip install --no-cache-dir "aiortc>=1.13.0"

# daily-python
RUN pip install --no-cache-dir daily-python

# Install CPU-only torch explicitly BEFORE ultralytics (prevents full CUDA torch download)
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# onnxruntime + ultralytics (will reuse torch above)
RUN pip install --no-cache-dir onnxruntime ultralytics

# Vision agents plugins
RUN pip install --no-cache-dir \
    vision-agents-plugins-deepgram \
    vision-agents-plugins-elevenlabs \
    vision-agents-plugins-anthropic \
    vision-agents-plugins-cartesia

RUN pip install --no-cache-dir --no-deps vision-agents

CMD sh -c "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"