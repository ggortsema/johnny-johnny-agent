"""Consistent HTTP error mapping for authentication and application failures."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from yaml import YAMLError

from johnny_johnny_agent.api.models import ErrorDetail, ErrorResponse
from johnny_johnny_agent.api.security import (
    AuthenticationRequiredError,
    AuthenticationServiceUnavailableError,
    InsufficientScopeError,
    InvalidAccessTokenError,
)
from johnny_johnny_agent.capabilities.backlog_persistence.postgres import (
    BacklogPersistenceError,
    ProviderProjectNotFoundError,
    RoundTripValidationError,
)
from johnny_johnny_agent.capabilities.backlog_persistence.workflow import (
    TargetedBacklogMutationCompensationError,
    TargetedBacklogMutationConsistencyError,
)


class BacklogDocumentError(RuntimeError):
    """Raised when an imported backlog document cannot be parsed or validated."""


class ApiRequestError(RuntimeError):
    """Raised for cross-field request constraints not represented by one field."""


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _request_validation_error)
    app.add_exception_handler(AuthenticationRequiredError, _authentication_required)
    app.add_exception_handler(InvalidAccessTokenError, _invalid_access_token)
    app.add_exception_handler(InsufficientScopeError, _insufficient_scope)
    app.add_exception_handler(
        AuthenticationServiceUnavailableError,
        _authentication_service_unavailable,
    )
    app.add_exception_handler(BacklogDocumentError, _backlog_document_error)
    app.add_exception_handler(ApiRequestError, _api_request_error)
    app.add_exception_handler(ProviderProjectNotFoundError, _provider_project_not_found)
    app.add_exception_handler(
        TargetedBacklogMutationConsistencyError,
        _consistency_error,
    )
    app.add_exception_handler(
        TargetedBacklogMutationCompensationError,
        _consistency_error,
    )
    app.add_exception_handler(RoundTripValidationError, _round_trip_error)
    app.add_exception_handler(BacklogPersistenceError, _persistence_error)
    app.add_exception_handler(YAMLError, _yaml_error)
    app.add_exception_handler(KeyError, _document_key_error)
    app.add_exception_handler(RuntimeError, _runtime_error)
    app.add_exception_handler(Exception, _unexpected_error)


async def _request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _response(
        status_code=422,
        code="request_validation_error",
        message="The request did not satisfy the API contract.",
        details=jsonable_encoder(exc.errors()),
    )


async def _authentication_required(
    request: Request,
    exc: AuthenticationRequiredError,
) -> JSONResponse:
    return _response(
        401,
        "authentication_required",
        str(exc),
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _invalid_access_token(
    request: Request,
    exc: InvalidAccessTokenError,
) -> JSONResponse:
    return _response(
        401,
        "invalid_access_token",
        str(exc),
        headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
    )


async def _insufficient_scope(
    request: Request,
    exc: InsufficientScopeError,
) -> JSONResponse:
    required = sorted(exc.required_scopes)
    challenge = 'Bearer error="insufficient_scope", scope="' + " ".join(required) + '"'
    return _response(
        403,
        "insufficient_scope",
        str(exc),
        details={"required_scopes": required},
        headers={"WWW-Authenticate": challenge},
    )


async def _authentication_service_unavailable(
    request: Request,
    exc: AuthenticationServiceUnavailableError,
) -> JSONResponse:
    return _response(
        503,
        "authentication_service_unavailable",
        str(exc),
    )


async def _backlog_document_error(
    request: Request,
    exc: BacklogDocumentError,
) -> JSONResponse:
    return _response(422, "backlog_document_invalid", str(exc))


async def _api_request_error(
    request: Request,
    exc: ApiRequestError,
) -> JSONResponse:
    return _response(400, "invalid_request", str(exc))


async def _provider_project_not_found(
    request: Request,
    exc: ProviderProjectNotFoundError,
) -> JSONResponse:
    return _response(404, "provider_project_not_found", str(exc))


async def _consistency_error(
    request: Request,
    exc: RuntimeError,
) -> JSONResponse:
    return _response(409, "cross_boundary_consistency_error", str(exc))


async def _round_trip_error(
    request: Request,
    exc: RoundTripValidationError,
) -> JSONResponse:
    return _response(409, "round_trip_validation_error", str(exc))


async def _persistence_error(
    request: Request,
    exc: BacklogPersistenceError,
) -> JSONResponse:
    return _response(503, "persistence_unavailable", str(exc))


async def _yaml_error(request: Request, exc: YAMLError) -> JSONResponse:
    return _response(422, "backlog_document_invalid", f"Invalid YAML: {exc}")


async def _document_key_error(request: Request, exc: KeyError) -> JSONResponse:
    missing = str(exc).strip("'")
    return _response(
        422,
        "backlog_document_invalid",
        f"Backlog document is missing required field: {missing}",
    )


async def _runtime_error(request: Request, exc: RuntimeError) -> JSONResponse:
    message = str(exc)
    normalized = message.lower()

    if "not found" in normalized:
        return _response(404, "resource_not_found", message)

    if "currently supports provider" in normalized:
        return _response(422, "unsupported_provider", message)

    conflict_markers = (
        "already exists",
        "different title",
        "different repository",
        "different description",
        "different acceptance criteria",
        "conflict",
    )
    if any(marker in normalized for marker in conflict_markers):
        return _response(409, "resource_conflict", message)

    provider_markers = (
        "github",
        "projectv2",
        "graphql",
        "rate limit",
        "missing github_token",
    )
    if any(marker in normalized for marker in provider_markers):
        return _response(502, "provider_operation_failed", message)

    return _response(422, "domain_validation_error", message)


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return _response(
        500,
        "internal_server_error",
        "The server could not complete the request.",
    )


def _response(
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        headers=headers,
    )
