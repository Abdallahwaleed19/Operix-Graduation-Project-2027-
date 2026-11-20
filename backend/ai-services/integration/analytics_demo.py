"""
integration/analytics_demo.py
Integration demonstration of the Workforce Analytics Service Layer.

Demonstrates how Seif (FastAPI Backend) or any Python script can consume
the WorkforceAnalyticsService without needing a running FastAPI web server.

Run from backend/ai-services/:
    python integration/analytics_demo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add backend/ai-services root to Python module path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from workforce_analytics.api_contracts.responses import WorkforceSummaryResponse
from workforce_analytics.config import DATABASE_URL, DEFAULT_FACTORY_ID
from workforce_analytics.services.analytics_service import WorkforceAnalyticsService


def main() -> int:
    print("=" * 70)
    print("  Operix — Workforce Analytics Service Integration Demo")
    print("=" * 70)

    # 1. Initialize Service
    print(f"\n[1] Initializing WorkforceAnalyticsService...")
    print(f"    Configured Factory ID : {DEFAULT_FACTORY_ID}")
    
    # Mask password in connection string for safe terminal output
    safe_db_url = DATABASE_URL
    if "@" in safe_db_url and ":" in safe_db_url:
        prefix, rest = safe_db_url.split("://", 1)
        creds, host_db = rest.split("@", 1)
        user = creds.split(":", 1)[0]
        safe_db_url = f"{prefix}://{user}:*****@{host_db}"
    print(f"    Target Database       : {safe_db_url}")

    service = WorkforceAnalyticsService()

    # 2. Check Database Health
    print("\n[2] Checking Database Connection & Health...")
    health = service.check_health()
    if not health.get("database_connected"):
        print("\n[ERROR] Database is unreachable. Please verify PostgreSQL is running")
        print("        and that credentials in .env are correct.")
        print(f"        Diagnostic details: {health}")
        return 1
    print(f"    Status: {health['status'].upper()} (PostgreSQL connected)")

    # 3. Invoke Service Operations
    print("\n[3] Invoking Service Operations...")
    try:
        # A. Overview
        overview = service.get_workforce_overview()
        print(f"    - Workforce Overview   : {overview.total_users} total users ({overview.active_workers} active)")

        # B. Attendance
        attendance = service.get_attendance_metrics()
        print(f"    - Attendance Activity  : {attendance.members_with_activity}/{attendance.total_members} members ({attendance.activity_rate_pct}%)")

        # C. Incidents
        incidents = service.get_incident_analytics()
        print(f"    - Safety Incidents     : {incidents.total_incidents} incidents ({incidents.resolved_incidents} resolved, {incidents.resolution_rate_pct}%)")

        # D. Productivity
        productivity = service.get_productivity_metrics()
        print(f"    - Worker Productivity  : {productivity.workers_analysed} analysed, avg {productivity.avg_handled_per_worker} handled")

        # E. Camera Coverage
        cameras = service.get_camera_coverage()
        print(f"    - Camera Coverage      : {cameras.active_cameras}/{cameras.total_cameras} cameras active, {cameras.overall_coverage_pct}% coverage")

        # F. Unified Summary
        print("\n[4] Generating Unified Summary (Pydantic & JSON Envelope)...")
        summary = service.get_workforce_summary()
        envelope = WorkforceSummaryResponse(
            data=summary,
            meta={"factory_id": summary.overview.factory_id},
        )
        json_output = envelope.model_dump(mode="json")

        print("\n[5] Unified JSON API Response Preview:")
        print("-" * 70)
        # Compact preview of the API response
        compact_preview = {
            "status": json_output["status"],
            "meta": json_output["meta"],
            "data_summary": {
                "generated_at": json_output["data"]["generated_at"],
                "active_workers": json_output["data"]["overview"]["active_workers"],
                "activity_rate_pct": json_output["data"]["attendance"]["activity_rate_pct"],
                "total_incidents": json_output["data"]["incidents"]["total_incidents"],
                "resolved_incidents": json_output["data"]["incidents"]["resolved_incidents"],
                "avg_handled_per_worker": json_output["data"]["productivity"]["avg_handled_per_worker"],
                "camera_coverage_pct": json_output["data"]["camera_coverage"]["overall_coverage_pct"],
            },
        }
        print(json.dumps(compact_preview, indent=2))
        print("-" * 70)

        print("\n[SUCCESS] Workforce Analytics Service Layer executed successfully without errors.")
        print("          Ready for integration into Seif's FastAPI backend.\n")
        return 0

    except Exception as exc:
        print(f"\n[FATAL ERROR] An unexpected exception occurred during service execution:")
        print(f"              {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
