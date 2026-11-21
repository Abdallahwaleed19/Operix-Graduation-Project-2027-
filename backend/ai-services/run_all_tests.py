"""
run_all_tests.py — Master Test Runner for Operix AI Services.
Executes the full test suite for both:
  1. Workforce Analytics Module (64 tests)
  2. LLM / RAG Assistant Module (38 tests)

Total: 102 automated tests. Zero external dependencies required.

Run from backend/ai-services/:
    python run_all_tests.py
"""
import sys
import unittest
from pathlib import Path

# Ensure ai-services root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))


def main():
    print("=" * 75)
    print("  Operix AI Services — Master Unified Test Suite Runner")
    print("  Modules: Workforce Analytics & LLM/RAG Assistant")
    print("=" * 75)
    print()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 1. Load Workforce Analytics Tests (from run_tests.py test classes)
    from run_tests import (
        TestAttendanceMetrics,
        TestCameraCoverage,
        TestIncidentAnalytics,
        TestProductivityMetrics,
        TestWorkforceOverview,
        TestWorkforceSummary,
    )
    from workforce_analytics.tests.test_service import (
        TestAPIContracts,
        TestServiceEdgeCases,
        TestWorkforceAnalyticsService,
    )

    wf_classes = [
        TestWorkforceOverview,
        TestAttendanceMetrics,
        TestIncidentAnalytics,
        TestProductivityMetrics,
        TestCameraCoverage,
        TestWorkforceSummary,
        TestWorkforceAnalyticsService,
        TestAPIContracts,
        TestServiceEdgeCases,
    ]
    for cls in wf_classes:
        suite.addTest(loader.loadTestsFromTestCase(cls))

    # 2. Discover LLM / RAG Assistant Tests
    rag_suite = loader.discover(
        start_dir=str(ROOT_DIR / "llm_rag_assistant" / "tests"),
        pattern="test_*.py",
        top_level_dir=str(ROOT_DIR),
    )
    suite.addTests(rag_suite)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 75)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures : {len(result.failures)}")
    print(f"Errors   : {len(result.errors)}")
    print("=" * 75)

    if result.wasSuccessful():
        print("\n[ALL TESTS PASSED] 100% SUCCESS ACROSS ALL MODULES!\n")
        return 0
    else:
        print("\n[TESTS FAILED] Please inspect error messages above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
