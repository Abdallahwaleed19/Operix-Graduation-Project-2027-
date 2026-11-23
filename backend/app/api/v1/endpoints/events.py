"""
app/api/v1/endpoints/events.py
REST API endpoints for Computer Vision event ingestion and historical queries.
"""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ....core.errors import ResourceNotFoundException
from ....models.enums import EventType
from ....models.incidents import Event
from ....schemas.common import APIResponse, APIResponseMeta
from ....schemas.events import (
    CVEventIngest,
    CVFrameResultIngest,
    EventBatchIngestResponse,
    EventIngestResponse,
    EventResponse,
)
from ....services.event_service import EventService
from ...deps import get_current_factory_id, get_db, require_cv_producer_auth

router = APIRouter(prefix="/events", tags=["Events & CV Ingestion"])


@router.post(
    "/ingest",
    response_model=APIResponse[EventIngestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a single Computer Vision safety event",
    description="Receives an event from authenticated CV detection modules and broadcasts to WebSockets.",
)
async def ingest_single_event(
    event_in: CVEventIngest,
    factory_id: uuid.UUID = Depends(require_cv_producer_auth),
    db: Session = Depends(get_db),
) -> APIResponse[EventIngestResponse]:
    """Ingest, validate, persist, and broadcast a single CV event."""
    result = await EventService.ingest_event(
        event_in=event_in,
        factory_id=factory_id,
        db=db,
        broadcast=True,
    )

    meta = APIResponseMeta(factory_id=factory_id, api_version="v1")
    return APIResponse[EventIngestResponse](
        status="success",
        data=result,
        meta=meta,
    )


@router.post(
    "/batch",
    response_model=APIResponse[EventBatchIngestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest batch of events from a single frame",
    description="Receives a FrameResult container containing multiple detections and safety events from an authenticated camera.",
)
async def ingest_frame_result(
    frame_result: CVFrameResultIngest,
    factory_id: uuid.UUID = Depends(require_cv_producer_auth),
    db: Session = Depends(get_db),
) -> APIResponse[EventBatchIngestResponse]:
    """Process all events emitted from a single processed frame."""
    result = await EventService.ingest_batch(
        frame_result=frame_result,
        factory_id=factory_id,
        db=db,
    )

    meta = APIResponseMeta(factory_id=factory_id, api_version="v1")
    return APIResponse[EventBatchIngestResponse](
        status="success",
        data=result,
        meta=meta,
    )


@router.get(
    "",
    response_model=APIResponse[List[EventResponse]],
    summary="List historical safety events",
    description="Query logged safety events for the current tenant factory with optional filters.",
)
def list_events(
    factory_id: uuid.UUID = Depends(get_current_factory_id),
    camera_id: Optional[uuid.UUID] = Query(None, description="Filter by camera UUID"),
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records offset"),
    db: Session = Depends(get_db),
) -> APIResponse[List[EventResponse]]:
    """Retrieve filtered events for dashboard history views."""
    stmt = (
        select(Event)
        .where(Event.factory_id == factory_id)
        .order_by(desc(Event.detected_at))
        .offset(offset)
        .limit(limit)
    )

    if camera_id is not None:
        stmt = stmt.where(Event.camera_id == camera_id)
    if event_type is not None:
        stmt = stmt.where(Event.event_type == event_type)

    try:
        events = db.execute(stmt).scalars().all()
        data = [EventResponse.model_validate(e) for e in events]
    except Exception:
        # Graceful fallback if database is offline
        data = []

    meta = APIResponseMeta(factory_id=factory_id, api_version="v1")
    return APIResponse[List[EventResponse]](
        status="success",
        data=data,
        meta=meta,
    )


@router.get(
    "/{event_id}",
    response_model=APIResponse[EventResponse],
    summary="Get single event by ID",
)
def get_event(
    event_id: uuid.UUID,
    factory_id: uuid.UUID = Depends(get_current_factory_id),
    db: Session = Depends(get_db),
) -> APIResponse[EventResponse]:
    """Retrieve single event details by UUID."""
    stmt = select(Event).where(
        Event.factory_id == factory_id,
        Event.id == event_id,
    )

    try:
        event = db.execute(stmt).scalars().first()
    except Exception:
        event = None

    if not event:
        raise ResourceNotFoundException("Event", event_id)

    meta = APIResponseMeta(factory_id=factory_id, api_version="v1")
    return APIResponse[EventResponse](
        status="success",
        data=EventResponse.model_validate(event),
        meta=meta,
    )
