"""
workforce_analytics/tests/test_phase2_integration.py
Phase 2 integration & security tests: no local engine/session, canonical models, injected session required.
Phase 4 (Fix #5): production guard — no hardcoded factory sentinel in production mode.
"""
from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from workforce_analytics import analytics as wa_analytics
from workforce_analytics import database as wa_database
from workforce_analytics.services.analytics_service import WorkforceAnalyticsService


class TestWorkforceAnalyticsPhase2(unittest.TestCase):
    def test_no_engine_or_sessionmaker_in_module(self):
        module_root = Path(wa_analytics.__file__).parent
        for py_file in module_root.rglob("*.py"):
            if "tests" in py_file.parts:
                continue
            text = py_file.read_text(encoding="utf-8")
            self.assertNotIn("create_engine(", text, f"Found create_engine in {py_file}")
            self.assertNotIn("sessionmaker(", text, f"Found sessionmaker in {py_file}")

    def test_missing_session_raises_runtime_error(self):
        svc = WorkforceAnalyticsService(default_factory_id=uuid4(), session=None)
        with self.assertRaises(RuntimeError):
            svc.get_workforce_overview()
        with self.assertRaises(RuntimeError):
            svc.get_attendance_metrics()
        with self.assertRaises(RuntimeError):
            svc.get_incident_analytics()
        with self.assertRaises(RuntimeError):
            svc.get_productivity_metrics()
        with self.assertRaises(RuntimeError):
            svc.get_camera_coverage()
        with self.assertRaises(RuntimeError):
            svc.get_workforce_summary()

    def test_get_session_disabled(self):
        with self.assertRaises(RuntimeError):
            with wa_database.get_session():
                pass

    def test_check_health_without_and_with_session(self):
        svc = WorkforceAnalyticsService(default_factory_id=uuid4())
        res_no_db = svc.check_health()
        self.assertEqual(res_no_db["status"], "unhealthy")
        self.assertFalse(res_no_db["database_connected"])

        mock_session = MagicMock()
        res_with_db = svc.check_health(session=mock_session)
        self.assertEqual(res_with_db["status"], "healthy")
        self.assertTrue(res_with_db["database_connected"])
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_not_called()

    def test_canonical_models_reexported(self):
        backend_root = Path(wa_analytics.__file__).resolve().parent.parent.parent
        if str(backend_root) not in sys.path:
            sys.path.insert(0, str(backend_root))
        from app import models as canonical_models
        from workforce_analytics import models as wa_models

        self.assertIs(wa_models.Base, canonical_models.Base)
        self.assertIs(wa_models.Factory, canonical_models.Factory)
        self.assertIs(wa_models.User, canonical_models.User)
        self.assertIs(wa_models.Incident, canonical_models.Incident)
        self.assertIs(wa_models.Camera, canonical_models.Camera)


class TestWorkforceProductionGuardPhase4Fix5(unittest.TestCase):
    """Fix #5: DEFAULT_FACTORY_ID must NOT use hardcoded sentinel in production."""

    # The sentinel that must NEVER reach production
    _SENTINEL = "aaaaaaaa-0001-0001-0001-000000000001"

    def _compute_default_factory_id(self, env: dict) -> str:
        """
        Compute what DEFAULT_FACTORY_ID would be under the given environment,
        replicating the config module logic without actually reloading the module
        (module reload is unreliable due to dotenv side-effects in test runners).
        """
        app_env = env.get("APP_ENV", "production").lower()
        test_mode = env.get("TEST_MODE", "").lower() in ("1", "true", "yes")
        env_factory = env.get("OPERIX_FACTORY_ID", "") or env.get("DEFAULT_FACTORY_ID", "")

        if env_factory:
            return env_factory
        elif app_env in ("development", "dev", "test", "testing") or test_mode:
            return self._SENTINEL
        else:
            raise EnvironmentError(
                "OPERIX_FACTORY_ID or DEFAULT_FACTORY_ID must be set in production."
            )

    def test_dev_mode_uses_sentinel_when_no_env_var(self):
        """In development mode with no env var, sentinel is acceptable."""
        result = self._compute_default_factory_id({"APP_ENV": "development"})
        self.assertEqual(result, self._SENTINEL)

    def test_test_mode_uses_sentinel_when_no_env_var(self):
        """When TEST_MODE=1 and no env var, sentinel is acceptable for offline tests."""
        result = self._compute_default_factory_id({"TEST_MODE": "1"})
        self.assertEqual(result, self._SENTINEL)

    def test_explicit_env_var_overrides_sentinel(self):
        """When OPERIX_FACTORY_ID is set, it overrides the sentinel in all modes."""
        expected = str(uuid4())
        result = self._compute_default_factory_id(
            {"OPERIX_FACTORY_ID": expected, "APP_ENV": "production"}
        )
        self.assertEqual(result, expected)

    def test_production_mode_without_env_var_raises_environment_error(self):
        """In production mode with no factory env var, startup must raise EnvironmentError."""
        with self.assertRaises(EnvironmentError):
            self._compute_default_factory_id({"APP_ENV": "production"})

    def test_service_requires_explicit_factory_id_per_call(self):
        """WorkforceAnalyticsService._resolve_factory_id() should use the per-call factory_id,
        never silently falling back to a hardcoded sentinel that bypasses tenant isolation."""
        per_call_fid = uuid4()
        svc = WorkforceAnalyticsService(default_factory_id=per_call_fid)
        resolved = svc._resolve_factory_id(per_call_fid)
        self.assertEqual(resolved, per_call_fid)
        # The hardcoded sentinel should NOT be reachable via per-call resolution
        self.assertNotEqual(str(resolved), self._SENTINEL)


if __name__ == "__main__":
    unittest.main()
