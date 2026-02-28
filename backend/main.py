"""
RehabAI - Main entry point
This file starts the FastAPI server.

Run: uv run uvicorn main:app --reload --port 8000
  OR: uv run python main.py
"""

import uvicorn
from server import app  # import the FastAPI app from server.py

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )