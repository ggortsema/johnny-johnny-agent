"""Johnny-Johnny FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from johnny_johnny_agent.api.errors import install_exception_handlers
from johnny_johnny_agent.api.routes import PROJECT_VERSION, router
from johnny_johnny_agent.api.security import (
    AccessTokenVerifier,
    Auth0AccessTokenVerifier,
)
from johnny_johnny_agent.config import (
    resolve_api_docs_enabled,
    resolve_auth0_settings,
)


def create_app(
    *,
    access_token_verifier: AccessTokenVerifier | None = None,
    api_docs_enabled: bool | None = None,
) -> FastAPI:
    """Create a fail-closed API application with a replaceable token boundary."""
    verifier = (
        Auth0AccessTokenVerifier(resolve_auth0_settings())
        if access_token_verifier is None
        else access_token_verifier
    )
    docs_enabled = (
        resolve_api_docs_enabled() if api_docs_enabled is None else api_docs_enabled
    )

    application = FastAPI(
        title="Johnny-Johnny Agent",
        version=PROJECT_VERSION,
        description=(
            "Auth0-secured REST adapter over the same PostgreSQL-backed "
            "application workflows used by the Johnny-Johnny CLI."
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    application.state.access_token_verifier = verifier
    install_exception_handlers(application)
    application.include_router(router)
    return application
