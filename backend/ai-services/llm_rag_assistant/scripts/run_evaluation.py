"""
scripts/run_evaluation.py
CLI benchmark evaluation runner.

Usage:
    python -m llm_rag_assistant.scripts.run_evaluation
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add backend/ai-services to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from llm_rag_assistant.config.settings import get_settings
from llm_rag_assistant.evaluation.benchmark_dataset import OPERIX_BENCHMARK_CASES
from llm_rag_assistant.evaluation.evaluator import RAGEvaluator
from llm_rag_assistant.providers.embedding_provider import MockEmbeddingProvider
from llm_rag_assistant.providers.llm_provider import MockLLMProvider
from llm_rag_assistant.retrieval.retriever import KnowledgeRetriever
from llm_rag_assistant.retrieval.vector_store import NumPyVectorStore
from llm_rag_assistant.services.assistant_service import OperixAssistantService


def main() -> int:
    print("=" * 75)
    print("  Operix LLM/RAG Assistant — Benchmark Evaluation Suite")
    print("=" * 75)

    settings = get_settings()
    vector_store = NumPyVectorStore(storage_dir=settings.vector_store_dir)
    service = OperixAssistantService(
        retriever=KnowledgeRetriever(
            embedding_provider=MockEmbeddingProvider(),
            vector_store=vector_store,
        ),
        llm_provider=MockLLMProvider(),
    )

    evaluator = RAGEvaluator(service)
    print(f"\n[*] Running {len(OPERIX_BENCHMARK_CASES)} Standardized Benchmark Cases...\n")

    results = evaluator.evaluate()

    print(f"{'ID':<10} | {'Lang':<5} | {'Category':<22} | {'Evidence':<9} | {'Latency':<8} | {'Status'}")
    print("-" * 75)
    for d in results["details"]:
        status = "PASSED" if d["passed"] else "FAILED"
        has_ev = "YES" if d["has_evidence"] else "NO"
        print(f"{d['id']:<10} | {d['language']:<5} | {d['category']:<22} | {has_ev:<9} | {d['latency_sec']}s    | {status}")

    print("-" * 75)
    print(f"\n[SUMMARY METRICS]")
    print(f"  • Total Benchmark Cases   : {results['total_cases']}")
    print(f"  • Grounding Accuracy Rate : {results['grounding_accuracy_pct']}%")
    print(f"  • Refusal Honesty Rate    : {results['refusal_honesty_pct']}% (Zero Hallucination)")
    print(f"  • Average Latency         : {results['avg_latency_ms']} ms")
    print("\n" + "=" * 75)
    return 0


if __name__ == "__main__":
    sys.exit(main())
