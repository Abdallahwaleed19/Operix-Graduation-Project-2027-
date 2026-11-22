"""
run_all_tests.py
Runs the full Operix AI Services test suite and reports results.

Covers:
  Task 1 — Workforce Analytics     (64 tests)
  Task 2 — LLM / RAG Assistant     (42 tests)
  Task 3 — Reports Generation      (new tests)
  Task 4 — Incident Evidence       (new tests)

Usage (PowerShell from backend/ai-services/):
    $env:PYTHONPATH="."
    C:\\Users\\AbdallahWaleed\\AppData\\Local\\Programs\\Python\\Python314\\python.exe run_all_tests.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Ensure the ai-services directory is on the path
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

MODULES = [
    # Task 1 — Workforce Analytics
    "workforce_analytics.tests",
    # Task 2 — LLM / RAG Assistant
    "llm_rag_assistant.tests",
    # Task 3 — Reports Generation
    "reports_generation.tests",
    # Task 4 — Incident Evidence
    "incident_evidence.tests",
]


def main() -> None:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    print("=" * 70)
    print("  Operix AI Services — Full Test Suite")
    print("=" * 70)

    for module_path in MODULES:
        try:
            discovered = loader.discover(
                start_dir=str(_ROOT / module_path.replace(".", "/")),
                pattern="test_*.py",
                top_level_dir=str(_ROOT),
            )
            count = discovered.countTestCases()
            suite.addTests(discovered)
            print(f"  [+] {module_path:<40} {count:>4} tests found")
        except Exception as exc:
            print(f"  [!] {module_path:<40} DISCOVERY ERROR: {exc}")

    print("─" * 70)
    total = suite.countTestCases()
    print(f"  Total tests to run: {total}")
    print("─" * 70)
    print()

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print()
    print("=" * 70)
    print(f"  RAN    : {result.testsRun}")
    print(f"  ERRORS : {len(result.errors)}")
    print(f"  FAIL   : {len(result.failures)}")
    print(f"  SKIP   : {len(result.skipped)}")
    if result.wasSuccessful():
        print("  STATUS : ✅ ALL TESTS PASSED")
    else:
        print("  STATUS : ❌ SOME TESTS FAILED")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
