r"""
integration/reports_demo.py
Live demonstration of the Reports Generation module.

Connects to the REAL PostgreSQL database (read-only for data fetching)
and generates all 4 report types in PDF, Excel, and JSON formats.
Files are saved to storage/reports/.

Usage (PowerShell from backend/ai-services/):
    $env:PYTHONPATH="."
    python integration/reports_demo.py

Requirements:
  - PostgreSQL database operix_db must be running
  - .env file must have DATABASE_URL or use defaults
  - PYTHONPATH must be set to backend/ai-services/
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

# ---------------------------------------------------------------------------
# Ensure we can import ai-services modules
# ---------------------------------------------------------------------------
_AI_SERVICES = Path(__file__).parent.parent
if str(_AI_SERVICES) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICES))

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")
DATE_FROM = date(2024, 1, 1)
DATE_TO = date(2025, 12, 31)


def _header(title: str) -> None:
    print("\n" + "─" * 64)
    print(f"  {title}")
    print("─" * 64)


def demo_generate_all_reports() -> None:
    _header("Generating All Report Types (PDF + Excel + JSON)")

    from reports_generation.services.report_service import get_report_service
    from reports_generation.schemas import ReportType, ReportFormat

    svc = get_report_service()

    results = []
    for report_type in ReportType:
        for fmt in ReportFormat:
            label = f"{report_type.value} / {fmt.value}"
            try:
                meta = svc.generate_report(
                    factory_id=FACTORY_ID,
                    report_type=report_type,
                    format=fmt,
                    date_from=DATE_FROM,
                    date_to=DATE_TO,
                )
                size_kb = meta.file_size_bytes / 1024
                print(f"  ✅  {label:<40} → {meta.file_name} ({size_kb:.1f} KB)")
                results.append(meta)
            except Exception as exc:
                print(f"  ❌  {label:<40} → ERROR: {exc}")

    return results


def demo_json_report_content() -> None:
    _header("Inspect Generated JSON Report Content")

    import json
    from reports_generation.config import REPORTS_STORAGE_DIR

    json_files = list(REPORTS_STORAGE_DIR.glob("*.json"))
    if not json_files:
        print("  [!] No JSON reports found.")
        return

    latest = max(json_files, key=lambda p: p.stat().st_mtime)
    print(f"  Most recent: {latest.name}")
    with open(latest, encoding="utf-8") as f:
        data = json.load(f)
    # Print top-level keys
    print(f"  Top-level keys: {list(data.keys())[:10]}")


def demo_api_contracts() -> None:
    _header("API Contract Validation")

    from reports_generation.api_contracts.requests import GenerateReportRequest
    from reports_generation.api_contracts.responses import GenerateReportResponse
    from reports_generation.schemas import ReportType, ReportFormat, ReportMetadata

    req = GenerateReportRequest(
        factory_id=FACTORY_ID,
        report_type=ReportType.WORKFORCE,
        format=ReportFormat.PDF,
        date_from=DATE_FROM,
        date_to=DATE_TO,
    )
    print(f"  Request validated: {req.report_type.value} / {req.format.value}")

    meta = ReportMetadata(
        report_id="REP-DEMO-001",
        report_type=ReportType.WORKFORCE,
        format=ReportFormat.PDF,
        factory_id=FACTORY_ID,
        title="Workforce Report",
        generated_at=datetime.now(tz=timezone.utc),
        file_name="workforce_REP-DEMO-001.pdf",
        file_size_bytes=48320,
        mime_type="application/pdf",
    )
    resp = GenerateReportResponse(data=meta)
    print(f"  Response envelope: success={resp.success}, report_id={resp.data.report_id}")
    print(f"  Disclaimer present: {'proxy' in resp.data.disclaimer.lower()}")


def main() -> None:
    print("=" * 64)
    print("  Operix — Reports Generation Module Demo")
    print(f"  Factory: {FACTORY_ID}")
    print(f"  Period : {DATE_FROM} → {DATE_TO}")
    print("=" * 64)

    results = demo_generate_all_reports()
    demo_json_report_content()
    demo_api_contracts()

    print("\n" + "=" * 64)
    successful = len(results) if results else 0
    total = len(list(__import__("reports_generation.schemas", fromlist=["ReportType"]).ReportType)) * 3
    print(f"  ✅ Demo complete — {successful}/{total} reports generated")
    print("=" * 64)


if __name__ == "__main__":
    main()
