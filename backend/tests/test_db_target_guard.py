"""
Guards that reject operix_db before an engine or a connection exists.

These tests never open a socket. The import check patches create_engine and
socket.connect so a regression fails closed instead of reaching PostgreSQL.
"""
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from app.core.db_target import (
    enforce_configured_test_target,
    require_disposable_live_postgres_url,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
_DISPOSABLE = "postgresql+psycopg://blocked:blocked@127.0.0.1:1/operix_disposable_ci"
_PRODUCTION = "postgresql+psycopg://blocked:blocked@127.0.0.1:1/operix_db"


def test_operix_db_rejected_even_when_allow_flag_is_true(monkeypatch):
    monkeypatch.setenv("OPERIX_ALLOW_LIVE_DB", "true")
    with pytest.raises(RuntimeError, match="operix_db"):
        enforce_configured_test_target(_PRODUCTION)
    with pytest.raises(RuntimeError, match="operix_db"):
        require_disposable_live_postgres_url(_PRODUCTION)


def test_live_url_must_name_a_disposable_postgres_database():
    with pytest.raises(RuntimeError, match="TEST_DATABASE_URL"):
        require_disposable_live_postgres_url("")
    with pytest.raises(RuntimeError, match="postgresql"):
        require_disposable_live_postgres_url("sqlite:///./operix_disposable_ci.db")
    with pytest.raises(RuntimeError, match="does not name a database"):
        require_disposable_live_postgres_url("postgresql+psycopg://blocked:blocked@127.0.0.1:1/")

    accepted = require_disposable_live_postgres_url(_DISPOSABLE)
    assert accepted == _DISPOSABLE


def test_empty_test_database_url_is_rejected():
    with pytest.raises(RuntimeError, match="DATABASE_URL is empty"):
        enforce_configured_test_target("  ")


def test_importing_database_module_does_not_reach_operix_db():
    """Import app.core.database with the production name configured.

    create_engine and socket.connect are both replaced before the import.
    A passing run has zero engine calls and zero connect attempts.
    """
    script = textwrap.dedent(
        """
        import os
        import socket
        import sys

        attempts = []

        def _blocked_connect(self, *args, **kwargs):
            attempts.append("connect")
            raise OSError("network blocked")

        def _blocked_create_connection(*args, **kwargs):
            attempts.append("create_connection")
            raise OSError("network blocked")

        socket.socket.connect = _blocked_connect
        socket.create_connection = _blocked_create_connection

        import sqlalchemy

        engine_calls = []

        def _blocked_create_engine(*args, **kwargs):
            engine_calls.append("create_engine")
            raise RuntimeError("create_engine was called")

        sqlalchemy.create_engine = _blocked_create_engine

        os.environ["OPERIX_REJECT_PRODUCTION_DB"] = "1"
        os.environ["OPERIX_ALLOW_LIVE_DB"] = "true"
        os.environ["DATABASE_URL"] = "postgresql+psycopg://blocked:blocked@127.0.0.1:1/operix_db"
        os.environ["WS_TICKET_KEY"] = "test-ws-ticket-key-32bytes-min-pad!"
        os.environ["SECRET_KEY"] = "test-secret-key-change-in-prod-32bytes!"

        sys.path.insert(0, sys.argv[1])
        try:
            import app.core.database  # noqa: F401
        except RuntimeError as exc:
            message = str(exc).splitlines()[0]
            rejected = "operix_db" in message and "create_engine was called" not in message
            print(f"rejected={int(rejected)}")
            print(f"engine_calls={len(engine_calls)}")
            print(f"connect_attempts={len(attempts)}")
            print(f"error_kind={type(exc).__name__}")
        else:
            print("rejected=0")
            print(f"engine_calls={len(engine_calls)}")
            print(f"connect_attempts={len(attempts)}")
            print("error_kind=none")
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(BACKEND_DIR)],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    output = completed.stdout
    assert completed.returncode == 0, completed.stderr
    assert "rejected=1" in output
    assert "engine_calls=0" in output
    assert "connect_attempts=0" in output
    assert "operix_app" not in output
    assert "127.0.0.1" not in output


def _run_isolated(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", script, str(BACKEND_DIR)],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        check=False,
    )


def test_importing_conftest_does_not_connect_to_operix_db():
    """Import the real test configuration with the network closed.

    .env.test supplies the URL. create_engine may run for that test URL.
    It must not be asked to open operix_db, and no socket may connect.
    """
    script = textwrap.dedent(
        """
        import importlib.util
        import socket
        import sys

        backend = sys.argv[1]
        sys.path.insert(0, backend)
        attempts = []

        def _blocked_connect(self, *args, **kwargs):
            attempts.append("connect")
            raise OSError("network blocked")

        def _blocked_create_connection(*args, **kwargs):
            attempts.append("create_connection")
            raise OSError("network blocked")

        socket.socket.connect = _blocked_connect
        socket.create_connection = _blocked_create_connection

        import sqlalchemy
        from sqlalchemy.engine.url import make_url

        original = sqlalchemy.create_engine
        names = []

        def _recording_create_engine(*args, **kwargs):
            raw = args[0] if args else kwargs.get("url", "")
            name = (make_url(str(raw)).database or "").lower()
            names.append(name)
            if name == "operix_db":
                raise RuntimeError("create_engine was called for operix_db")
            return original(*args, **kwargs)

        sqlalchemy.create_engine = _recording_create_engine

        spec = importlib.util.spec_from_file_location(
            "operix_conftest_under_test",
            backend + "/tests/conftest.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print("names=" + ",".join(names))
        print(f"connect_attempts={len(attempts)}")
        print("operix_db_engine=0")
        """
    )
    completed = _run_isolated(script)
    output = completed.stdout
    assert completed.returncode == 0, completed.stderr
    assert "operix_db_engine=0" in output
    assert "connect_attempts=0" in output
    name_line = output.split("names=", 1)[1].splitlines()[0]
    assert "operix_db" not in {name.strip().lower() for name in name_line.split(",") if name}


def test_conftest_rejects_operix_db_before_engine_even_if_allow_flag_is_set():
    """If test configuration still names operix_db, import must fail closed.

    load_dotenv is a no-op so the poisoned URL is the one the guard sees.
    OPERIX_ALLOW_LIVE_DB is set and must not be consulted.
    """
    script = textwrap.dedent(
        """
        import importlib.util
        import os
        import socket
        import sys

        backend = sys.argv[1]
        sys.path.insert(0, backend)
        attempts = []

        def _blocked_connect(self, *args, **kwargs):
            attempts.append("connect")
            raise OSError("network blocked")

        def _blocked_create_connection(*args, **kwargs):
            attempts.append("create_connection")
            raise OSError("network blocked")

        socket.socket.connect = _blocked_connect
        socket.create_connection = _blocked_create_connection

        import dotenv
        import sqlalchemy

        dotenv.load_dotenv = lambda *args, **kwargs: False

        engine_calls = []

        def _blocked_create_engine(*args, **kwargs):
            engine_calls.append("create_engine")
            raise RuntimeError("create_engine was called")

        sqlalchemy.create_engine = _blocked_create_engine

        os.environ["OPERIX_ALLOW_LIVE_DB"] = "true"
        os.environ["DATABASE_URL"] = "postgresql+psycopg://blocked:blocked@127.0.0.1:1/operix_db"
        os.environ["WS_TICKET_KEY"] = "test-ws-ticket-key-32bytes-min-pad!"
        os.environ["SECRET_KEY"] = "test-secret-key-change-in-prod-32bytes!"

        spec = importlib.util.spec_from_file_location(
            "operix_conftest_reject_operix_db",
            backend + "/tests/conftest.py",
        )
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except RuntimeError as exc:
            message = str(exc).splitlines()[0]
            rejected = "operix_db" in message and "create_engine was called" not in message
            print(f"rejected={int(rejected)}")
            print(f"engine_calls={len(engine_calls)}")
            print(f"connect_attempts={len(attempts)}")
        else:
            print("rejected=0")
            print(f"engine_calls={len(engine_calls)}")
            print(f"connect_attempts={len(attempts)}")
        """
    )
    completed = _run_isolated(script)
    output = completed.stdout
    assert completed.returncode == 0, completed.stderr
    assert "rejected=1" in output
    assert "engine_calls=0" in output
    assert "connect_attempts=0" in output
    assert "127.0.0.1" not in output


def test_importing_live_postgres_module_rejects_operix_db_before_engine():
    """Importing the live module with a production URL must not create an engine."""
    script = textwrap.dedent(
        """
        import importlib.util
        import os
        import socket
        import sys

        backend = sys.argv[1]
        sys.path.insert(0, backend)
        attempts = []

        def _blocked_connect(self, *args, **kwargs):
            attempts.append("connect")
            raise OSError("network blocked")

        socket.socket.connect = _blocked_connect
        socket.create_connection = lambda *args, **kwargs: (_ for _ in ()).throw(OSError("network blocked"))

        import sqlalchemy

        engine_calls = []

        def _blocked_create_engine(*args, **kwargs):
            engine_calls.append("create_engine")
            raise RuntimeError("create_engine was called")

        sqlalchemy.create_engine = _blocked_create_engine

        os.environ["OPERIX_ALLOW_LIVE_DB"] = "true"
        os.environ["TEST_DATABASE_URL"] = "postgresql+psycopg://blocked:blocked@127.0.0.1:1/operix_db"
        os.environ["DATABASE_URL"] = "sqlite:///./test_operix.db"
        os.environ["WS_TICKET_KEY"] = "test-ws-ticket-key-32bytes-min-pad!"
        os.environ["SECRET_KEY"] = "test-secret-key-change-in-prod-32bytes!"

        spec = importlib.util.spec_from_file_location(
            "operix_live_postgres_under_test",
            backend + "/tests/test_live_postgres.py",
        )
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except RuntimeError as exc:
            message = str(exc).splitlines()[0]
            rejected = "operix_db" in message and "create_engine was called" not in message
            print(f"rejected={int(rejected)}")
            print(f"engine_calls={len(engine_calls)}")
            print(f"connect_attempts={len(attempts)}")
        else:
            print("rejected=0")
            print(f"engine_calls={len(engine_calls)}")
            print(f"connect_attempts={len(attempts)}")
        """
    )
    completed = _run_isolated(script)
    output = completed.stdout
    assert completed.returncode == 0, completed.stderr
    assert "rejected=1" in output
    assert "engine_calls=0" in output
    assert "connect_attempts=0" in output
    assert "127.0.0.1" not in output
