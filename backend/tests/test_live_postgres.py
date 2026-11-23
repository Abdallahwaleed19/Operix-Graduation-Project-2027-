"""
tests/test_live_postgres.py
Verification suite for real PostgreSQL integration.

SAFETY RULES:
  - Marked `live_db`: excluded from default pytest runs (see pytest.ini).
  - Importing this module never opens a database connection.
  - TEST_DATABASE_URL is parsed before any live engine is created.
  - operix_db is rejected unconditionally. OPERIX_ALLOW_LIVE_DB is ignored.
  - Live tests require an explicitly named disposable PostgreSQL database.
  - After connect, current_database() is checked again before any writes.
"""
import os

import pytest

from app.core.db_target import require_disposable_live_postgres_url


def _live_skip_reason() -> str | None:
    """Decide whether live tests can run. Never connects.

    An unset TEST_DATABASE_URL skips the module. A URL that names operix_db,
    omits a database name, or is not PostgreSQL raises before any engine exists.
    OPERIX_ALLOW_LIVE_DB is not read.
    """
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        return (
            "TEST_DATABASE_URL is not set. Live tests require an explicitly "
            "named disposable PostgreSQL database and do not connect at import."
        )
    require_disposable_live_postgres_url(url)
    return None


_LIVE_SKIP_REASON = _live_skip_reason()

pytestmark = [
    pytest.mark.live_db,
    pytest.mark.skipif(
        _LIVE_SKIP_REASON is not None,
        reason=_LIVE_SKIP_REASON or "live database not configured",
    ),
]

# Model imports happen only after the URL has been parsed. An operix_db URL
# raises above, before these imports and before create_engine.
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import sessionmaker

from app.models.enums import CameraType, EventType, FactoryStatus, SourceStatus
from app.models.incidents import Event
from app.models.operational import Camera
from app.models.tenant import Factory

# Deterministic test UUIDs for safe cleanup
TEST_FACTORY_ID = uuid.UUID("99999999-0001-0001-0001-000000000001")
TEST_CAMERA_ID = uuid.UUID("99999999-0002-0001-0001-000000000001")
TEST_EVENT_ID_1 = uuid.UUID("99999999-0003-0001-0001-000000000001")
TEST_EVENT_ID_2 = uuid.UUID("99999999-0003-0001-0001-000000000002")


@pytest.fixture(scope="module")
def db_session():
    """Yield a session on an explicitly named disposable PostgreSQL database.

    LAYER 1 runs before create_engine. LAYER 2 runs after connect and before
    any test writes. operix_db fails both layers. OPERIX_ALLOW_LIVE_DB is ignored.
    """
    # LAYER 1 — parse only. No engine and no connection yet.
    url = require_disposable_live_postgres_url(os.environ.get("TEST_DATABASE_URL", ""))

    live_engine = create_engine(
        url,
        pool_pre_ping=False,
        connect_args={"connect_timeout": 2},
    )
    session = sessionmaker(autocommit=False, autoflush=False, bind=live_engine)()
    try:
        # LAYER 2 — identity of the database actually reached.
        current_db = session.execute(text("SELECT current_database()")).scalar()
        if current_db == "operix_db":
            raise RuntimeError(
                "BLOCKED: live test connected to operix_db. "
                "Closing without writes. OPERIX_ALLOW_LIVE_DB does not bypass this."
            )
        yield session
        try:
            session.rollback()
            session.execute(delete(Event).where(Event.id.in_([TEST_EVENT_ID_1, TEST_EVENT_ID_2])))
            session.execute(delete(Camera).where(Camera.id == TEST_CAMERA_ID))
            session.execute(delete(Factory).where(Factory.id == TEST_FACTORY_ID))
            session.commit()
        except Exception:
            session.rollback()
    finally:
        session.close()
        live_engine.dispose()


def test_real_postgres_connection_identity(db_session):
    """Verify live connection to PostgreSQL, database name, and user identity.

    The fixture has already rejected operix_db before and after connect.
    The database name is whatever TEST_DATABASE_URL named.
    """
    result = db_session.execute(text("SELECT current_database(), current_user, version();")).fetchone()
    current_db, current_user, pg_version = result[0], result[1], result[2]

    # Safety: confirm we are not on production (belt-and-suspenders)
    assert current_db != "operix_db", (
        f"BLOCKED: test is running against production database '{current_db}'"
    )
    assert current_user in ("postgres", "operix_app"), f"Unexpected connected user '{current_user}'"
    assert "PostgreSQL" in pg_version


def test_real_postgres_schema_tables_present(db_session):
    """Verify that all core tables exist on the disposable live database."""
    result = db_session.execute(
        text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
    ).fetchall()
    table_names = {row[0] for row in result}

    expected_core_tables = {
        "factories",
        "users",
        "auth_tokens",
        "cameras",
        "events",
        "incidents",
        "factory_memberships",
    }
    for t in expected_core_tables:
        assert t in table_names, f"Core table '{t}' missing from the disposable live database!"


def test_real_postgres_insert_and_select(db_session):
    """Verify real INSERT and SELECT of an Event record on the disposable database."""
    # 1. Ensure test factory exists
    factory = db_session.get(Factory, TEST_FACTORY_ID)
    if not factory:
        factory = Factory(
            id=TEST_FACTORY_ID,
            name="Test Verification Factory 99",
            slug=f"test-factory-{uuid.uuid4().hex[:8]}",
            status=FactoryStatus.ACTIVE,
        )
        db_session.add(factory)
        db_session.flush()

    # 2. Ensure test camera exists
    camera = db_session.get(Camera, TEST_CAMERA_ID)
    if not camera:
        camera = Camera(
            id=TEST_CAMERA_ID,
            factory_id=TEST_FACTORY_ID,
            name="Test Verification Cam 99",
            camera_type=CameraType.CCTV,
            stream_url_ref="rtsp://test/live",
            status=SourceStatus.AVAILABLE,
        )
        db_session.add(camera)
        db_session.flush()

    # 3. Clean any preexisting test event
    db_session.execute(delete(Event).where(Event.id == TEST_EVENT_ID_1))
    db_session.flush()

    # 4. Insert test event
    now = datetime.now(timezone.utc)
    event = Event(
        id=TEST_EVENT_ID_1,
        factory_id=TEST_FACTORY_ID,
        camera_id=TEST_CAMERA_ID,
        event_type=EventType.PPE_VIOLATION,
        detected_at=now,
        confidence=0.92,
        track_ref=42,
        bbox_x=0.15,
        bbox_y=0.25,
        bbox_w=0.35,
        bbox_h=0.45,
        details={"test_marker": True, "ppe_missing": ["helmet"]},
    )
    db_session.add(event)
    db_session.commit()

    # 5. Read back and verify
    fetched = db_session.get(Event, TEST_EVENT_ID_1)
    assert fetched is not None
    assert fetched.factory_id == TEST_FACTORY_ID
    assert fetched.camera_id == TEST_CAMERA_ID
    assert fetched.event_type == EventType.PPE_VIOLATION
    assert fetched.confidence == 0.92
    assert fetched.details.get("test_marker") is True


def test_real_postgres_atomic_duplicate_handling(db_session):
    """Verify database-level atomic idempotency via ON CONFLICT (id) DO NOTHING."""
    # Ensure prerequisite factory and camera exist
    factory = db_session.get(Factory, TEST_FACTORY_ID)
    if not factory:
        factory = Factory(
            id=TEST_FACTORY_ID,
            name="Test Verification Factory 99",
            slug=f"test-factory-{uuid.uuid4().hex[:8]}",
            status=FactoryStatus.ACTIVE,
        )
        db_session.add(factory)
        db_session.flush()

    camera = db_session.get(Camera, TEST_CAMERA_ID)
    if not camera:
        camera = Camera(
            id=TEST_CAMERA_ID,
            factory_id=TEST_FACTORY_ID,
            name="Test Verification Cam 99",
            camera_type=CameraType.CCTV,
            stream_url_ref="rtsp://test/live",
            status=SourceStatus.AVAILABLE,
        )
        db_session.add(camera)
        db_session.flush()

    # Clean existing record if any
    db_session.execute(delete(Event).where(Event.id == TEST_EVENT_ID_2))
    db_session.commit()

    # First Insert: should insert 1 row
    stmt1 = (
        pg_insert(Event)
        .values(
            id=TEST_EVENT_ID_2,
            factory_id=TEST_FACTORY_ID,
            camera_id=TEST_CAMERA_ID,
            event_type=EventType.FALL,
            detected_at=datetime.now(timezone.utc),
            confidence=0.88,
            details={"run": 1},
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    res1 = db_session.execute(stmt1)
    db_session.commit()
    assert res1.rowcount == 1, f"Expected rowcount=1 on first insert, got {res1.rowcount}"

    # Second Insert with same id: should conflict and insert 0 rows
    stmt2 = (
        pg_insert(Event)
        .values(
            id=TEST_EVENT_ID_2,
            factory_id=TEST_FACTORY_ID,
            camera_id=TEST_CAMERA_ID,
            event_type=EventType.FALL,
            detected_at=datetime.now(timezone.utc),
            confidence=0.88,
            details={"run": 2},
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    res2 = db_session.execute(stmt2)
    db_session.commit()
    assert res2.rowcount == 0, f"Expected rowcount=0 on duplicate insert, got {res2.rowcount}"


def test_real_postgres_transaction_rollback(db_session):
    """Verify transaction rollback prevents persistence of uncommitted events."""
    rollback_event_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Begin subtransaction or explicit rollback block
    try:
        event = Event(
            id=rollback_event_id,
            factory_id=TEST_FACTORY_ID,
            camera_id=TEST_CAMERA_ID,
            event_type=EventType.PPE_VIOLATION,
            detected_at=now,
        )
        db_session.add(event)
        db_session.flush()
        # Force rollback
        db_session.rollback()
    except Exception:
        db_session.rollback()

    # Assert event was not persisted
    fetched = db_session.get(Event, rollback_event_id)
    assert fetched is None, "Rolled-back event should not exist in database!"
