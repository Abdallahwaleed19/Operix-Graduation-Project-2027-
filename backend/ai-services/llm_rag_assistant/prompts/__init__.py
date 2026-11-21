"""
prompts package for Operix LLM/RAG Assistant.
"""
from .templates import (
    BASE_SYSTEM_PROMPT_AR,
    BASE_SYSTEM_PROMPT_EN,
    build_grounded_prompt,
)

__all__ = [
    "BASE_SYSTEM_PROMPT_AR",
    "BASE_SYSTEM_PROMPT_EN",
    "build_grounded_prompt",
]
