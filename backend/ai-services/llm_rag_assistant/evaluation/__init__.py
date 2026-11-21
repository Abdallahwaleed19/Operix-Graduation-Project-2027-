"""
evaluation package for Operix LLM/RAG Assistant.
"""
from .benchmark_dataset import OPERIX_BENCHMARK_CASES, BenchmarkTestCase
from .evaluator import RAGEvaluator

__all__ = [
    "BenchmarkTestCase",
    "OPERIX_BENCHMARK_CASES",
    "RAGEvaluator",
]
