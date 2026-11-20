"""
run_tests.py — Built-in test runner (Zero-dependency, uses standard library unittest).
Runs all 30+ tests against the real operix_db without requiring pytest.

Run from backend/ai-services/ directory:
    python run_tests.py
"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent))

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

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")


class TestWorkforceOverview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_available = test_connection()

    def setUp(self):
        if not self.db_available:
            self.skipTest("Database not reachable")

    def test_returns_correct_type(self):
        result = get_workforce_overview(FACTORY_ID)
        self.assertIsInstance(result, WorkforceOverview)

    def test_total_users_is_8(self):
        result = get_workforce_overview(FACTORY_ID)
        self.assertEqual(result.total_users, 8)

    def test_active_workers_is_7(self):
        result = get_workforce_overview(FACTORY_ID)
        self.assertEqual(result.active_workers, 7)

    def test_inactive_includes_disabled(self):
        result = get_workforce_overview(FACTORY_ID)
        self.assertGreaterEqual(result.inactive_workers, 1)

    def test_role_split_sums_to_active(self):
        result = get_workforce_overview(FACTORY_ID)
        role_sum = (
            result.by_role.factory_admin
            + result.by_role.factory_manager
            + result.by_role.safety_supervisor
        )
        self.assertEqual(role_sum, result.active_workers)

    def test_has_1_admin(self):
        result = get_workforce_overview(FACTORY_ID)
        self.assertEqual(result.by_role.factory_admin, 1)

    def test_has_2_managers(self):
        result = get_workforce_overview(FACTORY_ID)
        self.assertEqual(result.by_role.factory_manager, 2)

    def test_unavailable_fields_documented(self):
        result = get_workforce_overview(FACTORY_ID)
        self.assertIn("NOT AVAILABLE", result.workers_by_department)
        self.assertIn("NOT AVAILABLE", result.working_hours)


class TestAttendanceMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_available = test_connection()

    def setUp(self):
        if not self.db_available:
            self.skipTest("Database not reachable")

    def test_returns_correct_type(self):
        result = calculate_attendance_metrics(FACTORY_ID)
        self.assertIsInstance(result, AttendanceMetrics)

    def test_activity_rate_between_0_and_100(self):
        result = calculate_attendance_metrics(FACTORY_ID)
        self.assertTrue(0.0 <= result.activity_rate_pct <= 100.0)

    def test_members_add_up(self):
        result = calculate_attendance_metrics(FACTORY_ID)
        self.assertEqual(
            result.members_with_activity + result.members_no_activity,
            result.total_members
        )

    def test_daily_trend_is_list(self):
        result = calculate_attendance_metrics(FACTORY_ID)
        self.assertIsInstance(result.daily_activity_trend, list)

    def test_proxy_note_present(self):
        result = calculate_attendance_metrics(FACTORY_ID)
        self.assertIn("PROXY", result.data_quality_note)


class TestIncidentAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_available = test_connection()

    def setUp(self):
        if not self.db_available:
            self.skipTest("Database not reachable")

    def test_returns_correct_type(self):
        result = calculate_incident_analytics(FACTORY_ID)
        self.assertIsInstance(result, IncidentAnalytics)

    def test_total_is_15(self):
        result = calculate_incident_analytics(FACTORY_ID)
        self.assertEqual(result.total_incidents, 15)

    def test_resolved_is_7(self):
        result = calculate_incident_analytics(FACTORY_ID)
        self.assertEqual(result.resolved_incidents, 7)

    def test_resolution_rate_is_correct(self):
        result = calculate_incident_analytics(FACTORY_ID)
        expected = round(7 / 15 * 100, 2)
        self.assertEqual(result.resolution_rate_pct, expected)

    def test_resolved_plus_open_equals_total(self):
        result = calculate_incident_analytics(FACTORY_ID)
        self.assertEqual(
            result.resolved_incidents + result.open_incidents,
            result.total_incidents
        )

    def test_avg_resolve_time_is_positive(self):
        result = calculate_incident_analytics(FACTORY_ID)
        self.assertIsNotNone(result.avg_time_to_resolve_hrs)
        self.assertGreater(result.avg_time_to_resolve_hrs, 0)

    def test_date_range_filter(self):
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=7)
        result = calculate_incident_analytics(FACTORY_ID, start=start, end=end)
        self.assertLess(result.total_incidents, 15)

    def test_severity_split_sums_to_total(self):
        result = calculate_incident_analytics(FACTORY_ID)
        sev_sum = (
            result.by_severity.low
            + result.by_severity.medium
            + result.by_severity.high
            + result.by_severity.critical
        )
        self.assertEqual(sev_sum, result.total_incidents)

    def test_state_split_sums_to_total(self):
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
        self.assertEqual(state_sum, result.total_incidents)

    def test_invalid_date_range_returns_zero(self):
        start = datetime(2099, 1, 1, tzinfo=timezone.utc)
        end = datetime(2099, 1, 2, tzinfo=timezone.utc)
        result = calculate_incident_analytics(FACTORY_ID, start=start, end=end)
        self.assertEqual(result.total_incidents, 0)
        self.assertEqual(result.resolution_rate_pct, 0.0)


class TestProductivityMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_available = test_connection()

    def setUp(self):
        if not self.db_available:
            self.skipTest("Database not reachable")

    def test_returns_correct_type(self):
        result = calculate_productivity_metrics(FACTORY_ID)
        self.assertIsInstance(result, ProductivityMetrics)

    def test_workers_analysed_equals_active_members(self):
        result = calculate_productivity_metrics(FACTORY_ID)
        self.assertEqual(result.workers_analysed, 7)

    def test_per_worker_length_matches(self):
        result = calculate_productivity_metrics(FACTORY_ID)
        self.assertEqual(len(result.per_worker), result.workers_analysed)

    def test_productivity_labels_valid(self):
        result = calculate_productivity_metrics(FACTORY_ID)
        for w in result.per_worker:
            self.assertIn(w.productivity_label, ("low", "normal", "high"))

    def test_low_performers_subset_of_per_worker(self):
        result = calculate_productivity_metrics(FACTORY_ID)
        all_names = {w.full_name for w in result.per_worker}
        for name in result.low_performers:
            self.assertIn(name, all_names)

    def test_avg_per_worker_is_non_negative(self):
        result = calculate_productivity_metrics(FACTORY_ID)
        self.assertGreaterEqual(result.avg_handled_per_worker, 0)

    def test_custom_thresholds(self):
        result = calculate_productivity_metrics(
            FACTORY_ID, low_threshold=0, high_threshold=1
        )
        self.assertEqual(result.thresholds_used, {"low": 0, "high": 1})

    def test_empty_dataset_returns_zero(self):
        with patch("workforce_analytics.analytics.fetch_per_worker_productivity", return_value=[]):
            result = calculate_productivity_metrics(FACTORY_ID)
        self.assertEqual(result.workers_analysed, 0)
        self.assertEqual(result.avg_handled_per_worker, 0.0)
        self.assertEqual(result.low_performers, [])
        self.assertEqual(result.high_performers, [])


class TestCameraCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_available = test_connection()

    def setUp(self):
        if not self.db_available:
            self.skipTest("Database not reachable")

    def test_returns_correct_type(self):
        result = calculate_camera_coverage(FACTORY_ID)
        self.assertIsInstance(result, CameraCoverage)

    def test_total_cameras_is_4(self):
        result = calculate_camera_coverage(FACTORY_ID)
        self.assertEqual(result.total_cameras, 4)

    def test_active_cameras_is_3(self):
        result = calculate_camera_coverage(FACTORY_ID)
        self.assertEqual(result.active_cameras, 3)

    def test_coverage_between_0_and_100(self):
        result = calculate_camera_coverage(FACTORY_ID)
        self.assertTrue(0.0 <= result.overall_coverage_pct <= 100.0)

    def test_per_camera_length_matches(self):
        result = calculate_camera_coverage(FACTORY_ID)
        self.assertEqual(len(result.per_camera), result.total_cameras)


class TestWorkforceSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_available = test_connection()

    def setUp(self):
        if not self.db_available:
            self.skipTest("Database not reachable")

    def test_returns_correct_type(self):
        result = generate_workforce_summary(FACTORY_ID)
        self.assertIsInstance(result, WorkforceSummary)

    def test_all_sub_sections_present(self):
        result = generate_workforce_summary(FACTORY_ID)
        self.assertIsNotNone(result.overview)
        self.assertIsNotNone(result.attendance)
        self.assertIsNotNone(result.incidents)
        self.assertIsNotNone(result.productivity)
        self.assertIsNotNone(result.camera_coverage)

    def test_generated_at_is_recent(self):
        result = generate_workforce_summary(FACTORY_ID)
        delta = datetime.now(tz=timezone.utc) - result.generated_at
        self.assertLess(delta.total_seconds(), 60)

    def test_json_serialisable(self):
        import json
        result = generate_workforce_summary(FACTORY_ID)
        dumped = result.model_dump(mode="json")
        json_str = json.dumps(dumped)
        self.assertTrue(len(json_str) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
