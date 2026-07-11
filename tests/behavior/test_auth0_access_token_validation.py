from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.exceptions import PyJWKClientConnectionError

from johnny_johnny_agent.api.app import create_app
from johnny_johnny_agent.api.security import (
    AuthenticationServiceUnavailableError,
    Auth0AccessTokenVerifier,
    InvalidAccessTokenError,
)
from johnny_johnny_agent.config import (
    Auth0Settings,
    resolve_api_docs_enabled,
    resolve_auth0_settings,
)


ISSUER = "https://johnny-johnny-test.us.auth0.com/"
AUDIENCE = "https://api.johnny-johnny.local"


class _StaticJwksClient:
    def __init__(self, public_key):
        self.public_key = public_key
        self.tokens = []

    def get_signing_key_from_jwt(self, token: str):
        self.tokens.append(token)
        return SimpleNamespace(key=self.public_key)


class _UnavailableJwksClient:
    def get_signing_key_from_jwt(self, token: str):
        raise PyJWKClientConnectionError("offline")


def _settings() -> Auth0Settings:
    return Auth0Settings(
        domain="johnny-johnny-test.us.auth0.com",
        audience=AUDIENCE,
        issuer=ISSUER,
        jwks_url=f"{ISSUER}.well-known/jwks.json",
        clock_skew_seconds=0,
        jwks_timeout_seconds=1,
        jwks_cache_seconds=60,
    )


def _claims(**overrides):
    now = datetime.now(UTC)
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "auth0|user-123",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "scope": "read:backlogs write:backlogs",
        "azp": "client-123",
    }
    claims.update(overrides)
    return claims


def _rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _token(private_key, *, claims=None, headers=None):
    return jwt.encode(
        claims if claims is not None else _claims(),
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key", **(headers or {})},
    )


def test_auth0_verifier_validates_rs256_claims_and_extracts_scopes():
    private_key = _rsa_key()
    jwks = _StaticJwksClient(private_key.public_key())
    verifier = Auth0AccessTokenVerifier(_settings(), jwks_client=jwks)
    token = _token(private_key)

    principal = verifier.verify(token)

    assert jwks.tokens == [token]
    assert principal.subject == "auth0|user-123"
    assert principal.client_id == "client-123"
    assert principal.scopes == frozenset({"read:backlogs", "write:backlogs"})
    assert principal.claims["aud"] == AUDIENCE


@pytest.mark.parametrize(
    "claims",
    [
        _claims(iss="https://other-tenant.auth0.com/"),
        _claims(aud="https://some-other-api"),
        _claims(exp=1),
        {key: value for key, value in _claims().items() if key != "sub"},
    ],
)
def test_auth0_verifier_rejects_invalid_issuer_audience_expiry_and_subject(claims):
    private_key = _rsa_key()
    verifier = Auth0AccessTokenVerifier(
        _settings(),
        jwks_client=_StaticJwksClient(private_key.public_key()),
    )

    with pytest.raises(InvalidAccessTokenError):
        verifier.verify(_token(private_key, claims=claims))


def test_auth0_verifier_rejects_a_token_signed_by_another_key():
    trusted_key = _rsa_key()
    attacker_key = _rsa_key()
    verifier = Auth0AccessTokenVerifier(
        _settings(),
        jwks_client=_StaticJwksClient(trusted_key.public_key()),
    )

    with pytest.raises(InvalidAccessTokenError):
        verifier.verify(_token(attacker_key))


def test_auth0_verifier_rejects_non_rs256_and_remote_key_headers():
    verifier = Auth0AccessTokenVerifier(
        _settings(),
        jwks_client=_StaticJwksClient(_rsa_key().public_key()),
    )
    hs_token = jwt.encode(
        _claims(),
        "not-a-production-secret-that-is-at-least-32-bytes",
        algorithm="HS256",
        headers={"kid": "test-key"},
    )
    remote_key_token = _token(
        _rsa_key(),
        headers={"jku": "https://attacker.test/jwks"},
    )
    critical_header_token = _token(_rsa_key(), headers={"crit": ["example"]})
    missing_kid_token = jwt.encode(
        _claims(),
        _rsa_key(),
        algorithm="RS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        verifier.verify(hs_token)
    with pytest.raises(InvalidAccessTokenError):
        verifier.verify(remote_key_token)
    with pytest.raises(InvalidAccessTokenError):
        verifier.verify(critical_header_token)
    with pytest.raises(InvalidAccessTokenError):
        verifier.verify(missing_kid_token)


def test_auth0_verifier_does_not_treat_permissions_claim_as_requested_scope():
    private_key = _rsa_key()
    verifier = Auth0AccessTokenVerifier(
        _settings(),
        jwks_client=_StaticJwksClient(private_key.public_key()),
    )
    claims = _claims(scope="", permissions=["admin:backlogs"])

    principal = verifier.verify(_token(private_key, claims=claims))

    assert principal.scopes == frozenset()


def test_auth0_verifier_rejects_non_string_scope_claim():
    private_key = _rsa_key()
    verifier = Auth0AccessTokenVerifier(
        _settings(),
        jwks_client=_StaticJwksClient(private_key.public_key()),
    )

    with pytest.raises(InvalidAccessTokenError):
        verifier.verify(_token(private_key, claims=_claims(scope=["read:backlogs"])))


def test_auth0_verifier_reports_jwks_outage_as_service_unavailable():
    private_key = _rsa_key()
    verifier = Auth0AccessTokenVerifier(
        _settings(),
        jwks_client=_UnavailableJwksClient(),
    )

    with pytest.raises(AuthenticationServiceUnavailableError):
        verifier.verify(_token(private_key))


def test_auth0_configuration_normalizes_domain_and_builds_trusted_urls(monkeypatch):
    monkeypatch.setenv("AUTH0_DOMAIN", "https://Tenant.US.Auth0.com/")
    monkeypatch.setenv("AUTH0_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("AUTH0_CLOCK_SKEW_SECONDS", "15")
    monkeypatch.setenv("AUTH0_JWKS_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("AUTH0_JWKS_CACHE_SECONDS", "600")

    settings = resolve_auth0_settings()

    assert settings == Auth0Settings(
        domain="tenant.us.auth0.com",
        audience=AUDIENCE,
        issuer="https://tenant.us.auth0.com/",
        jwks_url="https://tenant.us.auth0.com/.well-known/jwks.json",
        clock_skew_seconds=15,
        jwks_timeout_seconds=2.5,
        jwks_cache_seconds=600.0,
    )


def test_auth0_configuration_fails_closed_when_required_values_are_missing(monkeypatch):
    monkeypatch.delenv("AUTH0_DOMAIN", raising=False)
    monkeypatch.delenv("AUTH0_AUDIENCE", raising=False)

    with pytest.raises(RuntimeError, match="AUTH0_DOMAIN is required"):
        resolve_auth0_settings()


def test_application_factory_fails_closed_without_auth0_configuration(monkeypatch):
    monkeypatch.delenv("AUTH0_DOMAIN", raising=False)
    monkeypatch.delenv("AUTH0_AUDIENCE", raising=False)

    with pytest.raises(RuntimeError, match="AUTH0_DOMAIN is required"):
        create_app(api_docs_enabled=False)


def test_api_docs_setting_is_explicit(monkeypatch):
    monkeypatch.setenv("JOHNNY_JOHNNY_API_DOCS_ENABLED", "false")
    assert resolve_api_docs_enabled() is False

    monkeypatch.setenv("JOHNNY_JOHNNY_API_DOCS_ENABLED", "sometimes")
    with pytest.raises(RuntimeError, match="must be true or false"):
        resolve_api_docs_enabled()
