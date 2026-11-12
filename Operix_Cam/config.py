"""
config.py — Operix Camera Configuration Loader
Loads settings from .env (or falls back to safe defaults).
Keeps every IP/URL in one place so the demo network can be changed in seconds.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve the .env file relative to this config.py so it works regardless of
# the working directory the script is launched from.
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

# ---------------------------------------------------------------------------
# Stream
# ---------------------------------------------------------------------------
RTSP_URL: str = os.getenv("RTSP_URL", "rtsp://192.168.1.9:554/md0_0")

# Force TCP transport to prevent packet loss / frame tearing over Wi-Fi.
# FFmpeg reads these before opening any RTSP connection.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
DISPLAY_WIDTH: int  = int(os.getenv("DISPLAY_WIDTH",  "1280"))
DISPLAY_HEIGHT: int = int(os.getenv("DISPLAY_HEIGHT", "720"))
WINDOW_TITLE: str   = "Operix — Live Camera Feed"

# ---------------------------------------------------------------------------
# Reconnection
# ---------------------------------------------------------------------------
RECONNECT_DELAY: int = int(os.getenv("RECONNECT_DELAY", "3"))   # seconds
