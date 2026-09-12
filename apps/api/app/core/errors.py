"""Centralized error classes and exception response handlers."""
import uuid
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: Any = None):
        msg = f"{resource} not found" if identifier is None else f"{resource} with id '{identifier}' not found"
        super().__init__(message=msg, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message=message, code="UNAUTHORIZED", status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message=message, code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN)


class ConflictError(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, code="CONFLICT", status_code=status.HTTP_409_CONFLICT)


class ValidationError(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)


class NoProviderConfiguredError(AppException):
    def __init__(self, message: str = "No AI provider configured. Configure at least one AI provider to start generating content."):
        super().__init__(message=message, code="AI_PROVIDER_REQUIRED", status_code=status.HTTP_400_BAD_REQUEST)


class ProviderUnavailableError(AppException):
    def __init__(self, provider_name: str, message: Optional[str] = None):
        msg = message or f"The configured AI provider '{provider_name}' is temporarily unavailable."
        super().__init__(message=msg, code="AI_PROVIDER_UNAVAILABLE", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class RateLimitExceededError(AppException):
    def __init__(self, message: str = "Rate limit exceeded. Please wait before retrying."):
        super().__init__(message=message, code="RATE_LIMIT_EXCEEDED", status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class BudgetExceededError(AppException):
    def __init__(self, message: str = "AI budget limit exceeded for this operation."):
        super().__init__(message=message, code="BUDGET_EXCEEDED", status_code=status.HTTP_400_BAD_REQUEST)


class SSRFViolationError(AppException):
    def __init__(self, message: str = "Requested URL points to an internal or disallowed destination."):
        super().__init__(message=message, code="SSRF_BLOCKED", status_code=status.HTTP_400_BAD_REQUEST)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Format domain exceptions to standard structured JSON response."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
                "details": exc.details,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors without exposing stack traces or internals."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please contact support if the issue persists.",
                "request_id": request_id,
            }
        },
    )
