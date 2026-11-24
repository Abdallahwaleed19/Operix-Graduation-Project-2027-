"""
app/api/v1/endpoints/assistant.py
REST API endpoints for LLM RAG Safety Assistant and Agentic Remediation Actions.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
import uuid
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ....core.errors import TenantAccessDeniedException
from ....schemas.common import APIResponse, APIResponseMeta
from ....services.ai_action_service import AIActionService, get_ai_action_service
from ...ai_deps import get_llm_assistant_service_dep
from ...deps import AuthenticatedUser, get_current_factory_id, get_current_user_context, get_tenant_db

router = APIRouter(prefix="/assistant", tags=["LLM RAG Assistant"])


# ---------------------------------------------------------------------------
# Schemas (mirrors and extends llm_rag_assistant contracts)
# ---------------------------------------------------------------------------

class UserContextDTO(BaseModel):
    user_id: Optional[UUID] = None
    full_name: Optional[str] = None
    role_code: Optional[str] = None
    factory_id: Optional[UUID] = None


class AssistantQueryIn(BaseModel):
    question: str = Field(min_length=2, max_length=1000, description="User query in Arabic or English")
    conversation_id: Optional[str] = Field(default=None, description="Optional conversation tracking ID")
    language_preference: Literal["auto", "ar", "en"] = Field(default="auto")
    user_context: Optional[UserContextDTO] = None


class ActionExecutionIn(BaseModel):
    action_id: str = Field(..., description="Unique proposal ID")
    action_type: str = Field(..., description="Action type (create_incident, acknowledge_incident, alert, mute_sensor, etc.)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    confirmed_by: Optional[str] = Field(default=None, description="Username or ID confirming action")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key to prevent double execution")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/ask",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Ask Safety Assistant",
    description="Query the RAG assistant with grounded safety knowledge retrieval in Arabic or English.",
)
def ask_assistant(
    query_in: AssistantQueryIn,
    user: AuthenticatedUser = Depends(get_current_user_context),
    assistant_svc: Any = Depends(get_llm_assistant_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Grounded RAG question answering."""
    # Enforce factory tenant isolation in user context
    from llm_rag_assistant.schemas.contracts import AssistantQueryRequest, UserContext
    req = AssistantQueryRequest(
        question=query_in.question,
        conversation_id=query_in.conversation_id,
        language_preference=query_in.language_preference,
        user_context=UserContext(
            user_id=user.user_id,
            full_name=user.full_name or "Operix User",
            role_code=user.role,
            factory_id=user.factory_id,
        ),
    )
    result = assistant_svc.ask(req)
    res_dict = result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)
    return APIResponse(
        status="success",
        data=res_dict,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.post(
    "/actions/execute",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Execute Agentic Remediation Action",
    description="Execute an authorized remediation action against real canonical models with WebSocket broadcasting.",
)
async def execute_action(
    action_in: ActionExecutionIn,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    action_svc: AIActionService = Depends(get_ai_action_service),
) -> APIResponse[Dict[str, Any]]:
    """Execute action through canonical backend services with post-commit WebSocket broadcasting."""
    res = await action_svc.execute_action(
        db=db,
        factory_id=user.factory_id,
        user_id=user.user_id,
        user_role=user.role,
        action_id=action_in.action_id,
        action_type=action_in.action_type,
        parameters=action_in.parameters,
        idempotency_key=action_in.idempotency_key,
        confirmed_by=action_in.confirmed_by or user.full_name,
        broadcast=True,
        defer_broadcast=True,
        raise_on_error=True,
    )

    # Schedule WebSocket broadcasting strictly post-commit via FastAPI BackgroundTasks
    pending_events = res.pop("_pending_broadcasts", [])
    if pending_events:
        background_tasks.add_task(action_svc.broadcast_pending_events, pending_events)

    return APIResponse(
        status="success",
        data=res,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/sources",
    response_model=APIResponse[List[Dict[str, Any]]],
    status_code=status.HTTP_200_OK,
    summary="Retrieve Source Citations",
    description="Retrieve matching knowledge citations directly without running LLM text generation.",
)
def get_sources(
    q: str = Query(..., min_length=2, description="Search term or topic"),
    user: AuthenticatedUser = Depends(get_current_user_context),
    assistant_svc: Any = Depends(get_llm_assistant_service_dep),
) -> APIResponse[List[Dict[str, Any]]]:
    """Fetch relevant citations for a given topic."""
    citations = assistant_svc.get_sources(query=q, factory_id=user.factory_id)
    serialized = [c.model_dump(mode="json") if hasattr(c, "model_dump") else dict(c) for c in citations]
    return APIResponse(
        status="success",
        data=serialized,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.delete(
    "/conversations/{conversation_id}",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Clear Conversation History",
    description="Clear saved dialogue turns for a specified session.",
)
def clear_conversation(
    conversation_id: str,
    user: AuthenticatedUser = Depends(get_current_user_context),
    assistant_svc: Any = Depends(get_llm_assistant_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Clear conversation history."""
    try:
        cleared = assistant_svc.clear_conversation(
            conversation_id,
            factory_id=user.factory_id,
            user_id=user.user_id,
        )
    except PermissionError as exc:
        raise TenantAccessDeniedException(str(exc)) from exc
    return APIResponse(
        status="success",
        data={"conversation_id": conversation_id, "cleared": cleared},
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/health",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="AI Assistant Health",
    description="Diagnostic health check for the RAG retriever and LLM provider.",
)
def assistant_health(
    user: AuthenticatedUser = Depends(get_current_user_context),
    assistant_svc: Any = Depends(get_llm_assistant_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Diagnostic health check."""
    status_data = assistant_svc.check_health()
    return APIResponse(
        status="success",
        data=status_data,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )
