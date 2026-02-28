FROM python:3.12-slim

WORKDIR /app

# System dependencies for aiortc, ultralytics
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

# Copy backend files
COPY backend/ .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Start server
CMD uvicorn server:app --host 0.0.0.0 --port $PORT