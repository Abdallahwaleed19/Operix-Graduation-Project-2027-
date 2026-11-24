"""
llm/context_manager.py
Thread-safe, ownership-enforced in-memory conversation history manager.

Every conversation is strictly owned by (factory_id, user_id, conversation_id).
Cross-user or cross-factory access to an existing conversation_id raises
ConversationOwnershipError and never silently creates or leaks history.
"""
from __future__ import annotations

import threading
import uuid
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from ..config.settings import get_settings
from ..providers.llm_provider import ChatMessage


class ConversationOwnershipError(PermissionError):
    """Raised when a caller attempts to access or modify a conversation they do not own."""


class ConversationManager:
    """Thread-safe, factory- and user-isolated conversation history tracker."""

    def __init__(self, max_turns: Optional[int] = None) -> None:
        self.max_turns = max_turns or get_settings().max_history_turns
        self._lock = threading.RLock()
        self._sessions: Dict[Tuple[str, str, str], List[ChatMessage]] = {}
        self._owners: Dict[str, Tuple[str, str]] = {}

    @staticmethod
    def _normalize_owner(factory_id: UUID | str | None, user_id: UUID | str | None) -> Tuple[str, str]:
        if factory_id is None or user_id is None:
            raise ConversationOwnershipError(
                "Authenticated factory_id and user_id are required for conversation access."
            )
        fid = str(factory_id).strip()
        uid = str(user_id).strip()
        if not fid or not uid:
            raise ConversationOwnershipError(
                "Authenticated factory_id and user_id must be non-empty."
            )
        return (fid, uid)

    def _assert_ownership(self, conversation_id: str, owner: Tuple[str, str]) -> None:
        existing_owner = self._owners.get(conversation_id)
        if existing_owner is not None and existing_owner != owner:
            raise ConversationOwnershipError(
                f"Access denied: conversation '{conversation_id}' belongs to another user or factory."
            )

    def get_or_create_id(
        self,
        conversation_id: Optional[str] = None,
        factory_id: UUID | str | None = None,
        user_id: UUID | str | None = None,
    ) -> str:
        """
        Return validated conversation_id or generate a new one bound to (factory_id, user_id).
        Raises ConversationOwnershipError if conversation_id belongs to another owner.
        """
        owner = self._normalize_owner(factory_id, user_id)
        with self._lock:
            if conversation_id and conversation_id.strip():
                conv_id = conversation_id.strip()
                self._assert_ownership(conv_id, owner)
                self._owners.setdefault(conv_id, owner)
                return conv_id
            conv_id = f"conv_{uuid.uuid4().hex[:12]}"
            self._owners[conv_id] = owner
            return conv_id

    def get_history(
        self,
        conversation_id: str,
        factory_id: UUID | str | None = None,
        user_id: UUID | str | None = None,
    ) -> List[ChatMessage]:
        """Retrieve stored chat history for an owned session."""
        owner = self._normalize_owner(factory_id, user_id)
        with self._lock:
            self._assert_ownership(conversation_id, owner)
            key = (owner[0], owner[1], conversation_id)
            return list(self._sessions.get(key, []))

    def add_turn(
        self,
        conversation_id: str,
        user_text: str,
        assistant_text: str,
        factory_id: UUID | str | None = None,
        user_id: UUID | str | None = None,
    ) -> None:
        """Record a completed conversational turn for an owned session and trim oldest turns."""
        owner = self._normalize_owner(factory_id, user_id)
        with self._lock:
            self._assert_ownership(conversation_id, owner)
            self._owners.setdefault(conversation_id, owner)
            key = (owner[0], owner[1], conversation_id)
            if key not in self._sessions:
                self._sessions[key] = []

            history = self._sessions[key]
            history.append(ChatMessage(role="user", content=user_text))
            history.append(ChatMessage(role="assistant", content=assistant_text))

            max_messages = self.max_turns * 2
            if len(history) > max_messages:
                self._sessions[key] = history[-max_messages:]

    def clear(
        self,
        conversation_id: str,
        factory_id: UUID | str | None = None,
        user_id: UUID | str | None = None,
    ) -> bool:
        """Clear session history after validating (factory_id, user_id) ownership."""
        owner = self._normalize_owner(factory_id, user_id)
        with self._lock:
            self._assert_ownership(conversation_id, owner)
            key = (owner[0], owner[1], conversation_id)
            existed = key in self._sessions or conversation_id in self._owners
            self._sessions.pop(key, None)
            if self._owners.get(conversation_id) == owner:
                self._owners.pop(conversation_id, None)
            return existed
