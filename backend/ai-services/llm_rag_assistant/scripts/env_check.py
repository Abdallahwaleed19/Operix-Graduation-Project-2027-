"""
scripts/env_check.py
Diagnostic tool for checking the Operix LLM/RAG Assistant environment and prerequisites.

Run from backend/ai-services/:
    python -m llm_rag_assistant.scripts.env_check
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add backend/ai-services to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from llm_rag_assistant.config.settings import get_settings


def check_python_environment() -> bool:
    print(f"[*] Python Version         : {sys.version.split()[0]} ({'OK' if sys.version_info >= (3, 10) else 'FAIL'})")
    return sys.version_info >= (3, 10)


def check_database_access(settings) -> bool:
    print(f"[*] Database URL           : {settings.database_url.split('@')[-1] if '@' in settings.database_url else 'CONFIGURED'}")
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(settings.database_url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            rules_count = conn.execute(text("SELECT COUNT(*) FROM safety_rules")).scalar()
            incidents_count = conn.execute(text("SELECT COUNT(*) FROM incidents")).scalar()
            print(f"    - PostgreSQL Status    : CONNECTED (operix_db read-only check)")
            print(f"    - Safety Rules Found   : {rules_count}")
            print(f"    - Incidents Found      : {incidents_count}")
            return True
    except Exception as exc:
        print(f"    - PostgreSQL Status    : FAILED ({exc})")
        return False


def check_vector_extension(settings) -> bool:
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            has_pgvector = conn.execute(text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'")).scalar()
            print(f"[*] pgvector Extension     : {'INSTALLED in operix_db' if has_pgvector else 'NOT INSTALLED (Using Isolated Vector Store)'}")
            return bool(has_pgvector)
    except Exception:
        print(f"[*] pgvector Extension     : UNKNOWN")
        return False


def check_openai_status(settings) -> bool:
    has_key = bool(settings.openai_api_key and not settings.openai_api_key.startswith("your_"))
    print(f"[*] OpenAI API Key         : {'CONFIGURED' if has_key else 'NOT CONFIGURED (Optional in mock/local mode)'}")
    print(f"    - Chat Model           : {settings.openai_chat_model}")
    print(f"    - Embedding Model      : {settings.openai_embedding_model}")
    return has_key


def check_ollama_status(settings) -> bool:
    print(f"[*] Ollama Base URL        : {settings.ollama_base_url}")
    print(f"    - Chat Model           : {settings.ollama_chat_model}")
    print(f"    - Embedding Model      : {settings.ollama_embedding_model}")
    try:
        import urllib.request
        req = urllib.request.Request(f"{settings.ollama_base_url}/api/tags", headers={"User-Agent": "OperixEnvCheck"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print(f"    - Ollama Service       : REACHABLE (Local Ollama is running)")
                return True
    except Exception:
        print(f"    - Ollama Service       : NOT REACHABLE (Local Ollama is currently offline/not running)")
    return False


def check_python_packages() -> dict[str, bool]:
    packages = ["pydantic", "sqlalchemy", "numpy", "pypdf", "fitz", "httpx", "dotenv"]
    results = {}
    print("[*] Required Core Packages:")
    for pkg in packages:
        try:
            __import__(pkg)
            results[pkg] = True
            print(f"    - {pkg:<15} : INSTALLED")
        except ImportError:
            results[pkg] = False
            print(f"    - {pkg:<15} : MISSING")
    return results


def main() -> int:
    print("=" * 70)
    print("  Operix LLM/RAG Assistant — Pre-Flight Environment Diagnostic")
    print("=" * 70)

    settings = get_settings()
    check_python_environment()
    check_python_packages()
    check_database_access(settings)
    check_vector_extension(settings)
    check_openai_status(settings)
    check_ollama_status(settings)

    print("=" * 70)
    print("Diagnostic complete. Initial configuration verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
