"""
services/assistant_service.py
High-level Operix AI Assistant Service Facade.
"""
from __future__ import annotations

import time
from typing import List, Optional
from uuid import UUID

from ..config.settings import get_settings
from ..ingestion.text_processor import detect_language
from ..llm.context_manager import ConversationManager
from ..llm.grounding_guardrails import extract_citations, is_refusal_response
from ..llm.remediation_engine import RemediationEngine
from ..prompts.templates import (
    BASE_SYSTEM_PROMPT_AR,
    BASE_SYSTEM_PROMPT_EN,
    build_grounded_prompt,
)
from ..providers.llm_provider import ChatMessage, LLMProviderBase, get_llm_provider
from ..retrieval.retriever import KnowledgeRetriever
from ..schemas.contracts import (
    ActionExecutionRequest,
    ActionExecutionResponse,
    AssistantQueryRequest,
    AssistantQueryResponse,
    ProposedAction,
    RetrievalFilter,
    SourceCitation,
)
from .action_service import OperixActionService, get_action_service


class OperixAssistantService:
    """Production facade orchestrating RAG knowledge retrieval, LLM generation, and agentic actions."""

    def __init__(
        self,
        retriever: Optional[KnowledgeRetriever] = None,
        llm_provider: Optional[LLMProviderBase] = None,
        conversation_manager: Optional[ConversationManager] = None,
        action_service: Optional[OperixActionService] = None,
    ) -> None:
        self.retriever = retriever or KnowledgeRetriever()
        self.llm_provider = llm_provider or get_llm_provider()
        self.conversation_manager = conversation_manager or ConversationManager()
        self.action_service = action_service or get_action_service()

    def check_health(self) -> dict[str, str]:
        """Diagnostic health check."""
        return {
            "status": "healthy",
            "llm_provider": self.llm_provider.provider_name,
            "llm_model": self.llm_provider.model_name,
            "embedding_provider": getattr(self.retriever.embedding_provider, "model_name", "configured"),
            "indexed_chunks": str(self.retriever.vector_store.count()),
        }

    def ask(self, request: AssistantQueryRequest) -> AssistantQueryResponse:
        """
        Execute grounded RAG QA workflow.
        """
        start_time = time.perf_counter()
        settings = get_settings()

        # 1. Determine conversation ID
        conv_id = self.conversation_manager.get_or_create_id(request.conversation_id)

        # 2. Determine language
        detected_lang = detect_language(request.question)
        target_lang = detected_lang if request.language_preference == "auto" else request.language_preference

        # 3. Determine tenant scope (factory_id)
        factory_scope = (
            request.user_context.factory_id
            if request.user_context
            else settings.default_factory_id
        )

        # 4. Retrieve verified knowledge chunks
        search_filter = RetrievalFilter(
            factory_id=factory_scope,
            top_k=settings.top_k,
            min_similarity=settings.similarity_threshold,
        )
        retrieval_res = self.retriever.retrieve(request.question, search_filter=search_filter)

        # 5. Build system prompt & grounded user prompt
        system_prompt = BASE_SYSTEM_PROMPT_AR if target_lang == "ar" else BASE_SYSTEM_PROMPT_EN
        grounded_prompt = build_grounded_prompt(
            question=request.question,
            chunks=retrieval_res.chunks,
            language=target_lang,
        )

        # 6. Assemble conversational message chain
        messages: List[ChatMessage] = [ChatMessage(role="system", content=system_prompt)]
        # Append prior conversation turns if present
        messages.extend(self.conversation_manager.get_history(conv_id))
        # Append current grounded user turn
        messages.append(ChatMessage(role="user", content=grounded_prompt))

        # 7. Generate grounded response from LLM
        generated_answer = self.llm_provider.generate(messages, temperature=0.0)

        # 8. Check refusal / grounding status
        has_evidence = retrieval_res.has_sufficient_evidence and not is_refusal_response(generated_answer)
        citations = extract_citations(retrieval_res.chunks, generated_answer) if has_evidence else []

        # 9. Agentic Remediation & Action Proposals
        suggested_actions: List[ProposedAction] = []
        if has_evidence:
            suggested_actions = RemediationEngine.evaluate_actions(
                question=request.question,
                retrieved_chunks=retrieval_res.chunks,
                language=target_lang,
            )

        # 10. Update conversation history
        self.conversation_manager.add_turn(conv_id, request.question, generated_answer)

        duration = round(time.perf_counter() - start_time, 3)

        return AssistantQueryResponse(
            answer=generated_answer,
            conversation_id=conv_id,
            has_sufficient_evidence=has_evidence,
            citations=citations,
            suggested_actions=suggested_actions,
            provider=self.llm_provider.provider_name,
            model_name=self.llm_provider.model_name,
            language=target_lang,
            processing_time_seconds=duration,
        )

    def execute_action(self, request: ActionExecutionRequest) -> ActionExecutionResponse:
        """Execute an authorized remediation action."""
        return self.action_service.execute(request)

    def get_sources(self, query: str, factory_id: Optional[UUID] = None) -> List[SourceCitation]:
        """Fetch matching citations directly without generating a chat completion."""
        settings = get_settings()
        search_filter = RetrievalFilter(
            factory_id=factory_id or settings.default_factory_id,
            top_k=settings.top_k,
            min_similarity=settings.similarity_threshold,
        )
        res = self.retriever.retrieve(query, search_filter)
        return extract_citations(res.chunks, "")

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear conversation history for specified session."""
        return self.conversation_manager.clear(conversation_id)
