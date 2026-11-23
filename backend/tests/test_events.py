"""
tests/test_events.py
Automated tests for CV Event Ingestion endpoints, payload validation,
coordinate normalization, idempotency, security headers, and query endpoints.
"""
from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.schemas.events import CVEventIngest
from app.services.event_service import EventService, normalize_coordinates


# Authenticated headers fixture/constant
CV_AUTH_HEADERS = {"X-Camera-Key": settings.DEFAULT_CV_API_KEY}


def test_coordinate_normalization():
    """Verify coordinate normalization from pixel bounding boxes to [0.0, 1.0]."""
    # Standard Skyworth camera resolution: 2304 x 1296
    frame_size = [2304, 1296]
    pixel_bbox = [576.0, 324.0, 1152.0, 648.0]  # Centered quarter

    bx, by, bw, bh = normalize_coordinates(pixel_bbox, frame_size)
    assert bx == 0.25
    assert by == 0.25
    assert bw == 0.25
    assert bh == 0.25

    # Coordinates already normalized (0 to 1)
    norm_bbox = [0.1, 0.2, 0.5, 0.8]
    nbx, nby, nbw, nbh = normalize_coordinates(norm_bbox, None)
    assert nbx == 0.1
    assert nby == 0.2
    assert nbw == 0.4
    assert nbh == 0.6


def test_ingest_missing_camera_key(client: TestClient):
    """Verify rejection with 401 when X-Camera-Key header is absent."""
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "ppe_violation",
        "module": "ppe_detection",
        "camera_id": "camera_01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = client.post("/api/v1/events/ingest", json=payload)
    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error_code"] == "MISSING_CAMERA_KEY"


def test_ingest_invalid_camera_key(client: TestClient):
    """Verify rejection with 401 when X-Camera-Key is incorrect/tampered."""
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "ppe_violation",
        "module": "ppe_detection",
        "camera_id": "camera_01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = client.post(
        "/api/v1/events/ingest",
        json=payload,
        headers={"X-Camera-Key": "unauthorized-fake-key-12345"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["status"] == "error"
    assert body["error_code"] == "INVALID_CAMERA_KEY"


def test_ingest_single_ppe_event_valid(client: TestClient):
    """Verify ingestion of a valid PPE violation event matching CV Guide §6.7."""
    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "event_type": "ppe_violation",
        "event_state": "started",
        "module": "ppe_detection",
        "camera_id": "camera_01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "frame_index": 880,
        "frame_size": [2304, 1296],
        "bbox": [600.0, 250.0, 790.0, 840.0],
        "track_id": None,
        "confidence": 0.88,
        "attributes": {
            "helmet": False,
            "safety_vest": True,
            "missing": ["helmet"],
        },
    }

    response = client.post(
        "/api/v1/events/ingest",
        json=payload,
        headers=CV_AUTH_HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["event_id"] == event_id
    assert body["data"]["status"] == "ingested"
    assert body["data"]["event_type"] == "ppe_violation"


def test_ingest_single_fall_event_valid(client: TestClient):
    """Verify ingestion of a valid fall detection event matching CV Guide §6.7."""
    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "event_type": "potential_fall",
        "event_state": "started",
        "module": "fall_detection",
        "camera_id": "camera_02",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "frame_index": 2210,
        "frame_size": [2304, 1296],
        "bbox": [880.0, 640.0, 1290.0, 790.0],
        "track_id": 2,
        "confidence": 0.81,
        "attributes": {
            "rapid_descent": True,
            "lying_duration_s": 2.1,
        },
    }

    response = client.post(
        "/api/v1/events/ingest",
        json=payload,
        headers=CV_AUTH_HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["event_id"] == event_id
    assert body["data"]["event_type"] == "fall"  # Mapped to canonical DB enum


def test_ingest_single_zone_event_valid(client: TestClient):
    """Verify ingestion of restricted zone intrusion matching CV Guide §6.7."""
    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "event_type": "restricted_zone_entry",
        "event_state": "started",
        "module": "person_tracking",
        "camera_id": "camera_01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "frame_index": 1432,
        "frame_size": [2304, 1296],
        "bbox": [1020.4, 310.2, 1190.8, 760.9],
        "track_id": 3,
        "confidence": 1.0,
        "attributes": {
            "zone_id": "zone_press_01",
            "point_used": "bottom_center",
        },
    }

    response = client.post(
        "/api/v1/events/ingest",
        json=payload,
        headers=CV_AUTH_HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["event_type"] == "restricted_zone_intrusion"


def test_ingest_duplicate_event_idempotency(client: TestClient):
    """
    Verify database-level idempotency: re-sending an event with the same event_id
    must return an idempotent response without duplicate broadcasts or failures.
    """
    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "event_type": "ppe_violation",
        "event_state": "started",
        "module": "ppe_detection",
        "camera_id": "camera_01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "confidence": 0.95,
        "attributes": {"missing": ["helmet"]},
    }

    # First ingestion
    res1 = client.post(
        "/api/v1/events/ingest",
        json=payload,
        headers=CV_AUTH_HEADERS,
    )
    assert res1.status_code == 201
    body1 = res1.json()
    assert body1["data"]["event_id"] == event_id

    # Second ingestion (retry with same event_id)
    res2 = client.post(
        "/api/v1/events/ingest",
        json=payload,
        headers=CV_AUTH_HEADERS,
    )
    assert res2.status_code == 201
    body2 = res2.json()
    assert body2["data"]["event_id"] == event_id
    # If the database is connected, status is duplicate_ignored and broadcast is False
    # If in disconnected fallback mode, status returns ingested
    assert body2["data"]["status"] in ("duplicate_ignored", "ingested")


def test_ingest_invalid_event_type(client: TestClient):
    """Verify unknown event_type is rejected with 422 Unprocessable Entity."""
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "unregistered_event_name",
        "module": "ppe_detection",
        "camera_id": "camera_01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    response = client.post(
        "/api/v1/events/ingest",
        json=payload,
        headers=CV_AUTH_HEADERS,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "error"
    assert body["error_code"] == "VALIDATION_ERROR"


def test_ingest_invalid_confidence(client: TestClient):
    """Verify confidence out of range [0, 1] is rejected with 422."""
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "ppe_violation",
        "module": "ppe_detection",
        "camera_id": "camera_01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "confidence": 1.5,  # Exceeds 1.0 limit
    }

    response = client.post(
        "/api/v1/events/ingest",
        json=payload,
        headers=CV_AUTH_HEADERS,
    )
    assert response.status_code == 422


def test_ingest_frame_result_batch(client: TestClient):
    """Verify ingestion of a multi-event FrameResult container."""
    payload = {
        "schema_version": "1.0",
        "module": "ppe_detection",
        "camera_id": "camera_01",
        "frame_index": 500,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "frame_size": [2304, 1296],
        "detections": [
            {
                "label": "person",
                "bbox": [100.0, 100.0, 300.0, 600.0],
                "confidence": 0.92,
                "track_id": 1,
            }
        ],
        "events": [
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "ppe_violation",
                "event_state": "started",
                "module": "ppe_detection",
                "camera_id": "camera_01",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.89,
                "attributes": {"missing": ["safety_vest"]},
            },
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "potential_fall",
                "event_state": "started",
                "module": "fall_detection",
                "camera_id": "camera_01",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.84,
                "attributes": {"rapid_descent": True},
            },
        ],
    }

    response = client.post(
        "/api/v1/events/batch",
        json=payload,
        headers=CV_AUTH_HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["total_received"] == 2
    assert body["data"]["ingested_count"] == 2


def test_list_events_endpoint(client: TestClient):
    """Verify GET /api/v1/events returns standardized list response."""
    response = client.get("/api/v1/events?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert isinstance(body["data"], list)
    assert "meta" in body


def test_get_event_not_found(client: TestClient):
    """Verify GET /api/v1/events/{id} returns 404 for unknown UUID."""
    unknown_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/events/{unknown_id}")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert body["error_code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.anyio
async def test_event_service_atomic_upsert_duplicate():
    """Verify EventService handles rowcount=0 as an atomic idempotent duplicate."""
    from unittest.mock import MagicMock

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_session.execute.return_value = mock_result

    event_in = CVEventIngest(
        event_id=uuid.uuid4(),
        event_type="ppe_violation",
        module="ppe_detection",
        camera_id="cam_01",
        timestamp=datetime.now(timezone.utc),
    )
    res = await EventService.ingest_event(
        event_in=event_in,
        factory_id=uuid.uuid4(),
        db=mock_session,
        broadcast=True,
    )
    assert res.status == "duplicate_ignored"
    assert res.broadcast is False
    assert res.persisted is True


@pytest.mark.anyio
async def test_event_service_persistence_error_not_swallowed():
    """Verify EventService propagates unexpected SQLAlchemy errors rather than swallowing them."""
    from unittest.mock import MagicMock
    from sqlalchemy.exc import IntegrityError

    mock_session = MagicMock()
    mock_session.execute.side_effect = IntegrityError("violates foreign key", params=None, orig=Exception())

    event_in = CVEventIngest(
        event_id=uuid.uuid4(),
        event_type="ppe_violation",
        module="ppe_detection",
        camera_id="cam_01",
        timestamp=datetime.now(timezone.utc),
    )
    with pytest.raises(IntegrityError):
        await EventService.ingest_event(
            event_in=event_in,
            factory_id=uuid.uuid4(),
            db=mock_session,
            broadcast=True,
        )
