"""
run.py
Convenient CLI entrypoint to launch the Operix FastAPI backend with Uvicorn.
Usage (Windows PowerShell):
    python run.py
"""
import sys
from pathlib import Path

# Add backend directory and ai-services to PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "ai-services"))

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
