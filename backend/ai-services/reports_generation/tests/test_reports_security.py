"""
reports_generation/tests/test_reports_security.py
Security and factory isolation tests for Phase 5 + Phase 6 fixes.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from reports_generation import config as rpt_config
from reports_generation.exceptions import ReportNotFoundError
from reports_generation.repositories import ReportRepository
from reports_generation.schemas import ReportFormat, ReportMetadata, ReportType
from reports_generation.services.report_service import ReportService


class TestReportsSecurityPhase5(unittest.TestCase):
    def test_no_hardcoded_db_credentials_or_engine_creation(self):
        self.assertFalse(hasattr(rpt_config, "DATABASE_URL"))
        module_root = Path(rpt_config.__file__).parent
        for py_file in module_root.rglob("*.py"):
            if "tests" in py_file.parts:
                continue
            text = py_file.read_text(encoding="utf-8")
            self.assertNotIn("create_engine(", text, f"Found create_engine in {py_file}")
            self.assertNotIn("postgresql+", text.lower(), f"Found postgresql+ in {py_file}")
            self.assertNotIn("://", text.lower(), f"Found connection URI in {py_file}")

    def test_repository_requires_injected_session_or_engine(self):
        repo = ReportRepository()
        with self.assertRaises(RuntimeError):
            repo.get_factory_info(uuid4())

    def test_factory_isolation_in_list_get_and_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f1 = uuid4()
            f2 = uuid4()
            mock_session = MagicMock()
            svc = ReportService(storage_dir=root, session=mock_session)

            # Create a physical report under factory f1
            f1_dir = root / str(f1)
            f1_dir.mkdir(parents=True, exist_ok=True)
            report_id = "REP-20261124-ABC123"
            report_file = f1_dir / f"workforce_{report_id}.pdf"
            report_file.write_bytes(b"%PDF-1.4 fake")

            meta = ReportMetadata(
                report_id=report_id,
                report_type=ReportType.WORKFORCE,
                format=ReportFormat.PDF,
                factory_id=f1,
                title="Workforce Report",
                file_path=str(report_file),
                file_name=report_file.name,
                file_size_bytes=13,
                mime_type="application/pdf",
            )
            svc._registry[report_id] = meta

            # f1 can list, get, and resolve path
            self.assertEqual(len(svc.list_reports(factory_id=f1)), 1)
            self.assertEqual(svc.get_report(report_id, factory_id=f1).factory_id, f1)
            self.assertEqual(svc.get_report_file_path(report_id, factory_id=f1), report_file.resolve())

            # f2 cannot list, get, or resolve path
            self.assertEqual(len(svc.list_reports(factory_id=f2)), 0)
            with self.assertRaises(ReportNotFoundError):
                svc.get_report(report_id, factory_id=f2)
            with self.assertRaises(ReportNotFoundError):
                svc.get_report_file_path(report_id, factory_id=f2)

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc = ReportService(storage_dir=Path(tmp), session=MagicMock())
            for bad_id in ["../secret", "../../etc/passwd", "REP/../../x", "REP\\..\\x", "id\x00.pdf"]:
                with self.assertRaises(ReportNotFoundError):
                    svc.get_report(bad_id, factory_id=uuid4())
                with self.assertRaises(ReportNotFoundError):
                    svc.get_report_file_path(bad_id, factory_id=uuid4())

    def test_disk_lookup_without_registry_uses_directory_factory_uuid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f1 = uuid4()
            f2 = uuid4()
            f1_dir = root / str(f1)
            f1_dir.mkdir(parents=True, exist_ok=True)
            report_id = "REP-20261124-DISK01"
            (f1_dir / f"incident_{report_id}.pdf").write_bytes(b"%PDF-1.4")

            svc = ReportService(storage_dir=root, session=MagicMock())
            meta = svc.get_report(report_id, factory_id=f1)
            self.assertEqual(meta.factory_id, f1)
            with self.assertRaises(ReportNotFoundError):
                svc.get_report(report_id, factory_id=f2)


class TestReportsFactoryIsolationPhase6(unittest.TestCase):
    """Phase 6: factory_id is now a required argument — None/falsy raises ValueError."""

    def _make_service_with_report(self):
        """Helper: create a temp service with one registered report under factory f1."""
        tmp_dir = tempfile.mkdtemp()
        root = Path(tmp_dir)
        f1 = uuid4()
        f1_dir = root / str(f1)
        f1_dir.mkdir(parents=True, exist_ok=True)
        report_id = "REP-20261124-REQ01"
        report_file = f1_dir / f"incident_{report_id}.pdf"
        report_file.write_bytes(b"%PDF-1.4 fake")
        svc = ReportService(storage_dir=root, session=MagicMock())
        meta = ReportMetadata(
            report_id=report_id,
            report_type=ReportType.INCIDENT,
            format=ReportFormat.PDF,
            factory_id=f1,
            title="Incident Report",
            file_path=str(report_file),
            file_name=report_file.name,
            file_size_bytes=13,
            mime_type="application/pdf",
        )
        svc._registry[report_id] = meta
        return svc, f1, report_id, report_file, root

    def test_get_report_raises_value_error_when_factory_id_none(self):
        """get_report() must raise ValueError when factory_id is None."""
        svc, f1, report_id, _, _ = self._make_service_with_report()
        with self.assertRaises((ValueError, TypeError)):
            svc.get_report(report_id, factory_id=None)

    def test_get_report_file_path_raises_value_error_when_factory_id_none(self):
        """get_report_file_path() must raise ValueError when factory_id is None."""
        svc, f1, report_id, _, _ = self._make_service_with_report()
        with self.assertRaises((ValueError, TypeError)):
            svc.get_report_file_path(report_id, factory_id=None)

    def test_list_reports_returns_empty_when_factory_id_none(self):
        """list_reports(factory_id=None) must return an empty list (fail-closed)."""
        svc, f1, _, _, _ = self._make_service_with_report()
        result = svc.list_reports(factory_id=None)
        self.assertEqual(result, [])

    def test_cross_factory_rejection_confirmed(self):
        """A report owned by f1 must not be accessible by f2."""
        svc, f1, report_id, _, _ = self._make_service_with_report()
        f2 = uuid4()
        with self.assertRaises(ReportNotFoundError):
            svc.get_report(report_id, factory_id=f2)
        with self.assertRaises(ReportNotFoundError):
            svc.get_report_file_path(report_id, factory_id=f2)
        self.assertEqual(svc.list_reports(factory_id=f2), [])

    def test_get_report_succeeds_with_valid_factory_id(self):
        """get_report() must succeed when the correct factory_id is provided."""
        svc, f1, report_id, _, _ = self._make_service_with_report()
        meta = svc.get_report(report_id, factory_id=f1)
        self.assertEqual(meta.factory_id, f1)
        self.assertEqual(meta.report_id, report_id)


class TestReportsRepositoryResultLifecyclePhase6(unittest.TestCase):
    """Phase 6: Repository result materialization — data accessible after connection closed."""

    def test_fetchone_session_path_materializes_row(self):
        """_execute_fetchone() via Session path returns a materialized row."""
        mock_row = MagicMock()
        mock_row.id = str(uuid4())
        mock_row.name = "Test Factory"
        mock_row.slug = "test-factory"
        mock_row.timezone = "UTC"

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result

        repo = ReportRepository(session=mock_session)
        import sqlalchemy as sa
        query = sa.text("SELECT id, name, slug, timezone FROM factories WHERE id = :factory_id")
        row = repo._execute_fetchone(query, {"factory_id": str(uuid4())})
        self.assertIs(row, mock_row)
        mock_result.fetchone.assert_called_once()

    def test_fetchall_session_path_materializes_rows(self):
        """_execute_fetchall() via Session path returns materialized rows list."""
        mock_rows = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result

        repo = ReportRepository(session=mock_session)
        import sqlalchemy as sa
        query = sa.text("SELECT id FROM incidents WHERE factory_id = :factory_id ORDER BY opened_at DESC LIMIT :limit")
        rows = repo._execute_fetchall(query, {"factory_id": str(uuid4()), "limit": 10})
        self.assertEqual(rows, mock_rows)
        mock_result.fetchall.assert_called_once()

    def test_no_session_no_engine_raises_runtime_error(self):
        """All _execute_* methods raise RuntimeError when neither session nor engine provided."""
        repo = ReportRepository()
        import sqlalchemy as sa
        q = sa.text("SELECT 1")
        with self.assertRaises(RuntimeError):
            repo._execute_fetchone(q, {})
        with self.assertRaises(RuntimeError):
            repo._execute_fetchall(q, {})
        with self.assertRaises(RuntimeError):
            repo._execute_scalar(q, {})

    def test_get_factory_info_no_session_raises_runtime_error(self):
        """get_factory_info() propagates RuntimeError when no DB available."""
        repo = ReportRepository()
        with self.assertRaises(RuntimeError):
            repo.get_factory_info(uuid4())

    def test_get_factory_info_returns_default_on_db_error(self):
        """get_factory_info() returns default FactoryInfo when DB query fails (non-RuntimeError)."""
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("DB unavailable")
        repo = ReportRepository(session=mock_session)
        fid = uuid4()
        info = repo.get_factory_info(fid)
        self.assertEqual(info.factory_id, fid)

    def test_engine_path_materializes_results_and_closes_connection(self):
        """
        Verify ReportRepository(engine=...) opens a connection, executes a query,
        materializes results before closing, closes the connection, keeps rows
        accessible after closure/dispose, and cleans up connections on errors.
        """
        import sqlalchemy as sa
        from sqlalchemy import event

        engine = sa.create_engine("sqlite:///:memory:")
        fid = uuid4()
        opened_conns = []
        closed_count = 0

        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_conn, conn_record, conn_proxy):
            opened_conns.append(conn_proxy)

        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_conn, conn_record):
            nonlocal closed_count
            closed_count += 1

        # Create isolated in-memory schema and seed test rows
        with engine.begin() as conn:
            conn.execute(sa.text(
                "CREATE TABLE factories (id TEXT PRIMARY KEY, name TEXT, slug TEXT, timezone TEXT)"
            ))
            conn.execute(sa.text(
                "CREATE TABLE safety_rules (id TEXT PRIMARY KEY, factory_id TEXT, is_enabled INTEGER)"
            ))
            conn.execute(sa.text(
                "CREATE TABLE unobserved_gaps (id TEXT PRIMARY KEY, factory_id TEXT, reason TEXT, started_at TEXT, ended_at TEXT)"
            ))
            conn.execute(
                sa.text("INSERT INTO factories (id, name, slug, timezone) VALUES (:id, :name, :slug, :tz)"),
                {"id": str(fid), "name": "Alpha Plant", "slug": "alpha-plant", "tz": "Africa/Cairo"},
            )
            conn.execute(
                sa.text("INSERT INTO safety_rules (id, factory_id, is_enabled) VALUES ('r1', :fid, 1), ('r2', :fid, 1)"),
                {"fid": str(fid)},
            )
            conn.execute(
                sa.text("INSERT INTO unobserved_gaps (id, factory_id, reason, started_at, ended_at) VALUES ('g1', :fid, 'cam_offline', NULL, NULL)"),
                {"fid": str(fid)},
            )

        # Reset counters after setup
        opened_conns.clear()
        closed_count = 0

        repo = ReportRepository(engine=engine)

        # 1. fetchone via get_factory_info
        info = repo.get_factory_info(fid)
        self.assertEqual(len(opened_conns), 1)
        self.assertEqual(closed_count, 1)

        # 2. fetchall via _execute_fetchall
        rows = repo._execute_fetchall(
            sa.text("SELECT id, reason FROM unobserved_gaps WHERE factory_id = :factory_id"),
            {"factory_id": str(fid)},
        )
        self.assertNotIsInstance(rows, sa.engine.Result)
        self.assertEqual(len(opened_conns), 2)
        self.assertEqual(closed_count, 2)

        # 3. scalar via _execute_scalar
        rule_count = repo._execute_scalar(
            sa.text("SELECT count(*) FROM safety_rules WHERE factory_id = :factory_id AND is_enabled = 1"),
            {"factory_id": str(fid)},
        )
        self.assertEqual(rule_count, 2)
        self.assertEqual(len(opened_conns), 3)
        self.assertEqual(closed_count, 3)

        # 4. Dispose engine completely and verify materialized results remain accessible
        engine.dispose()
        self.assertEqual(info.name, "Alpha Plant")
        self.assertEqual(info.slug, "alpha-plant")
        self.assertEqual(info.timezone, "Africa/Cairo")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].reason, "cam_offline")

        # 5. Error cleanup: connection must still be checked in / closed when query fails
        err_engine = sa.create_engine("sqlite:///:memory:")
        err_closed = 0

        @event.listens_for(err_engine, "checkin")
        def on_err_checkin(dbapi_conn, conn_record):
            nonlocal err_closed
            err_closed += 1

        err_repo = ReportRepository(engine=err_engine)
        with self.assertRaises(sa.exc.OperationalError):
            err_repo._execute_fetchall(sa.text("SELECT * FROM nonexistent_table"), {})
        self.assertEqual(err_closed, 1)
        err_engine.dispose()


if __name__ == "__main__":
    unittest.main()
