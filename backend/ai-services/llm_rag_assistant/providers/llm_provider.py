"""
providers/llm_provider.py
Unified LLM provider interface supporting OpenAI Cloud, Ollama Local, and Mock mode.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, List, Optional

import httpx

from ..config.settings import get_settings


class ChatMessage:
    """Standard chat message."""

    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


class LLMProviderBase(ABC):
    """Abstract base class for Large Language Model generation."""

    @abstractmethod
    def generate(self, messages: List[ChatMessage], temperature: float = 0.0) -> str:
        """Generate grounded response given conversational messages."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class MockLLMProvider(LLMProviderBase):
    """
    Deterministic Mock LLM for automated tests and offline CI.
    Generates grounded answers reflecting retrieved context and enforces safety rules.
    """

    def __init__(self, model_name: str = "mock-gpt-safety-v1") -> None:
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    def generate(self, messages: List[ChatMessage], temperature: float = 0.0) -> str:
        user_prompt = ""
        for m in reversed(messages):
            if m.role == "user":
                user_prompt = m.content
                break

        # Check if verified context block exists and has content
        has_context = "--- BEGIN VERIFIED RETRIEVED CONTEXT ---" in user_prompt
        has_empty_marker = "NO VERIFIED RECORDS RETRIEVED" in user_prompt

        is_arabic = any("\u0600" <= c <= "\u06FF" for c in user_prompt)

        # If insufficient evidence
        if not has_context or has_empty_marker:
            if is_arabic:
                return "بناءً على السجلات المتوفرة في نظام Operix، لا توجد معلومات كافية للإجابة عن هذا السؤال."
            return "Based on the available Operix records, there is insufficient information to answer this question."

        # Extract source titles for grounding citation
        sources = []
        for line in user_prompt.split("\n"):
            if line.startswith("[Source "):
                sources.append(line.split("|")[0].strip("[] "))

        citation_tag = f" [المصدر: {', '.join(sources)}]" if is_arabic else f" [Source: {', '.join(sources)}]"

        if is_arabic:
            return f"بناءً على سجلات وقواعد السلامة الموثقة في المصنع، تم استخراج البيانات المطابقة بنجاح وفق الضوابط المعتمدة.{citation_tag}"
        return f"Based on verified Operix industrial records, the relevant safety protocols and operational metrics have been identified.{citation_tag}"


class OpenAILLMProvider(LLMProviderBase):
    """OpenAI Chat Completion provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        if not self._api_key:
            raise ValueError("OpenAI API key missing. Set OPENAI_API_KEY in .env.")
        self._model = model_name or settings.openai_chat_model
        self._timeout = timeout or settings.openai_timeout_seconds

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "openai"

    def generate(self, messages: List[ChatMessage], temperature: float = 0.0) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
        }

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI Chat API failed [{resp.status_code}]: {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()


class OllamaLLMProvider(LLMProviderBase):
    """Ollama Local Chat Completion provider."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model_name or settings.ollama_chat_model
        self._timeout = timeout or settings.ollama_timeout_seconds

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "ollama"

    def generate(self, messages: List[ChatMessage], temperature: float = 0.0) -> str:
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama chat generation failed [{resp.status_code}]: {resp.text}")
            data = resp.json()
            return data["message"]["content"].strip()


def get_llm_provider(name: Optional[str] = None) -> LLMProviderBase:
    """Factory creating configured LLM provider instance."""
    provider_type = (name or get_settings().llm_provider).lower()
    if provider_type == "openai":
        return OpenAILLMProvider()
    elif provider_type == "ollama":
        return OllamaLLMProvider()
    elif provider_type == "mock":
        return MockLLMProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}. Expected 'openai', 'ollama', or 'mock'.")
