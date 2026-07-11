"""Auth0 access-token validation and API authorization dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

import jwt
from fastapi import Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError as PyJwtInvalidTokenError,
    PyJWKClientConnectionError,
    PyJWKClientError,
)

from johnny_johnny_agent.config import Auth0Settings


class ApiPermission(StrEnum):
    """Auth0 API permissions enforced by the REST adapter."""

    READ_BACKLOGS = "read:backlogs"
    WRITE_BACKLOGS = "write:backlogs"
    OPERATE_BACKLOGS = "operate:backlogs"
    ADMIN_BACKLOGS = "admin:backlogs"
    INVOKE_ASSISTANT = "invoke:assistant"


ALL_API_PERMISSIONS = frozenset(permission.value for permission in ApiPermission)


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Validated access-token identity and granted OAuth scopes."""

    subject: str
    scopes: frozenset[str]
    claims: dict[str, Any]
    client_id: str | None = None


class AccessTokenVerifier(Protocol):
    """Boundary used by FastAPI and replaceable in behavior tests."""

    def verify(self, token: str) -> AuthenticatedPrincipal:
        """Validate one bearer token and return its authenticated principal."""


class AuthenticationRequiredError(RuntimeError):
    """Raised when a protected route receives no bearer token."""


class InvalidAccessTokenError(RuntimeError):
    """Raised when a bearer token cannot be trusted."""


class AuthenticationServiceUnavailableError(RuntimeError):
    """Raised when the configured issuer keys cannot be reached."""


class InsufficientScopeError(RuntimeError):
    """Raised when an authenticated token lacks a required API permission."""

    def __init__(
        self,
        *,
        required_scopes: frozenset[str],
        granted_scopes: frozenset[str],
    ) -> None:
        self.required_scopes = required_scopes
        self.granted_scopes = granted_scopes
        self.missing_scopes = required_scopes - granted_scopes
        super().__init__(
            "The access token does not grant the permission required for this operation."
        )


class Auth0AccessTokenVerifier:
    """Validate Auth0 RS256 access tokens against a configured JWKS endpoint."""

    def __init__(
        self,
        settings: Auth0Settings,
        *,
        jwks_client: PyJWKClient | None = None,
    ) -> None:
        self.settings = settings
        self._jwks_client = jwks_client or PyJWKClient(
            settings.jwks_url,
            cache_keys=True,
            cache_jwk_set=True,
            lifespan=settings.jwks_cache_seconds,
            timeout=settings.jwks_timeout_seconds,
        )

    def verify(self, token: str) -> AuthenticatedPrincipal:
        if not token or not token.strip():
            raise InvalidAccessTokenError("The bearer token is empty.")

        try:
            header = jwt.get_unverified_header(token)
            self._validate_header(header)
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key=signing_key.key,
                algorithms=["RS256"],
                audience=self.settings.audience,
                issuer=self.settings.issuer,
                leeway=self.settings.clock_skew_seconds,
                options={
                    "require": ["aud", "exp", "iat", "iss", "sub"],
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_nbf": True,
                },
            )
            return _principal_from_claims(claims)
        except PyJWKClientConnectionError as exc:
            raise AuthenticationServiceUnavailableError(
                "The identity provider signing keys are temporarily unavailable."
            ) from exc
        except (
            PyJWKClientError,
            PyJwtInvalidTokenError,
            TypeError,
            ValueError,
        ) as exc:
            raise InvalidAccessTokenError(
                "The bearer token is invalid or expired."
            ) from exc

    @staticmethod
    def _validate_header(header: dict[str, Any]) -> None:
        if header.get("alg") != "RS256":
            raise InvalidAccessTokenError(
                "The bearer token does not use the required RS256 algorithm."
            )
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid.strip():
            raise InvalidAccessTokenError(
                "The bearer token does not identify an issuer signing key."
            )
        if "jku" in header or "x5u" in header:
            raise InvalidAccessTokenError(
                "The bearer token contains an unsupported remote-key header."
            )
        if "crit" in header:
            raise InvalidAccessTokenError(
                "The bearer token contains unsupported critical headers."
            )


def _principal_from_claims(claims: dict[str, Any]) -> AuthenticatedPrincipal:
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise InvalidAccessTokenError(
            "The bearer token does not contain a valid subject."
        )

    scope_claim = claims.get("scope", "")
    if not isinstance(scope_claim, str):
        raise InvalidAccessTokenError("The bearer token scope claim is not a string.")
    scopes = frozenset(scope for scope in scope_claim.split() if scope)

    raw_client_id = claims.get("client_id")
    if not isinstance(raw_client_id, str):
        raw_client_id = claims.get("azp")
    client_id = (
        raw_client_id.strip()
        if isinstance(raw_client_id, str) and raw_client_id.strip()
        else None
    )

    return AuthenticatedPrincipal(
        subject=subject,
        scopes=scopes,
        claims=dict(claims),
        client_id=client_id,
    )


_bearer_scheme = HTTPBearer(
    auto_error=False,
    bearerFormat="JWT",
    description=(
        "Auth0 access token issued for the configured Johnny-Johnny API audience."
    ),
    scheme_name="Auth0Bearer",
)


def authenticated_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> AuthenticatedPrincipal:
    """Authenticate a request without assigning route permissions."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationRequiredError(
            "A bearer access token is required for this endpoint."
        )

    verifier = getattr(request.app.state, "access_token_verifier", None)
    if verifier is None:
        raise AuthenticationServiceUnavailableError(
            "Access-token validation is not configured."
        )
    return verifier.verify(credentials.credentials)


def require_scopes(*required: ApiPermission | str):
    """Create a FastAPI dependency requiring every declared OAuth scope."""
    required_scopes = frozenset(
        permission.value if isinstance(permission, ApiPermission) else permission
        for permission in required
    )
    if not required_scopes:
        raise ValueError("At least one required scope must be declared.")

    def dependency(
        principal: AuthenticatedPrincipal = Security(authenticated_principal),
    ) -> AuthenticatedPrincipal:
        if not required_scopes.issubset(principal.scopes):
            raise InsufficientScopeError(
                required_scopes=required_scopes,
                granted_scopes=principal.scopes,
            )
        return principal

    return dependency
