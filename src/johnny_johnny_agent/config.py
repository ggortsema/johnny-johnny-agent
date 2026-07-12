"""Runtime configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Auth0Settings:
    """Server-owned Auth0 resource-server validation settings."""

    domain: str
    audience: str
    issuer: str
    jwks_url: str
    clock_skew_seconds: int = 30
    jwks_timeout_seconds: float = 5.0
    jwks_cache_seconds: float = 300.0


@dataclass(frozen=True)
class OpenAISettings:
    """Server-owned OpenAI provider settings and allowed model catalog."""

    api_key: str = field(repr=False)
    model: str
    models: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        default_model = self.model.strip()
        if not default_model:
            raise ValueError("OpenAI default model must not be blank.")

        normalized_models: list[str] = [default_model]
        seen = {default_model}
        for candidate in self.models:
            normalized = candidate.strip()
            if normalized and normalized not in seen:
                normalized_models.append(normalized)
                seen.add(normalized)

        object.__setattr__(self, "model", default_model)
        object.__setattr__(self, "models", tuple(normalized_models))


def resolve_database_url(explicit_database_url: str | None = None) -> str:
    """Resolve PostgreSQL connectivity without coupling to its network path."""
    database_url = explicit_database_url or os.environ.get("DATABASE_URL")
    if not database_url or not database_url.strip():
        raise RuntimeError(
            "DATABASE_URL is required. Set it in the environment or pass "
            "--database-url."
        )
    return database_url.strip()


def resolve_auth0_settings() -> Auth0Settings:
    """Resolve and validate the Auth0 issuer configuration for the API."""
    raw_domain = _required_environment_value("AUTH0_DOMAIN")
    audience = _required_environment_value("AUTH0_AUDIENCE")
    domain = _normalize_auth0_domain(raw_domain)
    issuer = f"https://{domain}/"

    return Auth0Settings(
        domain=domain,
        audience=audience,
        issuer=issuer,
        jwks_url=f"{issuer}.well-known/jwks.json",
        clock_skew_seconds=_non_negative_int_environment_value(
            "AUTH0_CLOCK_SKEW_SECONDS",
            default=30,
        ),
        jwks_timeout_seconds=_positive_float_environment_value(
            "AUTH0_JWKS_TIMEOUT_SECONDS",
            default=5.0,
        ),
        jwks_cache_seconds=_positive_float_environment_value(
            "AUTH0_JWKS_CACHE_SECONDS",
            default=300.0,
        ),
    )


def resolve_openai_settings() -> OpenAISettings:
    """Resolve the OpenAI credential and server-allowed model catalog."""
    configured_models = tuple(
        candidate.strip()
        for candidate in os.environ.get("OPENAI_MODELS", "").split(",")
        if candidate.strip()
    )
    return OpenAISettings(
        api_key=_required_environment_value("OPENAI_API_KEY"),
        model=_required_environment_value("OPENAI_MODEL"),
        models=configured_models,
    )


def resolve_api_docs_enabled() -> bool:
    """Resolve whether Swagger UI, ReDoc, and the OpenAPI document are served."""
    raw = os.environ.get("JOHNNY_JOHNNY_API_DOCS_ENABLED", "true")
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError("JOHNNY_JOHNNY_API_DOCS_ENABLED must be true or false.")


def _required_environment_value(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} is required to start the REST API.")
    return value.strip()


def _normalize_auth0_domain(raw_domain: str) -> str:
    candidate = raw_domain.strip().rstrip("/")
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError(
            "AUTH0_DOMAIN must be an Auth0 HTTPS domain such as tenant.us.auth0.com."
        )
    if parsed.username or parsed.password or parsed.port:
        raise RuntimeError("AUTH0_DOMAIN must not include credentials or a port.")
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise RuntimeError("AUTH0_DOMAIN must not include a path, query, or fragment.")
    return parsed.hostname.lower()


def _non_negative_int_environment_value(name: str, *, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if value < 0:
        raise RuntimeError(f"{name} must be zero or greater.")
    return value


def _positive_float_environment_value(name: str, *, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero.")
    return value
