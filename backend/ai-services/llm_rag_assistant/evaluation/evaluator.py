"""
evaluation/evaluator.py
Evaluation engine measuring retrieval precision, grounding fidelity, and anti-hallucination rate.
"""
from __future__ import annotations

import time
from typing import Any, List, Optional

from ..schemas.contracts import AssistantQueryRequest, UserContext
from ..services.assistant_service import OperixAssistantService
from .benchmark_dataset import OPERIX_BENCHMARK_CASES, BenchmarkTestCase


class RAGEvaluator:
    """Evaluates RAG assistant accuracy and safety against standardized benchmarks."""

    def __init__(
        self,
        service: OperixAssistantService,
        user_context: Optional[UserContext] = None,
    ) -> None:
        self.service = service
        self.user_context = user_context

    def evaluate(
        self,
        cases: Optional[List[BenchmarkTestCase]] = None,
        user_context: Optional[UserContext] = None,
    ) -> dict[str, Any]:
        active_context = user_context or self.user_context
        if active_context is None:
            raise ValueError(
                "RAGEvaluator requires an explicit UserContext (user_id and factory_id). "
                "Refusing to invent a fallback identity."
            )

        test_cases = cases or OPERIX_BENCHMARK_CASES
        total = len(test_cases)
        correct_evidence_judgments = 0
        refusal_tests = 0
        correct_refusals = 0
        total_latency_sec = 0.0

        details = []

        for case in test_cases:
            req = AssistantQueryRequest(
                question=case.question,
                user_context=active_context,
                language_preference=case.language,  # type: ignore
            )
            t0 = time.perf_counter()
            resp = self.service.ask(req)
            latency = time.perf_counter() - t0
            total_latency_sec += latency

            # Check if grounding judgment matched expectation
            judgment_correct = resp.has_sufficient_evidence == case.expected_to_have_evidence
            if judgment_correct:
                correct_evidence_judgments += 1

            if not case.expected_to_have_evidence:
                refusal_tests += 1
                if not resp.has_sufficient_evidence:
                    correct_refusals += 1

            details.append({
                "id": case.id,
                "category": case.category,
                "language": case.language,
                "passed": judgment_correct,
                "has_evidence": resp.has_sufficient_evidence,
                "citations_count": len(resp.citations),
                "latency_sec": round(latency, 3),
            })

        evidence_accuracy = (correct_evidence_judgments / total) * 100 if total else 0.0
        refusal_rate = (correct_refusals / refusal_tests) * 100 if refusal_tests else 100.0
        avg_latency = (total_latency_sec / total) * 1000 if total else 0.0

        return {
            "total_cases": total,
            "grounding_accuracy_pct": round(evidence_accuracy, 1),
            "refusal_honesty_pct": round(refusal_rate, 1),
            "avg_latency_ms": round(avg_latency, 1),
            "details": details,
        }
