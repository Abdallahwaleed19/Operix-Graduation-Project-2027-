"""
scripts/run_assistant_demo.py
Interactive CLI demonstration of the Operix LLM / RAG Assistant.

Usage:
    python -m llm_rag_assistant.scripts.run_assistant_demo
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import UUID

# Add backend/ai-services to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from llm_rag_assistant.config.settings import get_settings
from llm_rag_assistant.providers.embedding_provider import MockEmbeddingProvider
from llm_rag_assistant.providers.llm_provider import MockLLMProvider
from llm_rag_assistant.retrieval.retriever import KnowledgeRetriever
from llm_rag_assistant.retrieval.vector_store import NumPyVectorStore
from llm_rag_assistant.schemas.contracts import AssistantQueryRequest, UserContext
from llm_rag_assistant.services.assistant_service import OperixAssistantService


def main() -> int:
    print("=" * 70)
    print("  Operix — Intelligent LLM / RAG Assistant Demonstration")
    print("=" * 70)

    settings = get_settings()

    # If in development without OpenAI key, use Mock provider for instant demo
    vector_store = NumPyVectorStore(storage_dir=settings.vector_store_dir)

    # Use mock providers for standalone demo predictability unless OpenAI key is set
    has_key = bool(settings.openai_api_key and not settings.openai_api_key.startswith("your_"))
    if has_key and settings.llm_provider == "openai":
        print("[*] Mode: Cloud OpenAI API")
        service = OperixAssistantService()
    else:
        print("[*] Mode: Offline Zero-Cost Mock Assistant (Grounded & Deterministic)")
        service = OperixAssistantService(
            retriever=KnowledgeRetriever(
                embedding_provider=MockEmbeddingProvider(),
                vector_store=vector_store,
            ),
            llm_provider=MockLLMProvider(),
        )

    health = service.check_health()
    print(f"[*] Health Check: {health['status'].upper()} (Indexed Chunks: {health['indexed_chunks']})")

    # Sample demo queries
    sample_queries = [
        (
            "English Safety Query",
            "What protective equipment and safety goggles are required in the welding area?",
            "en",
        ),
        (
            "Arabic Safety Query",
            "ما هي قواعد السلامة ومعدات الوقاية المعتمدة في منطقة اللحام؟",
            "ar",
        ),
        (
            "Incident Query",
            "What happened during the restricted zone intrusion incident?",
            "en",
        ),
        (
            "Out-of-Scope / Anti-Hallucination Query",
            "What is the secret chemical formula of the factory cafeteria coffee?",
            "en",
        ),
    ]

    user_ctx = UserContext(
        user_id=UUID("aaaaaaaa-0001-0001-0001-000000000001"),
        full_name="Abdallah Waleed",
        role_code="factory_admin",
        factory_id=settings.default_factory_id,
    )

    for title, q, lang in sample_queries:
        print("\n" + "-" * 70)
        print(f"[{title}]")
        print(f"User: \"{q}\"")
        req = AssistantQueryRequest(
            question=q,
            user_context=user_ctx,
            language_preference=lang,  # type: ignore
        )
        resp = service.ask(req)

        print(f"\nAssistant ({resp.provider} / {resp.model_name} | {resp.processing_time_seconds}s):")
        print(f"  {resp.answer}")
        print(f"\n  • Grounded Evidence Found: {resp.has_sufficient_evidence}")
        if resp.citations:
            print("  • Verified Source Citations:")
            for cit in resp.citations:
                print(f"    - [{cit.source_type}] {cit.source_title} (ID: {cit.source_id})")

    print("\n" + "=" * 70)
    print("Demonstration completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
