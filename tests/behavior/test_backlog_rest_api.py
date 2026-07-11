from __future__ import annotations

import asyncio
import json
from urllib.parse import unquote, urlencode, urlsplit


import johnny_johnny_agent.api.routes as api_routes
from johnny_johnny_agent.api.app import create_app
from johnny_johnny_agent.api.security import (
    ALL_API_PERMISSIONS,
    AuthenticatedPrincipal,
    AuthenticationServiceUnavailableError,
    InvalidAccessTokenError,
)
from johnny_johnny_agent.capabilities.backlog_persistence.postgres import (
    BacklogImportResult,
    BacklogLocation,
    DatabaseStatus,
)
from johnny_johnny_agent.capabilities.backlog_persistence.workflow import (
    BacklogDeleteResult,
    BacklogPurgeResult,
    BacklogReconcilePreview,
    BacklogReconcileResult,
    BacklogYamlExportResult,
    TargetedBacklogMutationConsistencyError,
)
from johnny_johnny_agent.capabilities.backlog_sync.planner import (
    CreateEpicOperation,
    CreateIssueOperation,
    ExecutionPlan,
    UpdateIssueStatusOperation,
)
from johnny_johnny_agent.domain.backlog import (
    Backlog,
    Comment,
    Epic,
    Issue,
    Project,
)


class _Response:
    def __init__(self, status_code: int, headers: dict[str, str], content: bytes):
        self.status_code = status_code
        self.headers = headers
        self.content = content

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    def json(self):
        return json.loads(self.content)


class _AsgiTestClient:
    """Small dependency-free ASGI client for endpoint behavior tests."""

    def __init__(self, application, *, default_headers=None):
        self.application = application
        self.default_headers = default_headers or {}

    def get(self, path: str, *, params=None, headers=None) -> _Response:
        return self.request("GET", path, params=params, headers=headers)

    def post(
        self, path: str, *, params=None, json=None, content=None, headers=None
    ) -> _Response:
        return self.request(
            "POST",
            path,
            params=params,
            json_body=json,
            content=content,
            headers=headers,
        )

    def patch(
        self, path: str, *, params=None, json=None, content=None, headers=None
    ) -> _Response:
        return self.request(
            "PATCH",
            path,
            params=params,
            json_body=json,
            content=content,
            headers=headers,
        )

    def delete(
        self, path: str, *, params=None, json=None, content=None, headers=None
    ) -> _Response:
        return self.request(
            "DELETE",
            path,
            params=params,
            json_body=json,
            content=content,
            headers=headers,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params=None,
        json_body=None,
        content=None,
        headers=None,
    ) -> _Response:
        split = urlsplit(path)
        query = split.query
        if params:
            encoded = urlencode(params, doseq=True)
            query = f"{query}&{encoded}" if query else encoded

        request_headers = {
            key.lower(): value for key, value in self.default_headers.items()
        }
        request_headers.update(
            {key.lower(): value for key, value in (headers or {}).items()}
        )
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            request_headers.setdefault("content-type", "application/json")
        elif isinstance(content, str):
            body = content.encode("utf-8")
        else:
            body = content or b""
        request_headers.setdefault("host", "testserver")
        request_headers.setdefault("content-length", str(len(body)))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": unquote(split.path),
            "raw_path": split.path.encode("ascii"),
            "query_string": query.encode("ascii"),
            "root_path": "",
            "headers": [
                (key.encode("latin-1"), value.encode("latin-1"))
                for key, value in request_headers.items()
            ],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }

        async def invoke() -> _Response:
            sent_request = False
            messages = []

            async def receive():
                nonlocal sent_request
                if not sent_request:
                    sent_request = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return {"type": "http.disconnect"}

            async def send(message):
                messages.append(message)

            await self.application(scope, receive, send)
            start = next(
                message
                for message in messages
                if message["type"] == "http.response.start"
            )
            response_body = b"".join(
                message.get("body", b"")
                for message in messages
                if message["type"] == "http.response.body"
            )
            response_headers = {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in start.get("headers", [])
            }
            return _Response(start["status"], response_headers, response_body)

        return asyncio.run(invoke())


class _TestAccessTokenVerifier:
    def verify(self, token: str) -> AuthenticatedPrincipal:
        if token == "test-jwks-outage":
            raise AuthenticationServiceUnavailableError(
                "The identity provider signing keys are temporarily unavailable."
            )

        scopes_by_token = {
            "test-admin": ALL_API_PERMISSIONS,
            "test-reader": frozenset({"read:backlogs"}),
            "test-writer": frozenset({"read:backlogs", "write:backlogs"}),
            "test-operator": frozenset(
                {"read:backlogs", "write:backlogs", "operate:backlogs"}
            ),
            "test-admin-only": frozenset({"admin:backlogs"}),
            "test-unprivileged": frozenset(),
        }
        scopes = scopes_by_token.get(token)
        if scopes is None:
            raise InvalidAccessTokenError("The bearer token is invalid or expired.")
        return AuthenticatedPrincipal(
            subject=f"auth0|{token}",
            scopes=scopes,
            claims={"sub": f"auth0|{token}", "scope": " ".join(sorted(scopes))},
            client_id="test-client",
        )


app = create_app(
    access_token_verifier=_TestAccessTokenVerifier(),
    api_docs_enabled=True,
)
client = _AsgiTestClient(
    app,
    default_headers={"Authorization": "Bearer test-admin"},
)
anonymous_client = _AsgiTestClient(app)
writer_client = _AsgiTestClient(
    app,
    default_headers={"Authorization": "Bearer test-writer"},
)
operator_client = _AsgiTestClient(
    app,
    default_headers={"Authorization": "Bearer test-operator"},
)
admin_only_client = _AsgiTestClient(
    app,
    default_headers={"Authorization": "Bearer test-admin-only"},
)
PROJECT_PATH = "/api/v1/backlogs/Test%20Project"


def test_liveness_and_openapi_expose_the_versioned_api():
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "service": "johnny-johnny-agent",
        "version": "0.1.0",
        "status": "ok",
    }

    openapi = client.get("/openapi.json").json()
    assert (
        f"{PROJECT_PATH.replace('Test%20Project', '{project_title}')}/summary"
        in openapi["paths"]
    )
    assert "/api/v1/backlogs/import" in openapi["paths"]
    assert "/api/v1/auth/whoami" in openapi["paths"]


def test_application_can_remove_openapi_and_interactive_docs():
    private_app = create_app(
        access_token_verifier=_TestAccessTokenVerifier(),
        api_docs_enabled=False,
    )
    private_client = _AsgiTestClient(private_app)

    assert private_client.get("/openapi.json").status_code == 404
    assert private_client.get("/docs").status_code == 404
    assert private_client.get("/redoc").status_code == 404
    assert private_client.get("/api/v1/health/live").status_code == 200


def test_whoami_exercises_token_validation_without_database_access():
    authenticated = anonymous_client.get(
        "/api/v1/auth/whoami",
        headers={"Authorization": "Bearer test-reader"},
    )
    missing = anonymous_client.get("/api/v1/auth/whoami")

    assert authenticated.status_code == 200
    assert authenticated.json() == {
        "subject": "auth0|test-reader",
        "client_id": "test-client",
        "scopes": ["read:backlogs"],
    }
    assert missing.status_code == 401


def test_openapi_marks_backlog_routes_as_bearer_protected():
    openapi = client.get("/openapi.json").json()
    protected_operation = openapi["paths"]["/api/v1/backlogs/{project_title}/summary"][
        "get"
    ]
    whoami_operation = openapi["paths"]["/api/v1/auth/whoami"]["get"]
    live_operation = openapi["paths"]["/api/v1/health/live"]["get"]

    assert openapi["components"]["securitySchemes"]["Auth0Bearer"] == {
        "type": "http",
        "description": (
            "Auth0 access token issued for the configured Johnny-Johnny API audience."
        ),
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    assert protected_operation["security"] == [{"Auth0Bearer": []}]
    assert whoami_operation["security"] == [{"Auth0Bearer": []}]
    assert "security" not in live_operation


def test_protected_route_rejects_missing_and_invalid_tokens(monkeypatch):
    def should_not_load(**kwargs):
        raise AssertionError("authentication must fail before the workflow runs")

    monkeypatch.setattr(api_routes, "load_backlog_from_postgres", should_not_load)

    missing = anonymous_client.get(f"{PROJECT_PATH}/summary")
    invalid = anonymous_client.get(
        f"{PROJECT_PATH}/summary",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert missing.json()["error"] == {
        "code": "authentication_required",
        "message": "A bearer access token is required for this endpoint.",
        "details": None,
    }

    assert invalid.status_code == 401
    assert invalid.headers["www-authenticate"] == 'Bearer error="invalid_token"'
    assert invalid.json()["error"]["code"] == "invalid_access_token"


def test_authentication_key_outage_is_reported_without_running_the_workflow(
    monkeypatch,
):
    def should_not_load(**kwargs):
        raise AssertionError("authentication must fail before the workflow runs")

    monkeypatch.setattr(api_routes, "load_backlog_from_postgres", should_not_load)

    response = anonymous_client.get(
        f"{PROJECT_PATH}/summary",
        headers={"Authorization": "Bearer test-jwks-outage"},
    )

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "authentication_service_unavailable",
        "message": ("The identity provider signing keys are temporarily unavailable."),
        "details": None,
    }


def test_protected_route_rejects_an_authenticated_token_without_scope(monkeypatch):
    def should_not_load(**kwargs):
        raise AssertionError("authorization must fail before the workflow runs")

    monkeypatch.setattr(api_routes, "load_backlog_from_postgres", should_not_load)

    response = anonymous_client.get(
        f"{PROJECT_PATH}/summary",
        headers={"Authorization": "Bearer test-unprivileged"},
    )

    assert response.status_code == 403
    assert response.headers["www-authenticate"] == (
        'Bearer error="insufficient_scope", scope="read:backlogs"'
    )
    assert response.json()["error"] == {
        "code": "insufficient_scope",
        "message": (
            "The access token does not grant the permission required for "
            "this operation."
        ),
        "details": {"required_scopes": ["read:backlogs"]},
    }


def test_permissions_are_independent_and_admin_is_not_a_wildcard(monkeypatch):
    def should_not_run(**kwargs):
        raise AssertionError("authorization must fail before workflow dispatch")

    monkeypatch.setattr(
        api_routes,
        "preview_reconcile_backlog_from_postgres",
        should_not_run,
    )
    monkeypatch.setattr(
        api_routes,
        "preview_purge_backlog_projection",
        should_not_run,
    )
    monkeypatch.setattr(api_routes, "load_backlog_from_postgres", should_not_run)

    write_cannot_operate = writer_client.post(
        f"{PROJECT_PATH}/reconciliation",
        json={"mode": "dry-run", "max_operations": 1},
    )
    operate_cannot_administer = operator_client.post(
        f"{PROJECT_PATH}/purge",
        json={"mode": "dry-run", "max_issues": 1},
    )
    admin_cannot_read_without_read_scope = admin_only_client.get(
        f"{PROJECT_PATH}/summary"
    )

    assert write_cannot_operate.status_code == 403
    assert write_cannot_operate.json()["error"]["details"] == {
        "required_scopes": ["operate:backlogs"]
    }
    assert operate_cannot_administer.status_code == 403
    assert operate_cannot_administer.json()["error"]["details"] == {
        "required_scopes": ["admin:backlogs"]
    }
    assert admin_cannot_read_without_read_scope.status_code == 403
    assert admin_cannot_read_without_read_scope.json()["error"]["details"] == {
        "required_scopes": ["read:backlogs"]
    }


def test_read_scope_can_read_but_cannot_mutate(monkeypatch):
    monkeypatch.setattr(
        api_routes,
        "load_backlog_from_postgres",
        lambda **kwargs: _backlog(),
    )

    read = anonymous_client.get(
        f"{PROJECT_PATH}/summary",
        headers={"Authorization": "Bearer test-reader"},
    )
    mutation = anonymous_client.post(
        f"{PROJECT_PATH}/epics",
        headers={"Authorization": "Bearer test-reader"},
        json={
            "mode": "dry-run",
            "id": "not-created",
            "title": "Not Created",
            "repository": "ggortsema/test-repo",
        },
    )

    assert read.status_code == 200
    assert mutation.status_code == 403
    assert mutation.json()["error"]["details"] == {
        "required_scopes": ["write:backlogs"]
    }


def test_readiness_returns_minimal_503_when_database_check_raises(monkeypatch):
    def unavailable(database_url=None):
        raise RuntimeError("sensitive connection details")

    monkeypatch.setattr(api_routes, "check_postgres_backlog_database", unavailable)

    response = anonymous_client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "service": "johnny-johnny-agent",
        "version": "0.1.0",
        "status": "not-ready",
        "checks": {"database": "unavailable", "canonical_schema": "unknown"},
    }
    assert "sensitive" not in response.text


def test_readiness_reports_database_schema_state(monkeypatch):
    captured = []

    def fake_check(database_url=None):
        captured.append(database_url)
        return _database_status(ready=True)

    monkeypatch.setattr(api_routes, "check_postgres_backlog_database", fake_check)

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert captured == [None]
    assert response.json() == {
        "service": "johnny-johnny-agent",
        "version": "0.1.0",
        "status": "ready",
        "checks": {"database": "ok", "canonical_schema": "ok"},
    }


def test_readiness_returns_503_when_canonical_schema_is_incomplete(monkeypatch):
    monkeypatch.setattr(
        api_routes,
        "check_postgres_backlog_database",
        lambda database_url=None: _database_status(ready=False),
    )

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "service": "johnny-johnny-agent",
        "version": "0.1.0",
        "status": "not-ready",
        "checks": {"database": "ok", "canonical_schema": "unavailable"},
    }


def test_summary_epics_items_and_describe_reuse_postgres_domain_reads(monkeypatch):
    calls = []
    backlog = _backlog()

    def fake_load(**kwargs):
        calls.append(kwargs)
        return backlog

    monkeypatch.setattr(api_routes, "load_backlog_from_postgres", fake_load)

    summary = client.get(f"{PROJECT_PATH}/summary")
    epics = client.get(f"{PROJECT_PATH}/epics")
    items = client.get(
        f"{PROJECT_PATH}/items",
        params=[("status", "ready")],
    )
    described = client.get(f"{PROJECT_PATH}/items/test-issue")

    assert summary.status_code == 200
    assert summary.json()["epic_count"] == 2
    assert summary.json()["issue_count"] == 2
    assert summary.json()["comment_count"] == 1

    assert epics.status_code == 200
    assert [item["id"] for item in epics.json()["items"]] == [
        "test-epic",
        "target-epic",
    ]
    assert epics.json()["items"][0]["issue_count"] == 2

    assert items.status_code == 200
    assert [item["id"] for item in items.json()["items"]] == ["test-issue"]
    assert items.json()["items"][0]["parent_epic_id"] == "test-epic"

    assert described.status_code == 200
    assert described.json()["id"] == "test-issue"
    assert described.json()["parent_epic_id"] == "test-epic"
    assert described.json()["comments"][0]["id"] == "comment-1"

    assert calls == [
        _expected_location_kwargs(),
        _expected_location_kwargs(),
        _expected_location_kwargs(),
        _expected_location_kwargs(),
    ]


def test_item_filters_reject_include_and_exclude_together(monkeypatch):
    monkeypatch.setattr(
        api_routes, "load_backlog_from_postgres", lambda **kwargs: _backlog()
    )

    response = client.get(
        f"{PROJECT_PATH}/items",
        params=[("status", "Ready"), ("exclude_status", "Done")],
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_create_epic_dispatches_dry_run_and_confirmed_workflows(monkeypatch):
    calls = []

    def preview(**kwargs):
        calls.append(("preview", kwargs))
        return _epic("new-epic", "New Epic")

    def create(**kwargs):
        calls.append(("create", kwargs))
        epic = _epic("new-epic", "New Epic")
        epic.provider_metadata = {"github": {"number": 44}}
        return epic

    monkeypatch.setattr(api_routes, "preview_create_epic_in_postgres", preview)
    monkeypatch.setattr(api_routes, "create_epic_in_postgres", create)

    payload = {
        "id": "new-epic",
        "title": "New Epic",
        "repository": "ggortsema/test-repo",
        "description": "REST-created epic.",
        "acceptance_criteria": ["It is projected."],
    }
    dry_run = client.post(
        f"{PROJECT_PATH}/epics",
        json={"mode": "dry-run", **payload},
    )
    confirmed = client.post(
        f"{PROJECT_PATH}/epics",
        json={"mode": "confirmed", **payload},
    )

    assert dry_run.status_code == 200
    assert dry_run.json()["committed"] is False
    assert confirmed.status_code == 201
    assert confirmed.json()["committed"] is True
    assert confirmed.json()["item"]["provider_metadata"]["github"]["number"] == 44
    assert [name for name, _ in calls] == ["preview", "create"]
    assert calls[0][1] == {
        **_expected_location_kwargs(),
        "title": "New Epic",
        "repository_name": "ggortsema/test-repo",
        "epic_id": "new-epic",
        "description": "REST-created epic.",
        "acceptance_criteria": ["It is projected."],
    }


def test_create_issue_dispatches_dry_run_and_confirmed_workflows(monkeypatch):
    calls = []
    parent = _epic("test-epic", "Test Epic")

    def preview(**kwargs):
        calls.append(("preview", kwargs))
        return _issue("new-issue", "New Issue")

    def create(**kwargs):
        calls.append(("create", kwargs))
        issue = _issue("new-issue", "New Issue")
        issue.provider_metadata = {"github": {"number": 45}}
        return issue, parent

    monkeypatch.setattr(api_routes, "preview_create_issue_in_postgres", preview)
    monkeypatch.setattr(api_routes, "create_issue_in_postgres", create)

    payload = {
        "parent_epic_id": "test-epic",
        "id": "new-issue",
        "title": "New Issue",
        "description": "REST-created issue.",
        "acceptance_criteria": ["It is attached."],
    }
    dry_run = client.post(
        f"{PROJECT_PATH}/issues",
        json={"mode": "dry-run", **payload},
    )
    confirmed = client.post(
        f"{PROJECT_PATH}/issues",
        json={"mode": "confirmed", **payload},
    )

    assert dry_run.status_code == 200
    assert dry_run.json()["item"]["parent_epic_id"] == "test-epic"
    assert confirmed.status_code == 201
    assert confirmed.json()["item"]["provider_metadata"]["github"]["number"] == 45
    assert [name for name, _ in calls] == ["preview", "create"]


def test_update_item_dispatches_modes_and_requires_a_change(monkeypatch):
    calls = []

    def preview(**kwargs):
        calls.append(("preview", kwargs))
        issue = _issue("test-issue", "Updated Issue")
        issue.status = "In Progress"
        return issue

    def update(**kwargs):
        calls.append(("update", kwargs))
        issue = _issue("test-issue", "Updated Issue")
        issue.status = "In Progress"
        return issue

    monkeypatch.setattr(api_routes, "preview_update_item_in_postgres", preview)
    monkeypatch.setattr(api_routes, "update_item_in_postgres", update)

    invalid = client.patch(
        f"{PROJECT_PATH}/items/test-issue",
        json={"mode": "dry-run"},
    )
    dry_run = client.patch(
        f"{PROJECT_PATH}/items/test-issue",
        json={"mode": "dry-run", "status": "in progress"},
    )
    confirmed = client.patch(
        f"{PROJECT_PATH}/items/test-issue",
        json={"mode": "confirmed", "status": "in progress", "comment": "Started."},
    )

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "request_validation_error"
    assert dry_run.status_code == 200
    assert dry_run.json()["committed"] is False
    assert confirmed.status_code == 200
    assert confirmed.json()["committed"] is True
    assert [name for name, _ in calls] == ["preview", "update"]


def test_move_issue_dispatches_modes(monkeypatch):
    calls = []
    source = _epic("test-epic", "Test Epic")
    target = _epic("target-epic", "Target Epic")

    def preview(**kwargs):
        calls.append(("preview", kwargs))
        return _issue("test-issue", "Test Issue"), source, target

    def move(**kwargs):
        calls.append(("move", kwargs))
        return _issue("test-issue", "Test Issue"), source, target

    monkeypatch.setattr(api_routes, "preview_move_issue_in_postgres", preview)
    monkeypatch.setattr(api_routes, "move_issue_in_postgres", move)

    dry_run = client.post(
        f"{PROJECT_PATH}/issues/test-issue/move",
        json={"mode": "dry-run", "target_epic_id": "target-epic"},
    )
    confirmed = client.post(
        f"{PROJECT_PATH}/issues/test-issue/move",
        json={"mode": "confirmed", "target_epic_id": "target-epic"},
    )

    assert dry_run.status_code == 200
    assert dry_run.json()["source_epic"]["id"] == "test-epic"
    assert confirmed.json()["target_epic"]["id"] == "target-epic"
    assert confirmed.json()["item"]["parent_epic_id"] == "target-epic"
    assert [name for name, _ in calls] == ["preview", "move"]


def test_delete_issue_dispatches_modes(monkeypatch):
    calls = []
    issue = _issue("test-issue", "Test Issue")
    parent = _epic("test-epic", "Test Epic")

    def preview(**kwargs):
        calls.append(("preview", kwargs))
        return BacklogDeleteResult(
            issue=issue, parent_epic=parent, github_issue_deleted=False
        )

    def delete(**kwargs):
        calls.append(("delete", kwargs))
        return BacklogDeleteResult(
            issue=issue, parent_epic=parent, github_issue_deleted=True
        )

    monkeypatch.setattr(api_routes, "preview_delete_issue_in_postgres", preview)
    monkeypatch.setattr(api_routes, "delete_issue_in_postgres", delete)

    dry_run = client.delete(
        f"{PROJECT_PATH}/issues/test-issue",
        params={"mode": "dry-run"},
    )
    confirmed = client.delete(
        f"{PROJECT_PATH}/issues/test-issue",
        params={"mode": "confirmed"},
    )

    assert dry_run.status_code == 200
    assert dry_run.json()["github_issue_deleted"] is None
    assert confirmed.json()["github_issue_deleted"] is True
    assert [name for name, _ in calls] == ["preview", "delete"]


def test_reconciliation_dispatches_modes_and_serializes_operations(monkeypatch):
    calls = []
    backlog = _backlog()
    epic = backlog.epics[0]
    issue = next(item for item in epic.issues if item.id == "test-issue")
    plan = ExecutionPlan(
        operations=[
            CreateEpicOperation(epic=epic),
            CreateIssueOperation(issue=issue, parent_epic=epic),
            UpdateIssueStatusOperation(
                issue=issue,
                current_status="Backlog",
                desired_status="Ready",
            ),
        ]
    )
    preview = BacklogReconcilePreview(
        plan=plan,
        execution_plan=plan,
        total_operation_count=3,
        execution_operation_count=3,
        remaining_operation_count=0,
    )

    def fake_preview(**kwargs):
        calls.append(("preview", kwargs))
        return preview

    def fake_reconcile(**kwargs):
        calls.append(("reconcile", kwargs))
        return BacklogReconcileResult(
            preview=preview,
            executed_group_count=2,
            hydrated_item_count=1,
        )

    monkeypatch.setattr(
        api_routes, "preview_reconcile_backlog_from_postgres", fake_preview
    )
    monkeypatch.setattr(api_routes, "reconcile_backlog_from_postgres", fake_reconcile)

    dry_run = operator_client.post(
        f"{PROJECT_PATH}/reconciliation",
        json={"mode": "dry-run", "max_operations": 10},
    )
    confirmed = operator_client.post(
        f"{PROJECT_PATH}/reconciliation",
        json={"mode": "confirmed", "all": True},
    )

    assert dry_run.status_code == 200
    assert dry_run.json()["operations"][1] == {
        "kind": "create_issue",
        "item_id": "test-issue",
        "title": "Test Issue",
        "parent_epic_id": "test-epic",
        "comment_id": None,
        "current_status": None,
        "desired_status": None,
    }
    assert confirmed.json()["executed_group_count"] == 2
    assert confirmed.json()["hydrated_item_count"] == 1
    assert confirmed.json()["complete"] is True
    assert calls[0][1]["max_operations"] == 10
    assert calls[1][1]["max_operations"] is None


def test_purge_dispatches_modes_and_preserves_scope(monkeypatch):
    calls = []
    preview = BacklogPurgeResult(
        project_title="Test Project",
        issues=({"id": "I_1", "number": 1, "title": "Test Issue"},),
        total_issue_count=2,
        deleted_issue_count=0,
        remaining_issue_count=1,
        cleared_item_count=0,
        projection_metadata_cleared=False,
    )
    confirmed_result = BacklogPurgeResult(
        project_title="Test Project",
        issues=({"id": "I_1", "number": 1, "title": "Test Issue"},),
        total_issue_count=1,
        deleted_issue_count=1,
        remaining_issue_count=0,
        cleared_item_count=3,
        projection_metadata_cleared=True,
    )

    def fake_preview(**kwargs):
        calls.append(("preview", kwargs))
        return preview

    def fake_purge(**kwargs):
        calls.append(("purge", kwargs))
        return confirmed_result

    monkeypatch.setattr(api_routes, "preview_purge_backlog_projection", fake_preview)
    monkeypatch.setattr(
        api_routes, "purge_backlog_projection_from_postgres", fake_purge
    )

    dry_run = admin_only_client.post(
        f"{PROJECT_PATH}/purge",
        json={"mode": "dry-run", "max_issues": 1},
    )
    confirmed = admin_only_client.post(
        f"{PROJECT_PATH}/purge",
        json={"mode": "confirmed", "all": True},
    )

    assert dry_run.status_code == 200
    assert dry_run.json()["selected_issue_count"] == 1
    assert dry_run.json()["committed"] is False
    assert confirmed.json()["deleted_issue_count"] == 1
    assert confirmed.json()["projection_metadata_cleared"] is True
    assert confirmed.json()["complete"] is True
    assert calls[0][1]["max_issues"] == 1
    assert calls[1][1]["max_issues"] is None


def test_import_accepts_yaml_body_for_preview_and_confirmed_replacement(monkeypatch):
    calls = []

    def fake_import(**kwargs):
        calls.append(kwargs)
        return BacklogImportResult(
            location=BacklogLocation(
                provider="github",
                provider_account_username="ggortsema",
                project_title="Test Project",
            ),
            provider_project_id="project-1",
            epic_count=1,
            issue_count=1,
            acceptance_criterion_count=1,
            comment_count=0,
            label_count=0,
            assignee_count=0,
            verified=True,
        )

    monkeypatch.setattr(api_routes, "import_backlog_to_postgres", fake_import)
    content = _minimal_backlog_yaml()

    dry_run = admin_only_client.post(
        "/api/v1/backlogs/import",
        params={"mode": "dry-run"},
        content=content,
        headers={"Content-Type": "application/yaml"},
    )

    assert dry_run.status_code == 200
    assert dry_run.json()["project"]["title"] == "Test Project"
    assert dry_run.json()["committed"] is False
    assert calls == []

    confirmed = admin_only_client.post(
        "/api/v1/backlogs/import",
        params={"mode": "confirmed", "verify": "true"},
        content=content,
        headers={"Content-Type": "application/yaml"},
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["committed"] is True
    assert confirmed.json()["verified"] is True
    assert len(calls) == 1
    assert calls[0]["backlog"].project.title == "Test Project"
    assert calls[0]["verify"] is True


def test_import_reports_invalid_yaml_with_consistent_error_shape():
    response = admin_only_client.post(
        "/api/v1/backlogs/import",
        params={"mode": "dry-run"},
        content="epics: [",
        headers={"Content-Type": "application/yaml"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "backlog_document_invalid"


def test_export_returns_portable_yaml_and_counts(monkeypatch):
    captured = []

    def fake_export(**kwargs):
        captured.append(kwargs)
        return BacklogYamlExportResult(
            location=BacklogLocation(
                provider="github",
                provider_account_username="ggortsema",
                project_title="Test Project",
            ),
            content="version: 1\nproject:\n  title: Test Project\n",
            epic_count=2,
            issue_count=3,
            comment_count=4,
        )

    monkeypatch.setattr(
        api_routes, "export_backlog_yaml_text_from_postgres", fake_export
    )

    response = client.get(f"{PROJECT_PATH}/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/yaml")
    assert response.headers["x-johnny-epic-count"] == "2"
    assert response.headers["x-johnny-issue-count"] == "3"
    assert response.text.startswith("version: 1")
    assert captured == [_expected_location_kwargs()]


def test_not_found_and_consistency_failures_map_to_stable_http_errors(monkeypatch):
    monkeypatch.setattr(
        api_routes,
        "load_backlog_from_postgres",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("Backlog item not found: missing")
        ),
    )
    missing = client.get(f"{PROJECT_PATH}/items/missing")

    monkeypatch.setattr(
        api_routes,
        "delete_issue_in_postgres",
        lambda **kwargs: (_ for _ in ()).throw(
            TargetedBacklogMutationConsistencyError(
                "GitHub deleted; database rollback failed"
            )
        ),
    )
    inconsistent = client.delete(
        f"{PROJECT_PATH}/issues/test-issue",
        params={"mode": "confirmed"},
    )

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "resource_not_found"
    assert inconsistent.status_code == 409
    assert inconsistent.json()["error"]["code"] == "cross_boundary_consistency_error"


def _database_status(*, ready: bool) -> DatabaseStatus:
    expected = (
        "backlog_item_acceptance_criteria",
        "backlog_item_assignees",
        "backlog_item_comments",
        "backlog_item_labels",
        "backlog_items",
        "provider_accounts",
        "provider_projects",
        "providers",
        "users",
    )
    return DatabaseStatus(
        database="styxcd",
        database_user="rincexwind",
        schema="johnny_johnny",
        server_version="15.8",
        available_tables=expected if ready else expected[:-5],
        missing_tables=() if ready else ("backlog_items",),
        provider_count=5,
    )


def _expected_location_kwargs() -> dict:
    return {
        "provider": "github",
        "provider_account_username": "ggortsema",
        "provider_project_title": "Test Project",
        "database_url": None,
    }


def _backlog() -> Backlog:
    issue = _issue("test-issue", "Test Issue")
    issue.comments = [Comment(id="comment-1", body="A comment")]
    done_issue = _issue("done-issue", "Done Issue")
    done_issue.status = "Done"
    done_issue.issue_state = "CLOSED"
    done_issue.order = 2000
    return Backlog(
        project=Project(
            provider="github",
            title="Test Project",
            number=3,
            url="https://github.test/projects/3",
            provider_metadata={"github": {"id": "PVT_1"}},
        ),
        epics=[
            Epic(
                id="test-epic",
                type="epic",
                title="Test Epic",
                repository="ggortsema/test-repo",
                status="In Progress",
                issue_state="OPEN",
                order=1000,
                issues=[done_issue, issue],
            ),
            _epic("target-epic", "Target Epic", order=2000),
        ],
    )


def _epic(epic_id: str, title: str, *, order: int = 1000) -> Epic:
    return Epic(
        id=epic_id,
        type="epic",
        title=title,
        repository="ggortsema/test-repo",
        status="Backlog",
        issue_state="OPEN",
        order=order,
        provider_metadata={"github": {}},
    )


def _issue(issue_id: str, title: str) -> Issue:
    return Issue(
        id=issue_id,
        type="issue",
        title=title,
        repository="ggortsema/test-repo",
        status="Ready",
        issue_state="OPEN",
        order=1000,
        provider_metadata={"github": {}},
    )


def _minimal_backlog_yaml() -> str:
    return """\
version: 1
project:
  provider: github
  title: Test Project
  number: 3
  url: null
  provider_metadata:
    github:
      id: PVT_1
epics:
  - id: test-epic
    type: epic
    title: Test Epic
    repository: ggortsema/test-repo
    status: Backlog
    issue_state: OPEN
    order: 1000
    description: Test epic.
    acceptance_criteria:
      - The epic exists.
    comments: []
    labels: []
    assignees: []
    milestone: null
    provider_metadata:
      github: {}
    issues:
      - id: test-issue
        type: issue
        title: Test Issue
        repository: ggortsema/test-repo
        status: Ready
        issue_state: OPEN
        order: 1000
        description: Test issue.
        acceptance_criteria: []
        comments: []
        labels: []
        assignees: []
        milestone: null
        provider_metadata:
          github: {}
"""
