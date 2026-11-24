"""
workforce_analytics/tests/test_analytics.py
Automated pytest tests for all Workforce Analytics functions.

Test strategy:
  - Integration tests run against the real operix_db (sample data inserted in PHASE 3).
  - Unit tests use mock data via monkeypatching the repository layer.
  - No destructive operations (no INSERT/DELETE/TRUNCATE against the real DB).
  - Tests pass even if the DB has only the sample seed data inserted.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

try:
    import pytest
except ImportError:
    import unittest
    class _PytestShim:
        @staticmethod
        def fixture(*args, **kwargs):
            return lambda fn: fn
        @staticmethod
        def skip(reason=""):
            raise unittest.SkipTest(reason)
    pytest = _PytestShim()

# Make sure the ai-services root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from workforce_analytics.analytics import (
    calculate_attendance_metrics,
    calculate_camera_coverage,
    calculate_incident_analytics,
    calculate_productivity_metrics,
    generate_workforce_summary,
    get_workforce_overview,
)
from workforce_analytics.database import test_connection
from workforce_analytics.schemas import (
    AttendanceMetrics,
    CameraCoverage,
    IncidentAnalytics,
    ProductivityMetrics,
    WorkforceOverview,
    WorkforceSummary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")


@pytest.fixture(scope="session")
def db_available() -> bool:
    """Check once whether the real DB is reachable."""
    return test_connection()


# ---------------------------------------------------------------------------
# Integration tests (require real DB + sample data)
# ---------------------------------------------------------------------------

class TestWorkforceOverviewIntegration:
    def test_returns_correct_type(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = get_workforce_overview(FACTORY_ID)
        assert isinstance(result, WorkforceOverview)

    def test_total_users_is_8(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = get_workforce_overview(FACTORY_ID)
        assert result.total_users == 8

    def test_active_workers_is_7(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = get_workforce_overview(FACTORY_ID)
        assert result.active_workers == 7

    def test_inactive_includes_disabled(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = get_workforce_overview(FACTORY_ID)
        assert result.inactive_workers >= 1

    def test_role_split_sums_to_active(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = get_workforce_overview(FACTORY_ID)
        role_sum = (
            result.by_role.factory_admin
            + result.by_role.factory_manager
            + result.by_role.safety_supervisor
        )
        assert role_sum == result.active_workers

    def test_has_1_admin(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = get_workforce_overview(FACTORY_ID)
        assert result.by_role.factory_admin == 1

    def test_has_2_managers(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = get_workforce_overview(FACTORY_ID)
        assert result.by_role.factory_manager == 2

    def test_unavailable_fields_documented(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = get_workforce_overview(FACTORY_ID)
        assert "NOT AVAILABLE" in result.workers_by_department
        assert "NOT AVAILABLE" in result.working_hours


class TestAttendanceMetricsIntegration:
    def test_returns_correct_type(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_attendance_metrics(FACTORY_ID)
        assert isinstance(result, AttendanceMetrics)

    def test_activity_rate_between_0_and_100(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_attendance_metrics(FACTORY_ID)
        assert 0.0 <= result.activity_rate_pct <= 100.0

    def test_members_add_up(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_attendance_metrics(FACTORY_ID)
        assert result.members_with_activity + result.members_no_activity == result.total_members

    def test_daily_trend_is_list(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_attendance_metrics(FACTORY_ID)
        assert isinstance(result.daily_activity_trend, list)

    def test_proxy_note_present(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_attendance_metrics(FACTORY_ID)
        assert "PROXY" in result.data_quality_note


class TestIncidentAnalyticsIntegration:
    def test_returns_correct_type(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_incident_analytics(FACTORY_ID)
        assert isinstance(result, IncidentAnalytics)

    def test_total_is_15(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_incident_analytics(FACTORY_ID)
        assert result.total_incidents == 15

    def test_resolved_is_7(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_incident_analytics(FACTORY_ID)
        assert result.resolved_incidents == 7

    def test_resolution_rate_is_correct(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_incident_analytics(FACTORY_ID)
        expected = round(7 / 15 * 100, 2)
        assert result.resolution_rate_pct == expected

    def test_resolved_plus_open_equals_total(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_incident_analytics(FACTORY_ID)
        assert result.resolved_incidents + result.open_incidents == result.total_incidents

    def test_avg_resolve_time_is_positive(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_incident_analytics(FACTORY_ID)
        assert result.avg_time_to_resolve_hrs is not None
        assert result.avg_time_to_resolve_hrs > 0

    def test_date_range_filter(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        # Only last 7 days — expect fewer incidents
        end   = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=7)
        result = calculate_incident_analytics(FACTORY_ID, start=start, end=end)
        assert result.total_incidents < 15

    def test_severity_split_sums_to_total(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_incident_analytics(FACTORY_ID)
        sev_sum = (
            result.by_severity.low
            + result.by_severity.medium
            + result.by_severity.high
            + result.by_severity.critical
        )
        assert sev_sum == result.total_incidents

    def test_state_split_sums_to_total(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_incident_analytics(FACTORY_ID)
        state_sum = (
            result.by_state.detected
            + result.by_state.classified
            + result.by_state.recorded
            + result.by_state.alert_pending
            + result.by_state.alert_dispatched
            + result.by_state.under_review
            + result.by_state.resolved
        )
        assert state_sum == result.total_incidents

    def test_invalid_date_range_returns_zero(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        # Future range — no incidents
        start = datetime(2099, 1, 1, tzinfo=timezone.utc)
        end   = datetime(2099, 1, 2, tzinfo=timezone.utc)
        result = calculate_incident_analytics(FACTORY_ID, start=start, end=end)
        assert result.total_incidents == 0
        assert result.resolution_rate_pct == 0.0


class TestProductivityMetricsIntegration:
    def test_returns_correct_type(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_productivity_metrics(FACTORY_ID)
        assert isinstance(result, ProductivityMetrics)

    def test_workers_analysed_equals_active_members(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_productivity_metrics(FACTORY_ID)
        assert result.workers_analysed == 7   # 7 active members

    def test_per_worker_length_matches(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_productivity_metrics(FACTORY_ID)
        assert len(result.per_worker) == result.workers_analysed

    def test_productivity_labels_valid(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_productivity_metrics(FACTORY_ID)
        for w in result.per_worker:
            assert w.productivity_label in ("low", "normal", "high")

    def test_low_performers_subset_of_per_worker(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_productivity_metrics(FACTORY_ID)
        all_names = {w.full_name for w in result.per_worker}
        for name in result.low_performers:
            assert name in all_names

    def test_avg_per_worker_is_non_negative(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_productivity_metrics(FACTORY_ID)
        assert result.avg_handled_per_worker >= 0

    def test_custom_thresholds(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_productivity_metrics(
            FACTORY_ID, low_threshold=0, high_threshold=1
        )
        assert result.thresholds_used == {"low": 0, "high": 1}

    def test_empty_dataset_returns_zero(self):
        """Unit test: no DB needed — mock returns empty list and injected session."""
        from unittest.mock import MagicMock
        mock_session = MagicMock()
        with patch("workforce_analytics.analytics.fetch_per_worker_productivity",
                   return_value=[]):
            result = calculate_productivity_metrics(FACTORY_ID, session=mock_session)
        assert result.workers_analysed == 0
        assert result.avg_handled_per_worker == 0.0
        assert result.low_performers == []
        assert result.high_performers == []


class TestCameraCoverageIntegration:
    def test_returns_correct_type(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_camera_coverage(FACTORY_ID)
        assert isinstance(result, CameraCoverage)

    def test_total_cameras_is_4(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_camera_coverage(FACTORY_ID)
        assert result.total_cameras == 4

    def test_active_cameras_is_3(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_camera_coverage(FACTORY_ID)
        assert result.active_cameras == 3

    def test_coverage_between_0_and_100(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_camera_coverage(FACTORY_ID)
        assert 0.0 <= result.overall_coverage_pct <= 100.0

    def test_per_camera_length_matches(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = calculate_camera_coverage(FACTORY_ID)
        assert len(result.per_camera) == result.total_cameras


class TestWorkforceSummaryIntegration:
    def test_returns_correct_type(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = generate_workforce_summary(FACTORY_ID)
        assert isinstance(result, WorkforceSummary)

    def test_all_sub_sections_present(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = generate_workforce_summary(FACTORY_ID)
        assert result.overview       is not None
        assert result.attendance     is not None
        assert result.incidents      is not None
        assert result.productivity   is not None
        assert result.camera_coverage is not None

    def test_generated_at_is_recent(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        result = generate_workforce_summary(FACTORY_ID)
        delta = datetime.now(tz=timezone.utc) - result.generated_at
        assert delta.total_seconds() < 60   # generated within last minute

    def test_json_serialisable(self, db_available):
        if not db_available:
            pytest.skip("DB not reachable")
        import json
        result = generate_workforce_summary(FACTORY_ID)
        dumped = result.model_dump(mode="json")
        # Must not raise
        json.dumps(dumped)
