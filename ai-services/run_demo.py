"""
run_demo.py — Quick CLI demo that prints live JSON analytics output.
Run from ai-services/ directory:
    python run_demo.py
"""
import json
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workforce_analytics.analytics import generate_workforce_summary
from workforce_analytics.database import test_connection

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")

def main():
    print("\n" + "="*65)
    print("  Operix — Workforce Analytics Demo")
    print("="*65)

    if not test_connection():
        print("[ERROR] Cannot reach database. Check .env settings.")
        sys.exit(1)

    print("[OK] Database connection successful.\n")
    print("Generating full workforce summary...")

    summary = generate_workforce_summary(FACTORY_ID)
    output  = summary.model_dump(mode="json")

    # Pretty-print key sections
    ov = output["overview"]
    inc = output["incidents"]
    prod = output["productivity"]
    cam = output["camera_coverage"]

    print("\n── A. WORKFORCE OVERVIEW ──────────────────────────────────")
    print(f"  Total users    : {ov['total_users']}")
    print(f"  Active workers : {ov['active_workers']}")
    print(f"  Inactive       : {ov['inactive_workers']}")
    print(f"  By role        : {ov['by_role']}")

    print("\n── B. ATTENDANCE (proxy) ───────────────────────────────────")
    att = output["attendance"]
    print(f"  Members with activity : {att['members_with_activity']} / {att['total_members']}")
    print(f"  Activity rate         : {att['activity_rate_pct']}%")
    print(f"  Daily trend entries   : {len(att['daily_activity_trend'])}")

    print("\n── C. INCIDENT ANALYTICS ───────────────────────────────────")
    print(f"  Total incidents      : {inc['total_incidents']}")
    print(f"  Resolved             : {inc['resolved_incidents']}")
    print(f"  Open                 : {inc['open_incidents']}")
    print(f"  Resolution rate      : {inc['resolution_rate_pct']}%")
    print(f"  Target met (≥80%)    : {inc['target_met']}")
    print(f"  Avg resolve time     : {inc['avg_time_to_resolve_hrs']} hrs")
    print(f"  Avg review time      : {inc['avg_time_to_review_hrs']} hrs")
    print(f"  By severity          : {inc['by_severity']}")
    print(f"  By type              : {inc['by_type']}")

    print("\n── D. PRODUCTIVITY METRICS ─────────────────────────────────")
    print(f"  Workers analysed     : {prod['workers_analysed']}")
    print(f"  Avg handled/worker   : {prod['avg_handled_per_worker']}")
    print(f"  High performers      : {prod['high_performers']}")
    print(f"  Low performers       : {prod['low_performers']}")
    print("  Per-worker breakdown:")
    for w in prod["per_worker"]:
        print(f"    {w['full_name']:<20} role={w['role']:<20} "
              f"reviewed={w['incidents_reviewed']} resolved={w['incidents_resolved']} "
              f"total={w['total_handled']} [{w['productivity_label']}]")

    print("\n── E. CAMERA COVERAGE ──────────────────────────────────────")
    print(f"  Total cameras        : {cam['total_cameras']}")
    print(f"  Active / Inactive    : {cam['active_cameras']} / {cam['inactive_cameras']}")
    print(f"  Overall coverage     : {cam['overall_coverage_pct']}%")
    print(f"  Total downtime       : {cam['total_downtime_hrs']} hrs")
    print("  Per-camera:")
    for c in cam["per_camera"]:
        print(f"    {c['camera_name']:<20} dept={c['department_name']:<15} "
              f"active={c['is_active']} downtime={c['total_downtime_hrs']}h gaps={c['gap_count']}")

    print("\n── FULL JSON OUTPUT (summary) ──────────────────────────────")
    # Print a compact version of the full JSON
    compact = {
        "generated_at":    output["generated_at"],
        "total_workers":   ov["active_workers"],
        "inactive_workers":ov["inactive_workers"],
        "activity_rate_pct": att["activity_rate_pct"],
        "total_incidents": inc["total_incidents"],
        "resolved_incidents": inc["resolved_incidents"],
        "resolution_rate_pct": inc["resolution_rate_pct"],
        "avg_resolve_time_hrs": inc["avg_time_to_resolve_hrs"],
        "avg_handled_per_worker": prod["avg_handled_per_worker"],
        "camera_coverage_pct": cam["overall_coverage_pct"],
    }
    print(json.dumps(compact, indent=2, default=str))
    print("\n" + "="*65 + "\n")

if __name__ == "__main__":
    main()
