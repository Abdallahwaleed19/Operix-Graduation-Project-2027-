"""
app/core/errors.py
Standardized exception hierarchy and global FastAPI error handlers.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import logger


class OperixException(Exception):
    """Base application exception for Operix."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or []


class ResourceNotFoundException(OperixException):
    """Entity not found in database."""

    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            message=f"{resource} with id '{identifier}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
        )


class TenantAccessDeniedException(OperixException):
    """Operation violates tenant boundary or permission."""

    def __init__(self, message: str = "Access denied for current tenant context.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="TENANT_ACCESS_DENIED",
        )


def register_error_handlers(app: FastAPI) -> None:
    """Register uniform JSON error handlers on the FastAPI application."""

    @app.exception_handler(OperixException)
    async def operix_exception_handler(_: Request, exc: OperixException) -> JSONResponse:
        logger.warning(f"OperixException [{exc.error_code}]: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error.get("loc", []))
            details.append({"field": field, "issue": error.get("msg", "Invalid value")})

        logger.info(f"Validation error: {details}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "error_code": "VALIDATION_ERROR",
                "message": "Input validation failed.",
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error_code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled server error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "details": [{"issue": str(exc)}] if app.debug else [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
