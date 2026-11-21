"""
llm/context_manager.py
In-memory session and conversation history manager with context-window trimming.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from ..config.settings import get_settings
from ..providers.llm_provider import ChatMessage


class ConversationManager:
    """Session-isolated conversation history tracker."""

    def __init__(self, max_turns: Optional[int] = None) -> None:
        self.max_turns = max_turns or get_settings().max_history_turns
        self._sessions: Dict[str, List[ChatMessage]] = {}

    def get_or_create_id(self, conversation_id: Optional[str] = None) -> str:
        """Return provided conversation_id or generate a new UUID."""
        return conversation_id.strip() if conversation_id and conversation_id.strip() else f"conv_{uuid.uuid4().hex[:12]}"

    def get_history(self, conversation_id: str) -> List[ChatMessage]:
        """Retrieve stored chat history for session."""
        return list(self._sessions.get(conversation_id, []))

    def add_turn(self, conversation_id: str, user_text: str, assistant_text: str) -> None:
        """Record a completed conversational turn and trim oldest turns if exceeding limit."""
        if conversation_id not in self._sessions:
            self._sessions[conversation_id] = []

        history = self._sessions[conversation_id]
        history.append(ChatMessage(role="user", content=user_text))
        history.append(ChatMessage(role="assistant", content=assistant_text))

        # Enforce max turns (each turn = 2 messages: user + assistant)
        max_messages = self.max_turns * 2
        if len(history) > max_messages:
            self._sessions[conversation_id] = history[-max_messages:]

    def clear(self, conversation_id: str) -> bool:
        """Clear session history."""
        if conversation_id in self._sessions:
            del self._sessions[conversation_id]
            return True
        return False
