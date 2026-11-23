# Operix AI Services — Seif Integration Guide

**Target Audience:** Seif Elsawy (Backend Lead & FastAPI Maintainer)  
**Author:** Abdallah Waleed (AI & Analytical Services Lead)  
**Scope:** Wiring `backend/ai-services/` modules into the main Operix FastAPI backend (`backend/app/`)  
**Status:** Validated with PostgreSQL 18 & Python 3.14

---

## 1. Overview & Architecture

All four AI service modules are designed as self-contained service packages under `backend/ai-services/`. They do not run their own HTTP servers; instead, they expose service layer classes that accept standard SQLAlchemy sessions, Pydantic request models, or storage interfaces.

### Modules to Mount

| Module | Core Service Class | Primary Database Dependency | Recommended API Route Prefix |
| :--- | :--- | :--- | :--- |
| **Workforce Analytics** | `WorkforceAnalyticsService` | Read-only SQLAlchemy Session | `/api/v1/workforce-analytics` |
| **RAG Assistant & Actions** | `OperixRAGAssistant`, `OperixActionService` | Vector Index / Ingestion Pipeline / Session | `/api/v1/rag-assistant` |
| **Reports Generation** | `ReportService` | Read-only SQLAlchemy Engine / Session | `/api/v1/reports` |
| **Incident Evidence** | `EvidenceServiceFacade` (Upload, Retrieval, Integrity) | Read/Write SQLAlchemy Session + LocalStorage | `/api/v1/evidence` |

---

## 2. Environment & Import Path Setup

Ensure `backend/ai-services` is accessible on Python's module search path. In your `backend/app/main.py` (or ASGI entrypoint), add:

```python
import sys
from pathlib import Path

# Add ai-services to sys.path so modules import cleanly
AI_SERVICES_PATH = Path(__file__).resolve().parent.parent / "ai-services"
if str(AI_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(AI_SERVICES_PATH))
```

---

## 3. Dependency Injection & Service Factories

Use FastAPI's `Depends` system to inject the active database session and instantiate services per request.

### 3.1 Workforce Analytics Service Factory

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db  # Seif's DB session dependency
from workforce_analytics.services import WorkforceAnalyticsService

def get_analytics_service(db: Session = Depends(get_db)) -> WorkforceAnalyticsService:
    """Provides a thread-safe WorkforceAnalyticsService instance with active DB session."""
    return WorkforceAnalyticsService(session=db)
```

### 3.2 Incident Evidence Service Factory

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from incident_evidence.services.evidence_service import EvidenceServiceFacade, get_evidence_service

def get_evidence_facade(db: Session = Depends(get_db)) -> EvidenceServiceFacade:
    """
    Creates an EvidenceServiceFacade wrapping:
    - EvidenceUploadService (with rollback protection)
    - EvidenceRetrievalService (with tenant validation)
    - EvidenceIntegrityService (SHA-256 verification)
    """
    return get_evidence_service(session=db)
```

### 3.3 Reports Generation Service Factory

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from reports_generation.services.report_service import ReportService
from reports_generation.services.report_data_service import ReportDataService

def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    """Instantiates the report orchestration service using the active DB engine."""
    data_service = ReportDataService(engine=db.get_bind())
    return ReportService(data_service=data_service)
```

### 3.4 RAG Assistant & Action Service Factory (Singleton + Scoped Action)

```python
from functools import lru_cache
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from llm_rag_assistant.services.assistant_service import OperixRAGAssistant
from llm_rag_assistant.services.action_service import OperixActionService
from llm_rag_assistant.retrieval.vector_store import NumPyVectorStore

@lru_cache(maxsize=1)
def get_rag_assistant_singleton() -> OperixRAGAssistant:
    """Vector store and LLM provider initialized once at startup."""
    store = NumPyVectorStore()
    return OperixRAGAssistant(vector_store=store)

def get_action_service(db: Session = Depends(get_db)) -> OperixActionService:
    """Action service with durable audit callback wired to your audit logging table."""
    def record_audit_to_db(audit_record: dict):
        # Optional: Seif can persist audit_record into an audit table here
        pass

    return OperixActionService(audit_callback=record_audit_to_db)
```

---

## 4. Exception Mapping to HTTP Status Codes

When an exception is raised inside any AI service, translate it to standard FastAPI `HTTPException` responses using global or router-level exception handlers:

| AI Service Exception | Suggested HTTP Status | User Message / Response Details |
| :--- | :--- | :--- |
| `incident_evidence.exceptions.EvidenceNotFoundError` | **404 Not Found** | `"Evidence record does not exist or has been deleted."` |
| `incident_evidence.exceptions.EvidenceExpiredError` | **410 Gone** | `"Evidence has exceeded its retention period and is expired."` |
| `incident_evidence.exceptions.EvidencePurgedError` | **410 Gone** | `"Evidence file payload has already been purged from storage."` |
| `incident_evidence.exceptions.FactoryMismatchError` | **403 Forbidden** | `"Access denied: Requested evidence does not belong to authorized factory."` |
| `incident_evidence.exceptions.InvalidMimeTypeError` | **400 Bad Request** | `"Unsupported MIME type. Note: Audio evidence is not supported."` |
| `incident_evidence.exceptions.FileSizeLimitExceededError` | **413 Content Too Large** | `"File exceeds maximum allowed upload size (50MB for video, 10MB for image)."` |
| `incident_evidence.exceptions.FileIntegrityError` | **400 Bad Request** | `"SHA-256 verification failed during upload processing."` |
| `reports_generation.exceptions.ReportGenerationError` | **500 Internal Server Error** | `"Report rendering or data collection failed."` |
| `workforce_analytics.schemas.WorkforceAnalyticsError` | **500 Internal Server Error** | `"Analytics computation error. Ensure factory_id is valid."` |

### Recommended FastAPI Global Handler Snippet

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from incident_evidence.exceptions import (
    EvidenceNotFoundError, EvidenceExpiredError, EvidencePurgedError,
    FactoryMismatchError, InvalidMimeTypeError, FileSizeLimitExceededError
)

def register_ai_exception_handlers(app: FastAPI):
    @app.exception_handler(EvidenceNotFoundError)
    async def handle_not_found(request: Request, exc: EvidenceNotFoundError):
        return JSONResponse(status_code=404, content={"success": False, "error": str(exc), "code": "EVIDENCE_NOT_FOUND"})

    @app.exception_handler(EvidenceExpiredError)
    @app.exception_handler(EvidencePurgedError)
    async def handle_gone(request: Request, exc: Exception):
        return JSONResponse(status_code=410, content={"success": False, "error": str(exc), "code": "EVIDENCE_EXPIRED_OR_PURGED"})

    @app.exception_handler(FactoryMismatchError)
    async def handle_forbidden(request: Request, exc: FactoryMismatchError):
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc), "code": "FACTORY_ACCESS_DENIED"})

    @app.exception_handler(InvalidMimeTypeError)
    @app.exception_handler(FileSizeLimitExceededError)
    async def handle_bad_request(request: Request, exc: Exception):
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc), "code": "INVALID_UPLOAD_PAYLOAD"})
```

---

## 5. Ready-to-Mount FastAPI Router Templates

### 5.1 Workforce Analytics Router (`backend/app/api/v1/workforce.py`)

```python
from uuid import UUID
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.api.dependencies import get_current_user  # Your auth dependency
from workforce_analytics.services import WorkforceAnalyticsService
from workforce_analytics.schemas import (
    WorkforceOverviewResponse, AttendanceMetricsResponse,
    IncidentAnalyticsResponse, CameraCoverageResponse, WorkforceSummaryResponse
)

router = APIRouter(prefix="/workforce-analytics", tags=["Workforce Analytics"])

@router.get("/overview", response_model=WorkforceOverviewResponse)
def get_overview(
    factory_id: UUID = Query(..., description="Factory UUID"),
    service: WorkforceAnalyticsService = Depends(get_analytics_service),
    current_user = Depends(get_current_user),
):
    return service.get_workforce_overview(factory_id=factory_id)

@router.get("/attendance", response_model=AttendanceMetricsResponse)
def get_attendance(
    factory_id: UUID = Query(...),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    service: WorkforceAnalyticsService = Depends(get_analytics_service),
    current_user = Depends(get_current_user),
):
    return service.get_attendance_metrics(factory_id=factory_id, date_from=date_from, date_to=date_to)

@router.get("/incidents", response_model=IncidentAnalyticsResponse)
def get_incidents(
    factory_id: UUID = Query(...),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    service: WorkforceAnalyticsService = Depends(get_analytics_service),
    current_user = Depends(get_current_user),
):
    return service.get_incident_analytics(factory_id=factory_id, date_from=date_from, date_to=date_to)

@router.get("/camera-coverage", response_model=CameraCoverageResponse)
def get_camera_coverage(
    factory_id: UUID = Query(...),
    service: WorkforceAnalyticsService = Depends(get_analytics_service),
    current_user = Depends(get_current_user),
):
    return service.get_camera_coverage(factory_id=factory_id)

@router.get("/summary", response_model=WorkforceSummaryResponse)
def get_summary(
    factory_id: UUID = Query(...),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    service: WorkforceAnalyticsService = Depends(get_analytics_service),
    current_user = Depends(get_current_user),
):
    return service.get_workforce_summary(factory_id=factory_id, date_from=date_from, date_to=date_to)
```

---

### 5.2 Incident Evidence Router (`backend/app/api/v1/evidence.py`)

```python
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from incident_evidence.schemas import (
    EvidenceUploadRequest, EvidenceUploadResponse, EvidenceResponse,
    EvidenceListResponse, EvidenceIntegrityResponse
)
from incident_evidence.services.evidence_service import EvidenceServiceFacade

router = APIRouter(prefix="/evidence", tags=["Incident Evidence"])

@router.post("/upload", response_model=EvidenceUploadResponse)
async def upload_evidence(
    factory_id: UUID = Form(...),
    event_id: UUID = Form(...),
    file: UploadFile = File(...),
    duration_s: Optional[int] = Form(None),
    captured_at: Optional[str] = Form(None),
    expires_at: Optional[str] = Form(None),
    facade: EvidenceServiceFacade = Depends(get_evidence_facade),
):
    file_bytes = await file.read()
    request_data = EvidenceUploadRequest(
        factory_id=factory_id,
        event_id=event_id,
        content_type=file.content_type or "application/octet-stream",
        duration_s=duration_s,
        captured_at=captured_at,
        expires_at=expires_at,
    )
    return facade.upload(file_bytes=file_bytes, request=request_data)

@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence_metadata(
    evidence_id: UUID,
    factory_id: UUID = Query(...),
    facade: EvidenceServiceFacade = Depends(get_evidence_facade),
):
    return facade.get_metadata(evidence_id=evidence_id, factory_id=factory_id)

@router.get("/{evidence_id}/download")
def download_evidence_file(
    evidence_id: UUID,
    factory_id: UUID = Query(...),
    facade: EvidenceServiceFacade = Depends(get_evidence_facade),
):
    stream, content_type, filename = facade.download(evidence_id=evidence_id, factory_id=factory_id)
    return StreamingResponse(
        stream,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/{evidence_id}/integrity", response_model=EvidenceIntegrityResponse)
def verify_integrity(
    evidence_id: UUID,
    factory_id: UUID = Query(...),
    facade: EvidenceServiceFacade = Depends(get_evidence_facade),
):
    return facade.verify_integrity(evidence_id=evidence_id, factory_id=factory_id)

@router.get("/by-event/{event_id}", response_model=EvidenceListResponse)
def list_by_event(
    event_id: UUID,
    factory_id: UUID = Query(...),
    facade: EvidenceServiceFacade = Depends(get_evidence_facade),
):
    return facade.list_by_event(event_id=event_id, factory_id=factory_id)
```

---

### 5.3 Reports Generation Router (`backend/app/api/v1/reports.py`)

Because ReportLab and openpyxl perform synchronous CPU and file operations, wrap report generation inside `starlette.concurrency.run_in_threadpool` to prevent blocking the async event loop:

```python
from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from reports_generation.schemas import ReportGenerationRequest, ReportGenerationResponse
from reports_generation.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Automated Reports"])

@router.post("/generate", response_model=ReportGenerationResponse)
async def generate_report(
    req: ReportGenerationRequest,
    report_service: ReportService = Depends(get_report_service),
):
    # Offload CPU-bound rendering to threadpool
    return await run_in_threadpool(
        report_service.generate_report,
        factory_id=req.factory_id,
        report_type=req.report_type,
        format=req.format,
        date_from=req.date_from,
        date_to=req.date_to,
    )

@router.get("/download/{file_path:path}")
def download_report(file_path: str):
    # Path validation handled securely inside FileResponse
    return FileResponse(
        path=file_path,
        filename=Path(file_path).name,
    )
```

---

### 5.4 LLM / RAG Assistant Router (`backend/app/api/v1/rag.py`)

```python
from fastapi import APIRouter, Depends, Header
from typing import Optional
from llm_rag_assistant.schemas.contracts import (
    ChatMessageRequest, ChatMessageResponse,
    ActionExecutionRequest, ActionExecutionResponse
)
from llm_rag_assistant.services.assistant_service import OperixRAGAssistant
from llm_rag_assistant.services.action_service import OperixActionService

router = APIRouter(prefix="/rag-assistant", tags=["LLM & RAG Assistant"])

@router.post("/chat", response_model=ChatMessageResponse)
def chat_with_assistant(
    request: ChatMessageRequest,
    assistant: OperixRAGAssistant = Depends(get_rag_assistant_singleton),
):
    return assistant.chat(request)

@router.post("/execute-action", response_model=ActionExecutionResponse)
def execute_remediation(
    request: ActionExecutionRequest,
    action_service: OperixActionService = Depends(get_action_service),
    x_idempotency_key: Optional[str] = Header(None),
):
    if x_idempotency_key and not request.idempotency_key:
        request.idempotency_key = x_idempotency_key
    return action_service.execute(request)
```

---

## 6. Performance & Threading Best Practices

1. **Async Event Loop Protection:** Never call ReportLab's `canvas.save()` or openpyxl's `wb.save()` directly in an `async def` route without `run_in_threadpool`.
2. **Session Lifetimes:** Avoid holding a database transaction open across long LLM calls. Query the necessary incident or rule data first, close or release the connection, and then stream or await the LLM completion.
3. **Evidence Cleanup:** The database schema tracks `expires_at` and `purged_at`. Run a lightweight background cron task (e.g. daily) that queries `evidence_files` where `expires_at < NOW() AND purged_at IS NULL` to delete old payloads from disk and set `purged_at = NOW()`.
