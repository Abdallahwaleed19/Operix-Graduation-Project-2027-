"""
providers/embedding_provider.py
Embedding provider abstraction supporting OpenAI Cloud, Ollama Local, and Mock mode.
"""
from __future__ import annotations

import hashlib
import logging
import math
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx
import numpy as np

from ..config.settings import get_settings

logger = logging.getLogger("EmbeddingProvider")


class EmbeddingProviderBase(ABC):
    """Abstract base class for text embedding generation."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Embed a batch of texts into an array of shape (N, dimension).
        """
        pass

    @abstractmethod
    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a single search query into a vector of shape (dimension,).
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier."""
        pass


COMMON_STOP_WORDS = {
    "what", "is", "the", "for", "in", "a", "an", "and", "or", "of", "to", "at",
    "by", "with", "from", "on", "are", "be", "this", "that", "it", "as", "was",
    "which", "how", "many", "all", "any", "some", "about",
    "هل", "ما", "ماذا", "من", "في", "على", "إلى", "عن", "مع", "هو", "هي", "التي", "الذي", "كم",
}

DOMAIN_KEYWORDS = {
    "ppe", "welding", "safety", "rule", "rules", "incident", "incidents", "hazard", "hazardous",
    "camera", "cameras", "zone", "zones", "intrusion", "fatigue", "fall", "goggles", "helmet",
    "boots", "downtime", "department", "departments", "warehouse", "maintenance", "loto",
    "outage", "stream", "resolved", "critical", "severity", "protocol", "violation", "violations",
    "equipment", "protective", "inactive", "transit", "lane", "forklift",
# Arabic domain keywords
    "لحام", "سلامة", "وقاية", "خوذة", "نظارات", "كاميرا", "كاميرات", "حادث", "حوادث", "مخالفة",
    "مخالفات", "منطقة", "مناطق", "رافعات", "شوكية", "صيانة", "أمان", "مستودع", "توقف", "عطل",
    "إجراءات", "شروط", "خطرة", "شخصية",
}

ARABIC_CROSS_LINGUAL_SYNONYMS = {
    "لحام": "welding",
    "سلامة": "safety",
    "وقاية": "ppe",
    "خوذة": "helmet",
    "نظارات": "goggles",
    "كاميرا": "camera",
    "كاميرات": "cameras",
    "حادث": "incident",
    "حوادث": "incidents",
    "مخالفة": "violation",
    "مخالفات": "violations",
    "منطقة": "zone",
    "مناطق": "zones",
    "رافعات": "forklift",
    "شوكية": "forklift",
    "صيانة": "maintenance",
    "أمان": "safety",
    "مستودع": "warehouse",
    "عطل": "downtime",
    "شخصية": "ppe",
}


class MockEmbeddingProvider(EmbeddingProviderBase):
    """
    Deterministic pseudo-embedding provider for offline testing and CI.
    Uses token-hashing term-frequency vectorization with domain keyword boosting
    and stop-word pruning, normalized to unit length.
    """

    def __init__(self, dimension: int = 384, model_name: str = "mock-embed-v1") -> None:
        self._dim = dimension
        self._model_name = model_name

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    def _hash_to_vector(self, text: str) -> np.ndarray:
        vec = np.zeros(self._dim, dtype=np.float32)
        words = [
            w.lower().strip(".,!?:;\"'()[]{}؟—-_")
            for w in text.split()
            if len(w) > 1 and w.lower() not in COMMON_STOP_WORDS
        ]

        if not words:
            return vec

        for raw_w in words:
            idx = int(hashlib.md5(raw_w.encode("utf-8")).hexdigest()[:8], 16) % self._dim
            weight = 5.0 if raw_w in DOMAIN_KEYWORDS else 1.0
            vec[idx] += weight

            # Arabic stemming / prefix removal for offline mock cross-lingual retrieval
            norm_w = raw_w
            if any("\u0600" <= c <= "\u06FF" for c in norm_w):
                if norm_w.startswith("ال") and len(norm_w) > 3:
                    norm_w = norm_w[2:]
                elif norm_w.startswith("وال") and len(norm_w) > 4:
                    norm_w = norm_w[3:]
                elif norm_w.startswith("بال") and len(norm_w) > 4:
                    norm_w = norm_w[3:]
                elif norm_w.startswith("ب") and len(norm_w) > 2:
                    norm_w = norm_w[1:]
                elif norm_w.startswith("و") and len(norm_w) > 2:
                    norm_w = norm_w[1:]

            synonym = ARABIC_CROSS_LINGUAL_SYNONYMS.get(norm_w) or ARABIC_CROSS_LINGUAL_SYNONYMS.get(raw_w)
            if synonym:
                syn_idx = int(hashlib.md5(synonym.encode("utf-8")).hexdigest()[:8], 16) % self._dim
                vec[syn_idx] += 10.0

        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dim), dtype=np.float32)
        vectors = [self._hash_to_vector(t) for t in texts]
        return np.vstack(vectors)

    def embed_query(self, query: str) -> np.ndarray:
        return self._hash_to_vector(query)


class OpenAIEmbeddingProvider(EmbeddingProviderBase):
    """OpenAI Cloud embedding provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        if not self._api_key:
            raise ValueError("OpenAI API key is missing. Set OPENAI_API_KEY in .env.")
        self._model = model_name or settings.openai_embedding_model
        self._timeout = timeout or settings.openai_timeout_seconds
        # text-embedding-3-small dimension is 1536
        self._dim = 1536 if "small" in self._model else 3072

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dim), dtype=np.float32)

        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"input": texts, "model": self._model}

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI Embedding API failed [{resp.status_code}]: {resp.text}")
            data = resp.json()

        sorted_items = sorted(data["data"], key=lambda x: x["index"])
        embeddings = [item["embedding"] for item in sorted_items]
        arr = np.array(embeddings, dtype=np.float32)
        # Normalize to unit length
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        return arr / np.where(norms == 0, 1, norms)

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed_texts([query])[0]


class OllamaEmbeddingProvider(EmbeddingProviderBase):
    """Ollama Local embedding provider."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model_name or settings.ollama_embedding_model
        self._timeout = timeout or settings.ollama_timeout_seconds
        self._dim = 768  # nomic-embed-text standard dimension

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dim), dtype=np.float32)

        url = f"{self._base_url}/api/embeddings"
        vectors: List[List[float]] = []

        with httpx.Client(timeout=self._timeout) as client:
            for text in texts:
                resp = client.post(url, json={"model": self._model, "prompt": text})
                if resp.status_code != 200:
                    raise RuntimeError(f"Ollama embedding failed [{resp.status_code}]: {resp.text}")
                vectors.append(resp.json()["embedding"])

        arr = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        return arr / np.where(norms == 0, 1, norms)

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed_texts([query])[0]


def get_embedding_provider(name: Optional[str] = None) -> EmbeddingProviderBase:
    """Factory creating configured embedding provider instance."""
    provider_type = (name or get_settings().embedding_provider).lower()
    if provider_type == "openai":
        try:
            return OpenAIEmbeddingProvider()
        except ValueError:
            logger.warning("OPENAI_API_KEY not configured. Falling back to MockEmbeddingProvider for offline/dev operation.")
            return MockEmbeddingProvider()
    elif provider_type == "ollama":
        return OllamaEmbeddingProvider()
    elif provider_type == "mock":
        return MockEmbeddingProvider()
    else:
        raise ValueError(f"Unknown embedding provider: {provider_type}. Expected 'openai', 'ollama', or 'mock'.")
