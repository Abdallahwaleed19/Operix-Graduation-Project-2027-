"""
tests/conftest.py
Pytest test fixtures and configuration.
"""
import sys
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(BACKEND_DIR / "ai-services") not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR / "ai-services"))

from app.main import create_application
from app.core.config import Settings, get_settings


@pytest.fixture(scope="session")
def app():
    """Create a fresh FastAPI app instance for testing."""
    return create_application()


@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """Test client yielding synchronous HTTP requests."""
    test_client = TestClient(app)
    yield test_client
