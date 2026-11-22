"""
app/core/logging.py
Structured logging configuration for Operix Main Backend.
"""
import logging
import sys
from .config import settings


def setup_logging() -> None:
    """Configure root logger with consistent formatting."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    log_format = (
        "[%(asctime)s] [%(levelname)s] [%(name)s] "
        "[%(filename)s:%(lineno)d]: %(message)s"
    )

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Silence excessively verbose third-party loggers in dev
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger("operix")
