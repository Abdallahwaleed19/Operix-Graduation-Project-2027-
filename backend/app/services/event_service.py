"""
app/services/event_service.py
Service layer handling CV event validation, coordinate normalization,
idempotent PostgreSQL persistence, and real-time WebSocket distribution.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import InterfaceError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..core.logging import logger
from ..core.websocket import ws_manager
from ..models.enums import EventType
from ..models.incidents import Event
from ..schemas.events import (
    CV_TO_DB_EVENT_TYPE,
    CVEventIngest,
    CVFrameResultIngest,
    EventBatchIngestResponse,
    EventIngestResponse,
)
from .rule_evaluation_service import RuleEvaluationResult, RuleEvaluationService


def normalize_coordinates(
    bbox: Optional[List[float]],
    frame_size: Optional[List[int]],
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Convert absolute pixel bounding box [x1, y1, x2, y2] to
    normalized [bbox_x, bbox_y, bbox_w, bbox_h] in range [0.0, 1.0].
    """
    if not bbox or len(bbox) < 4:
        return None, None, None, None

    x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]

    # If frame_size provided, normalize using frame dimensions
    if frame_size and len(frame_size) >= 2 and frame_size[0] > 0 and frame_size[1] > 0:
        width = float(frame_size[0])
        height = float(frame_size[1])

        norm_x = max(0.0, min(1.0, x1 / width))
        norm_y = max(0.0, min(1.0, y1 / height))
        norm_w = max(0.0, min(1.0, (x2 - x1) / width))
        norm_h = max(0.0, min(1.0, (y2 - y1) / height))
        return round(norm_x, 4), round(norm_y, 4), round(norm_w, 4), round(norm_h, 4)

    # If coordinates are already normalized (0.0 to 1.0)
    if all(0.0 <= val <= 1.0 for val in (x1, y1, x2, y2)):
        norm_w = max(0.0, min(1.0, x2 - x1)) if x2 >= x1 else x2
        norm_h = max(0.0, min(1.0, y2 - y1)) if y2 >= y1 else y2
        return round(x1, 4), round(y1, 4), round(norm_w, 4), round(norm_h, 4)

    # Cannot normalize without frame_size
    return None, None, None, None


def resolve_camera_uuid(camera_id_str: str) -> Optional[uuid.UUID]:
    """Parse camera_id string into UUID if valid, or return None."""
    try:
        return uuid.UUID(camera_id_str)
    except ValueError:
        return None


class EventService:
    """Orchestrates event ingestion, DB persistence, and real-time delivery."""

    @staticmethod
    async def ingest_event(
        event_in: CVEventIngest,
        factory_id: uuid.UUID,
        db: Optional[Session] = None,
        broadcast: bool = True,
    ) -> EventIngestResponse:
        """
        Process a single Computer Vision event with idempotency and real-time broadcast.
        """
        # 1. Map CV event type to canonical DB EventType
        db_event_type = CV_TO_DB_EVENT_TYPE.get(event_in.event_type, EventType.PPE_VIOLATION)

        # 2. Normalize bounding box coordinates
        bbox_x, bbox_y, bbox_w, bbox_h = normalize_coordinates(
            bbox=event_in.bbox,
            frame_size=event_in.frame_size,
        )

        camera_uuid = resolve_camera_uuid(event_in.camera_id)

        # 3. Construct rich details payload
        details_payload: Dict[str, Any] = {
            "module": event_in.module,
            "event_state": event_in.event_state,
            "raw_camera_tag": event_in.camera_id,
            "frame_index": event_in.frame_index,
            "frame_size": event_in.frame_size,
            "raw_bbox": event_in.bbox,
            **event_in.attributes,
        }

        persisted = False
        primary_rule_id: Optional[uuid.UUID] = None
        matched_count = 0
        should_notify = False
        persisted_event: Optional[Event] = None

        # 4. Database-level atomic idempotency & persistence
        if db is not None:
            try:
                bind = db.get_bind()
                dialect_name = bind.dialect.name if bind is not None else "postgresql"
                insert_fn = pg_insert if dialect_name == "postgresql" else sqlite_insert

                insert_stmt = (
                    insert_fn(Event)
                    .values(
                        id=event_in.event_id,
                        factory_id=factory_id,
                        event_type=db_event_type,
                        camera_id=camera_uuid,
                        detected_at=event_in.timestamp,
                        confidence=event_in.confidence,
                        track_ref=event_in.track_id,
                        bbox_x=bbox_x,
                        bbox_y=bbox_y,
                        bbox_w=bbox_w,
                        bbox_h=bbox_h,
                        details=details_payload,
                    )
                    .on_conflict_do_nothing(index_elements=["id"])
                )
                result = db.execute(insert_stmt)
                db.commit()

                rowcount = getattr(result, "rowcount", 1)
                if rowcount == 0:
                    # Idempotent duplicate: existing record was not overwritten
                    logger.info(f"Duplicate event {event_in.event_id} ignored via database-level idempotency.")
                    existing_rule_id = None
                    try:
                        existing = db.get(Event, event_in.event_id)
                        raw_rid = getattr(existing, "rule_id", None)
                        if isinstance(raw_rid, uuid.UUID):
                            existing_rule_id = raw_rid
                        elif isinstance(raw_rid, str):
                            existing_rule_id = uuid.UUID(raw_rid)
                    except Exception:
                        existing_rule_id = None

                    return EventIngestResponse(
                        event_id=event_in.event_id,
                        status="duplicate_ignored",
                        event_type=db_event_type.value,
                        broadcast=False,
                        persisted=True,
                        rule_id=existing_rule_id,
                        matched_rules_count=0,
                        should_notify=False,
                    )

                persisted = True
                logger.info(f"Persisted event {event_in.event_id} [{db_event_type.value}] for factory {factory_id}")

                # 4b. Deterministic Safety Rule Evaluation on newly persisted event
                persisted_event = db.get(Event, event_in.event_id)
                if persisted_event is not None:
                    try:
                        eval_res = RuleEvaluationService.evaluate_event(
                            db=db,
                            factory_id=factory_id,
                            event=persisted_event,
                        )
                        matched_count = len(eval_res.matched_rule_ids)
                        should_notify = any(m.notify for m in eval_res.matches)
                        primary_rule_id = persisted_event.rule_id

                        details_payload["rule_evaluation"] = {
                            "status": eval_res.evaluation_status,
                            "evaluated_count": len(eval_res.evaluated_rule_ids),
                            "matched_count": matched_count,
                            "matched_rule_ids": [str(rid) for rid in eval_res.matched_rule_ids],
                            "highest_severity": eval_res.matched_highest_severity.value if eval_res.matched_highest_severity else None,
                            "should_notify": should_notify,
                            "primary_rule_id": str(primary_rule_id) if primary_rule_id else None,
                            "incident_id": str(persisted_event.incident_id) if persisted_event.incident_id else None,
                        }
                        persisted_event.details = dict(details_payload)
                        db.commit()
                    except Exception as eval_err:
                        logger.warning(f"Non-fatal error during rule evaluation for {event_in.event_id}: {eval_err}")
            except (OperationalError, InterfaceError) as db_conn_err:
                db.rollback()
                logger.warning(
                    f"PostgreSQL connection offline or unavailable during event persistence ({db_conn_err.__class__.__name__}). "
                    f"Proceeding with real-time broadcast."
                )
                persisted = False
            except SQLAlchemyError as exc:
                db.rollback()
                logger.error(f"Database error during event persistence for {event_in.event_id}: {exc}")
                raise

        # 5. Broadcast to factory-specific WebSocket room in real time
        broadcast_sent = False
        if broadcast:
            ws_packet = {
                "type": "safety_event",
                "factory_id": str(factory_id),
                "data": {
                    "event_id": str(event_in.event_id),
                    "event_type": db_event_type.value,
                    "event_state": event_in.event_state,
                    "module": event_in.module,
                    "camera_id": str(camera_uuid) if camera_uuid else event_in.camera_id,
                    "timestamp": event_in.timestamp.isoformat(),
                    "confidence": event_in.confidence,
                    "track_id": event_in.track_id,
                    "bbox_normalized": [bbox_x, bbox_y, bbox_w, bbox_h] if bbox_x is not None else None,
                    "rule_id": str(primary_rule_id) if primary_rule_id else None,
                    "incident_id": str(persisted_event.incident_id) if (persisted_event and persisted_event.incident_id) else None,
                    "should_notify": should_notify,
                    "details": details_payload,
                },
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
            client_count = await ws_manager.broadcast_to_factory(factory_id, ws_packet)
            broadcast_sent = client_count > 0

        return EventIngestResponse(
            event_id=event_in.event_id,
            status="ingested",
            event_type=db_event_type.value,
            broadcast=broadcast_sent,
            persisted=persisted,
            rule_id=primary_rule_id,
            matched_rules_count=matched_count,
            should_notify=should_notify,
        )

    @staticmethod
    async def ingest_batch(
        frame_result: CVFrameResultIngest,
        factory_id: uuid.UUID,
        db: Optional[Session] = None,
    ) -> EventBatchIngestResponse:
        """
        Process a batch of events originating from a single video frame.
        """
        results: List[EventIngestResponse] = []
        ingested_count = 0
        duplicates_count = 0

        for cv_event in frame_result.events:
            # Propagate frame dimensions from FrameResult if missing on event
            if not cv_event.frame_size:
                cv_event.frame_size = frame_result.frame_size
            if cv_event.frame_index is None:
                cv_event.frame_index = frame_result.frame_index

            res = await EventService.ingest_event(
                event_in=cv_event,
                factory_id=factory_id,
                db=db,
                broadcast=True,
            )
            results.append(res)
            if res.status == "ingested":
                ingested_count += 1
            elif res.status == "duplicate_ignored":
                duplicates_count += 1

        return EventBatchIngestResponse(
            total_received=len(frame_result.events),
            ingested_count=ingested_count,
            duplicates_count=duplicates_count,
            events=results,
        )
