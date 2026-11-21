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
from llm_rag_assistant.schemas.contracts import (
    ActionExecutionRequest,
    AssistantQueryRequest,
    ProposedAction,
    UserContext,
)
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
    print("  - Type 'exec <num>' or 'نفذ <num>' to authorize and execute a proposed action.")
    print("  - Type 'sources' to inspect all currently indexed sources.")
    print("  - Type 'exit' or 'quit' to end chat.")
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
    last_actions: list[ProposedAction] = []

    while True:
        try:
            print("-" * 70)
            user_input = input("User (Operix) > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("\n[!] Exiting Operix Assistant. Stay safe!")
                break

            # Handle Action Execution Command: 'exec 1' or 'نفذ 1'
            exec_match = None
            for prefix in ("exec", "act", "نفذ", "طبق", "execute"):
                if user_input.lower().startswith(prefix):
                    parts = user_input.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        exec_match = int(parts[1]) - 1
                    break

            if exec_match is not None:
                if not last_actions or exec_match < 0 or exec_match >= len(last_actions):
                    print(f"\n[!] Invalid action index. Available actions count: {len(last_actions)}")
                else:
                    selected_act = last_actions[exec_match]
                    print(f"\n[*] Executing Authorized Action: [{selected_act.title}]...")
                    exec_res = service.execute_action(
                        ActionExecutionRequest(
                            action_id=selected_act.action_id,
                            action_type=selected_act.action_type,
                            parameters=selected_act.parameters,
                            confirmed_by=user_ctx.full_name,
                            factory_id=user_ctx.factory_id,
                        )
                    )
                    print(f"\n[SUCCESS - ACTION EXECUTED]")
                    print(f"  • Status          : {exec_res.status.upper()}")
                    print(f"  • Audit Reference : {exec_res.audit_reference}")
                    print(f"  • Message         : {exec_res.message}")
                    print(f"  • Details         : {exec_res.details}\n")
                continue

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
            last_actions = resp.suggested_actions

            print(f"\nOperix Assistant ({resp.provider}/{resp.model_name} | {resp.processing_time_seconds}s):")
            print(f"  {resp.answer}\n")

            print(f"  [Grounding Status] Evidence Found: {resp.has_sufficient_evidence}")
            if resp.citations:
                print("  [Verified Citations]:")
                for c in resp.citations:
                    page_str = f", Page {c.page_number}" if c.page_number else ""
                    stype = getattr(c.source_type, "value", str(c.source_type))
                    print(f"    - [{stype}] {c.source_title} (ID: {c.source_id}{page_str})")

            # Display Suggested Agentic Actions if available
            if resp.suggested_actions:
                is_ar = resp.language == "ar"
                hdr = "إجراءات تصحيحية مقترحة (اكتب 'نفذ 1' أو 'exec 1' للتنفيذ الآن):" if is_ar else "Suggested Remediation Actions (Type 'exec 1' to authorize):"
                print(f"\n  [AGENTIC ACTIONS] {hdr}")
                for idx, act in enumerate(resp.suggested_actions, 1):
                    sev_badge = f"[{act.severity.upper()}]"
                    print(f"    {idx}. {sev_badge} {act.title}")
                    print(f"       -> {act.description}")

        except KeyboardInterrupt:
            print("\n[!] Session interrupted.")
            break
        except Exception as exc:
            print(f"\n[ERROR] {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
