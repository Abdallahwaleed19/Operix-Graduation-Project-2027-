"""
scripts/interactive_chat.py
Interactive CLI Chat session with Operix Industrial RAG Assistant.

Allows the user to type live queries in Arabic or English, inspect retrieved
chunks, source citations, grounding verification, and anti-hallucination refusals.

Usage:
    python -m llm_rag_assistant.scripts.interactive_chat
"""
from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

# Ensure root import path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from llm_rag_assistant.config.settings import get_settings
from llm_rag_assistant.providers.embedding_provider import (
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
    OllamaEmbeddingProvider,
)
from llm_rag_assistant.providers.llm_provider import (
    MockLLMProvider,
    OpenAILLMProvider,
    OllamaLLMProvider,
)
from llm_rag_assistant.retrieval.retriever import KnowledgeRetriever
from llm_rag_assistant.retrieval.vector_store import NumPyVectorStore
from llm_rag_assistant.schemas.contracts import AssistantQueryRequest, UserContext
from llm_rag_assistant.services.assistant_service import OperixAssistantService


def build_service() -> OperixAssistantService:
    settings = get_settings()
    vector_store = NumPyVectorStore(storage_dir=settings.vector_store_dir)
    vector_store.load()

    has_openai = bool(settings.openai_api_key and not settings.openai_api_key.startswith("your_"))

    if settings.llm_provider == "openai" and has_openai:
        print("[*] Active Engine: OpenAI Cloud (Grounded Live RAG)")
        retriever = KnowledgeRetriever(
            embedding_provider=OpenAIEmbeddingProvider(),
            vector_store=vector_store,
        )
        llm = OpenAILLMProvider()
    elif settings.llm_provider == "ollama":
        print("[*] Active Engine: Ollama Local (On-Premise Live RAG)")
        retriever = KnowledgeRetriever(
            embedding_provider=OllamaEmbeddingProvider(),
            vector_store=vector_store,
        )
        llm = OllamaLLMProvider()
    else:
        print("[*] Active Engine: Offline High-Speed Mock Engine (Deterministic & Zero-Cost)")
        retriever = KnowledgeRetriever(
            embedding_provider=MockEmbeddingProvider(),
            vector_store=vector_store,
        )
        llm = MockLLMProvider()

    return OperixAssistantService(retriever=retriever, llm_provider=llm)


def main() -> int:
    settings = get_settings()
    print("=" * 70)
    print("  Operix — Industrial Safety RAG Assistant (Live Interactive Chat)")
    print("=" * 70)
    print("Commands:")
    print("  - Type your question in Arabic or English (e.g. 'ما هي شروط منطقة اللحام؟')")
    print("  - Type 'exit' or 'quit' to end chat.")
    print("  - Type 'sources' to inspect all currently indexed sources.")
    print("=" * 70)

    service = build_service()
    health = service.check_health()
    print(f"[*] Status: {health['status'].upper()} | Indexed Chunks: {health['indexed_chunks']}\n")

    user_ctx = UserContext(
        user_id=UUID("aaaaaaaa-0001-0001-0001-000000000001"),
        full_name="Abdallah Waleed",
        role_code="safety_supervisor",
        factory_id=settings.default_factory_id,
    )
    session_id = "interactive-cli-session"

    while True:
        try:
            print("-" * 70)
            user_input = input("User (Operix) > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("\n[!] Exiting Operix Assistant. Stay safe!")
                break

            if user_input.lower() == "sources":
                chunks = getattr(service.retriever.vector_store, "_chunks", [])
                print(f"\n[*] Available Indexed Chunks ({len(chunks)} chunks):")
                seen = set()
                for c in chunks:
                    key = (c.metadata.source_type.value, c.metadata.source_title)
                    if key not in seen:
                        seen.add(key)
                        print(f"  • [{c.metadata.source_type.value}] {c.metadata.source_title}")
                continue

            req = AssistantQueryRequest(
                question=user_input,
                session_id=session_id,
                user_context=user_ctx,
                language_preference="auto",
            )

            resp = service.ask(req)

            print(f"\nOperix Assistant ({resp.provider}/{resp.model_name} | {resp.processing_time_seconds}s):")
            print(f"  {resp.answer}\n")

            print(f"  [Grounding Status] Evidence Found: {resp.has_sufficient_evidence}")
            if resp.citations:
                print("  [Verified Citations]:")
                for c in resp.citations:
                    page_str = f", Page {c.page_number}" if c.page_number else ""
                    stype = getattr(c.source_type, "value", str(c.source_type))
                    print(f"    - [{stype}] {c.source_title} (ID: {c.source_id}{page_str})")

        except KeyboardInterrupt:
            print("\n[!] Session interrupted.")
            break
        except Exception as exc:
            print(f"\n[ERROR] {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
