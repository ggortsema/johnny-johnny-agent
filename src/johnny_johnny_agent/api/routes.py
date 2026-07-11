"""FastAPI routes over the shared PostgreSQL-backed application workflows."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Response

from johnny_johnny_agent.api.errors import ApiRequestError, BacklogDocumentError
from johnny_johnny_agent.api.models import (
    BacklogImportResponse,
    BacklogItemListResponse,
    BacklogItemResponse,
    BacklogSummaryResponse,
    AuthenticatedPrincipalResponse,
    CreateEpicRequest,
    CreateIssueRequest,
    DeleteIssueResponse,
    ErrorResponse,
    ExecutionMode,
    ItemMutationResponse,
    MoveIssueRequest,
    MoveIssueResponse,
    PurgeRequest,
    PurgeResponse,
    ReconcileRequest,
    ReconcileResponse,
    ServiceReadinessResponse,
    ServiceStatusResponse,
    UpdateBacklogItemRequest,
)
from johnny_johnny_agent.api.serialization import (
    item_response,
    item_summary_response,
    project_response,
    purge_issue_response,
    reconcile_operation_response,
)
from johnny_johnny_agent.api.security import (
    ApiPermission,
    AuthenticatedPrincipal,
    authenticated_principal,
    require_scopes,
)
from johnny_johnny_agent.capabilities.backlog_persistence.workflow import (
    check_postgres_backlog_database,
    create_epic_in_postgres,
    create_issue_in_postgres,
    delete_issue_in_postgres,
    export_backlog_yaml_text_from_postgres,
    import_backlog_to_postgres,
    load_backlog_from_postgres,
    move_issue_in_postgres,
    preview_create_epic_in_postgres,
    preview_create_issue_in_postgres,
    preview_delete_issue_in_postgres,
    preview_move_issue_in_postgres,
    preview_purge_backlog_projection,
    preview_reconcile_backlog_from_postgres,
    preview_update_item_in_postgres,
    purge_backlog_projection_from_postgres,
    reconcile_backlog_from_postgres,
    summarize_backlog,
    update_item_in_postgres,
)
from johnny_johnny_agent.capabilities.backlog_sync.mutations import (
    find_backlog_item,
    find_epic_issues,
    find_parent_epic,
)
from johnny_johnny_agent.capabilities.backlog_sync.yaml_loader import (
    load_backlog_yaml_text,
)
from johnny_johnny_agent.domain.backlog import Issue


API_VERSION = "v1"
PROJECT_VERSION = "0.1.0"
DEFAULT_PROVIDER_ACCOUNT_USERNAME = os.environ.get(
    "JOHNNY_JOHNNY_PROVIDER_ACCOUNT",
    "ggortsema",
)

ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid bearer token"},
    403: {"model": ErrorResponse, "description": "Bearer token lacks required scope"},
    400: {"model": ErrorResponse, "description": "Invalid cross-field request"},
    404: {"model": ErrorResponse, "description": "Backlog resource not found"},
    409: {"model": ErrorResponse, "description": "Conflict or consistency failure"},
    422: {"model": ErrorResponse, "description": "Validation or domain failure"},
    502: {"model": ErrorResponse, "description": "Provider operation failed"},
    503: {
        "model": ErrorResponse,
        "description": "Persistence or authentication dependency unavailable",
    },
}

router = APIRouter(prefix=f"/api/{API_VERSION}", responses=ERROR_RESPONSES)

REQUIRE_BACKLOG_READ = Depends(require_scopes(ApiPermission.READ_BACKLOGS))
REQUIRE_BACKLOG_WRITE = Depends(require_scopes(ApiPermission.WRITE_BACKLOGS))
REQUIRE_BACKLOG_OPERATE = Depends(require_scopes(ApiPermission.OPERATE_BACKLOGS))
REQUIRE_BACKLOG_ADMIN = Depends(require_scopes(ApiPermission.ADMIN_BACKLOGS))


@dataclass(frozen=True)
class ProviderContext:
    provider: str
    provider_account_username: str


def provider_context(
    provider: Annotated[str, Query(description="Provider key.")] = "github",
    provider_account_username: Annotated[
        str,
        Query(
            alias="provider_account",
            description="Provider account username that owns the project.",
        ),
    ] = DEFAULT_PROVIDER_ACCOUNT_USERNAME,
) -> ProviderContext:
    return ProviderContext(
        provider=provider,
        provider_account_username=provider_account_username,
    )


ProviderContextDependency = Annotated[ProviderContext, Depends(provider_context)]
AuthenticatedPrincipalDependency = Annotated[
    AuthenticatedPrincipal,
    Depends(authenticated_principal),
]


@router.get(
    "/auth/whoami",
    response_model=AuthenticatedPrincipalResponse,
    tags=["authentication"],
)
def whoami(
    principal: AuthenticatedPrincipalDependency,
) -> AuthenticatedPrincipalResponse:
    """Confirm token validation without exposing the token's raw claims."""
    return AuthenticatedPrincipalResponse(
        subject=principal.subject,
        client_id=principal.client_id,
        scopes=sorted(principal.scopes),
    )


@router.get("/health/live", response_model=ServiceStatusResponse, tags=["health"])
def liveness() -> ServiceStatusResponse:
    return ServiceStatusResponse(
        service="johnny-johnny-agent",
        version=PROJECT_VERSION,
        status="ok",
    )


@router.get(
    "/health/ready",
    response_model=ServiceReadinessResponse,
    responses={
        503: {
            "model": ServiceReadinessResponse,
            "description": "PostgreSQL or canonical schema readiness failed",
        }
    },
    tags=["health"],
)
def readiness(response: Response) -> ServiceReadinessResponse:
    try:
        database_status = check_postgres_backlog_database()
    except Exception:
        response.status_code = 503
        return ServiceReadinessResponse(
            service="johnny-johnny-agent",
            version=PROJECT_VERSION,
            status="not-ready",
            checks={"database": "unavailable", "canonical_schema": "unknown"},
        )

    ready = database_status.ready
    if not ready:
        response.status_code = 503
    return ServiceReadinessResponse(
        service="johnny-johnny-agent",
        version=PROJECT_VERSION,
        status="ready" if ready else "not-ready",
        checks={
            "database": "ok",
            "canonical_schema": "ok" if ready else "unavailable",
        },
    )


@router.get(
    "/backlogs/{project_title}/summary",
    response_model=BacklogSummaryResponse,
    dependencies=[REQUIRE_BACKLOG_READ],
    tags=["backlog reads"],
)
def inspect_backlog(
    project_title: str,
    context: ProviderContextDependency,
) -> BacklogSummaryResponse:
    backlog = _load_backlog(project_title, context)
    summary = summarize_backlog(backlog)
    return BacklogSummaryResponse(
        project=project_response(backlog.project),
        epic_count=summary.epic_count,
        issue_count=summary.issue_count,
        acceptance_criterion_count=summary.acceptance_criterion_count,
        comment_count=summary.comment_count,
        label_count=summary.label_count,
        assignee_count=summary.assignee_count,
    )


@router.get(
    "/backlogs/{project_title}/epics",
    response_model=BacklogItemListResponse,
    dependencies=[REQUIRE_BACKLOG_READ],
    tags=["backlog reads"],
)
def list_epics(
    project_title: str,
    context: ProviderContextDependency,
) -> BacklogItemListResponse:
    backlog = _load_backlog(project_title, context)
    items = [
        item_summary_response(epic)
        for epic in sorted(backlog.epics, key=lambda item: item.order)
    ]
    return BacklogItemListResponse(
        project=project_response(backlog.project),
        items=items,
        count=len(items),
    )


@router.get(
    "/backlogs/{project_title}/items",
    response_model=BacklogItemListResponse,
    dependencies=[REQUIRE_BACKLOG_READ],
    tags=["backlog reads"],
)
def list_items(
    project_title: str,
    context: ProviderContextDependency,
    epic_id: Annotated[
        str | None,
        Query(description="Restrict results to one parent epic."),
    ] = None,
    status: Annotated[
        list[str] | None,
        Query(description="Status to include. Repeat for multiple values."),
    ] = None,
    exclude_status: Annotated[
        list[str] | None,
        Query(description="Status to exclude. Repeat for multiple values."),
    ] = None,
) -> BacklogItemListResponse:
    if status and exclude_status:
        raise ApiRequestError("Use either status or exclude_status, not both.")

    backlog = _load_backlog(project_title, context)
    epics = (
        [next((epic for epic in backlog.epics if epic.id == epic_id), None)]
        if epic_id is not None
        else sorted(backlog.epics, key=lambda item: item.order)
    )
    if epic_id is not None and epics[0] is None:
        raise RuntimeError(f"Epic not found: {epic_id}")

    items = []
    for epic in epics:
        assert epic is not None
        items.extend(
            item_summary_response(issue, parent_epic_id=epic.id)
            for issue in find_epic_issues(
                backlog=backlog,
                epic_id=epic.id,
                statuses=status,
                excluded_statuses=exclude_status,
            )
        )

    return BacklogItemListResponse(
        project=project_response(backlog.project),
        items=items,
        count=len(items),
    )


@router.get(
    "/backlogs/{project_title}/items/{item_id}",
    response_model=BacklogItemResponse,
    dependencies=[REQUIRE_BACKLOG_READ],
    tags=["backlog reads"],
)
def describe_item(
    project_title: str,
    item_id: str,
    context: ProviderContextDependency,
) -> BacklogItemResponse:
    backlog = _load_backlog(project_title, context)
    item = find_backlog_item(backlog, item_id)
    parent_epic_id = (
        find_parent_epic(backlog, item.id).id if isinstance(item, Issue) else None
    )
    return item_response(item, parent_epic_id=parent_epic_id)


@router.post(
    "/backlogs/{project_title}/epics",
    response_model=ItemMutationResponse,
    dependencies=[REQUIRE_BACKLOG_WRITE],
    tags=["backlog mutations"],
)
def create_epic(
    project_title: str,
    request: CreateEpicRequest,
    response: Response,
    context: ProviderContextDependency,
) -> ItemMutationResponse:
    workflow = (
        preview_create_epic_in_postgres
        if request.mode is ExecutionMode.DRY_RUN
        else create_epic_in_postgres
    )
    epic = workflow(
        provider=context.provider,
        provider_account_username=context.provider_account_username,
        provider_project_title=project_title,
        title=request.title,
        repository_name=request.repository,
        epic_id=request.id,
        description=request.description,
        acceptance_criteria=request.acceptance_criteria,
        database_url=None,
    )
    committed = request.mode is ExecutionMode.CONFIRMED
    if committed:
        response.status_code = 201
    return ItemMutationResponse(
        mode=request.mode,
        committed=committed,
        item=item_response(epic, include_children=False),
    )


@router.post(
    "/backlogs/{project_title}/issues",
    response_model=ItemMutationResponse,
    dependencies=[REQUIRE_BACKLOG_WRITE],
    tags=["backlog mutations"],
)
def create_issue(
    project_title: str,
    request: CreateIssueRequest,
    response: Response,
    context: ProviderContextDependency,
) -> ItemMutationResponse:
    if request.mode is ExecutionMode.DRY_RUN:
        issue = preview_create_issue_in_postgres(
            provider=context.provider,
            provider_account_username=context.provider_account_username,
            provider_project_title=project_title,
            parent_epic_id=request.parent_epic_id,
            title=request.title,
            issue_id=request.id,
            description=request.description,
            repository_name=request.repository,
            acceptance_criteria=request.acceptance_criteria,
            database_url=None,
        )
        committed = False
    else:
        issue, _parent = create_issue_in_postgres(
            provider=context.provider,
            provider_account_username=context.provider_account_username,
            provider_project_title=project_title,
            parent_epic_id=request.parent_epic_id,
            title=request.title,
            issue_id=request.id,
            description=request.description,
            repository_name=request.repository,
            acceptance_criteria=request.acceptance_criteria,
            database_url=None,
        )
        committed = True
        response.status_code = 201

    return ItemMutationResponse(
        mode=request.mode,
        committed=committed,
        item=item_response(issue, parent_epic_id=request.parent_epic_id),
        parent_epic_id=request.parent_epic_id,
    )


@router.patch(
    "/backlogs/{project_title}/items/{item_id}",
    response_model=ItemMutationResponse,
    dependencies=[REQUIRE_BACKLOG_WRITE],
    tags=["backlog mutations"],
)
def update_item(
    project_title: str,
    item_id: str,
    request: UpdateBacklogItemRequest,
    context: ProviderContextDependency,
) -> ItemMutationResponse:
    workflow = (
        preview_update_item_in_postgres
        if request.mode is ExecutionMode.DRY_RUN
        else update_item_in_postgres
    )
    item = workflow(
        provider=context.provider,
        provider_account_username=context.provider_account_username,
        provider_project_title=project_title,
        item_id=item_id,
        title=request.title,
        description=request.description,
        status=request.status,
        acceptance_criteria=request.acceptance_criteria,
        comment=request.comment,
        database_url=None,
    )
    return ItemMutationResponse(
        mode=request.mode,
        committed=request.mode is ExecutionMode.CONFIRMED,
        item=item_response(item, include_children=False),
    )


@router.post(
    "/backlogs/{project_title}/issues/{issue_id}/move",
    response_model=MoveIssueResponse,
    dependencies=[REQUIRE_BACKLOG_WRITE],
    tags=["backlog mutations"],
)
def move_issue(
    project_title: str,
    issue_id: str,
    request: MoveIssueRequest,
    context: ProviderContextDependency,
) -> MoveIssueResponse:
    workflow = (
        preview_move_issue_in_postgres
        if request.mode is ExecutionMode.DRY_RUN
        else move_issue_in_postgres
    )
    issue, source_epic, target_epic = workflow(
        provider=context.provider,
        provider_account_username=context.provider_account_username,
        provider_project_title=project_title,
        issue_id=issue_id,
        target_epic_id=request.target_epic_id,
        database_url=None,
    )
    return MoveIssueResponse(
        mode=request.mode,
        committed=request.mode is ExecutionMode.CONFIRMED,
        item=item_response(issue, parent_epic_id=target_epic.id),
        source_epic=item_summary_response(source_epic),
        target_epic=item_summary_response(target_epic),
    )


@router.delete(
    "/backlogs/{project_title}/issues/{issue_id}",
    response_model=DeleteIssueResponse,
    dependencies=[REQUIRE_BACKLOG_WRITE],
    tags=["backlog mutations"],
)
def delete_issue(
    project_title: str,
    issue_id: str,
    mode: Annotated[
        ExecutionMode,
        Query(description="Preview or confirm the deletion."),
    ],
    context: ProviderContextDependency,
) -> DeleteIssueResponse:
    workflow = (
        preview_delete_issue_in_postgres
        if mode is ExecutionMode.DRY_RUN
        else delete_issue_in_postgres
    )
    result = workflow(
        provider=context.provider,
        provider_account_username=context.provider_account_username,
        provider_project_title=project_title,
        issue_id=issue_id,
        database_url=None,
    )
    return DeleteIssueResponse(
        mode=mode,
        committed=mode is ExecutionMode.CONFIRMED,
        issue=item_response(result.issue, parent_epic_id=result.parent_epic.id),
        parent_epic=item_summary_response(result.parent_epic),
        github_issue_deleted=(
            result.github_issue_deleted if mode is ExecutionMode.CONFIRMED else None
        ),
    )


@router.post(
    "/backlogs/{project_title}/reconciliation",
    response_model=ReconcileResponse,
    dependencies=[REQUIRE_BACKLOG_OPERATE],
    tags=["projection operations"],
)
def reconcile(
    project_title: str,
    request: ReconcileRequest,
    context: ProviderContextDependency,
) -> ReconcileResponse:
    kwargs = {
        "provider": context.provider,
        "provider_account_username": context.provider_account_username,
        "provider_project_title": project_title,
        "max_operations": request.operation_limit,
        "database_url": None,
    }
    if request.mode is ExecutionMode.DRY_RUN:
        preview = preview_reconcile_backlog_from_postgres(**kwargs)
        executed_group_count = 0
        hydrated_item_count = 0
        committed = False
    else:
        result = reconcile_backlog_from_postgres(**kwargs)
        preview = result.preview
        executed_group_count = result.executed_group_count
        hydrated_item_count = result.hydrated_item_count
        committed = True

    return ReconcileResponse(
        mode=request.mode,
        committed=committed,
        operations=[
            reconcile_operation_response(operation)
            for operation in preview.execution_plan.operations
        ],
        total_operation_count=preview.total_operation_count,
        execution_operation_count=preview.execution_operation_count,
        remaining_operation_count=preview.remaining_operation_count,
        executed_group_count=executed_group_count,
        hydrated_item_count=hydrated_item_count,
        complete=preview.remaining_operation_count == 0,
    )


@router.post(
    "/backlogs/{project_title}/purge",
    response_model=PurgeResponse,
    dependencies=[REQUIRE_BACKLOG_ADMIN],
    tags=["projection operations"],
)
def purge(
    project_title: str,
    request: PurgeRequest,
    context: ProviderContextDependency,
) -> PurgeResponse:
    workflow = (
        preview_purge_backlog_projection
        if request.mode is ExecutionMode.DRY_RUN
        else purge_backlog_projection_from_postgres
    )
    result = workflow(
        provider=context.provider,
        provider_account_username=context.provider_account_username,
        provider_project_title=project_title,
        max_issues=request.issue_limit,
        database_url=None,
    )
    return PurgeResponse(
        mode=request.mode,
        committed=request.mode is ExecutionMode.CONFIRMED,
        project_title=result.project_title,
        issues=[purge_issue_response(issue) for issue in result.issues],
        total_issue_count=result.total_issue_count,
        selected_issue_count=len(result.issues),
        deleted_issue_count=result.deleted_issue_count,
        remaining_issue_count=result.remaining_issue_count,
        cleared_item_count=result.cleared_item_count,
        projection_metadata_cleared=result.projection_metadata_cleared,
        complete=result.remaining_issue_count == 0,
    )


@router.post(
    "/backlogs/import",
    response_model=BacklogImportResponse,
    dependencies=[REQUIRE_BACKLOG_ADMIN],
    tags=["portable YAML boundary"],
)
def import_backlog(
    backlog_yaml: Annotated[
        str,
        Body(
            media_type="application/yaml",
            description="Canonical backlog v1 YAML document.",
        ),
    ],
    mode: Annotated[
        ExecutionMode,
        Query(description="Preview or confirm the snapshot replacement."),
    ],
    provider_account_username: Annotated[
        str,
        Query(alias="provider_account"),
    ] = DEFAULT_PROVIDER_ACCOUNT_USERNAME,
    user_display_name: Annotated[str, Query()] = "Grant Gortsema",
    user_primary_email: Annotated[str | None, Query()] = None,
    verify: Annotated[bool, Query()] = True,
) -> BacklogImportResponse:
    backlog = _parse_backlog_document(backlog_yaml)
    summary = summarize_backlog(backlog)
    verified: bool | None = None

    if mode is ExecutionMode.CONFIRMED:
        result = import_backlog_to_postgres(
            backlog=backlog,
            user_display_name=user_display_name,
            user_primary_email=user_primary_email,
            provider_account_username=provider_account_username,
            provider_account_display_name=user_display_name,
            database_url=None,
            verify=verify,
        )
        verified = result.verified

    return BacklogImportResponse(
        mode=mode,
        committed=mode is ExecutionMode.CONFIRMED,
        project=project_response(backlog.project),
        provider_account_username=provider_account_username,
        epic_count=summary.epic_count,
        issue_count=summary.issue_count,
        acceptance_criterion_count=summary.acceptance_criterion_count,
        comment_count=summary.comment_count,
        label_count=summary.label_count,
        assignee_count=summary.assignee_count,
        verified=verified,
    )


@router.get(
    "/backlogs/{project_title}/export",
    response_class=Response,
    responses={
        200: {
            "content": {"application/yaml": {}},
            "description": "Portable canonical backlog YAML snapshot",
        }
    },
    dependencies=[REQUIRE_BACKLOG_READ],
    tags=["portable YAML boundary"],
)
def export_backlog(
    project_title: str,
    context: ProviderContextDependency,
) -> Response:
    result = export_backlog_yaml_text_from_postgres(
        provider=context.provider,
        provider_account_username=context.provider_account_username,
        provider_project_title=project_title,
        database_url=None,
    )
    return Response(
        content=result.content,
        media_type="application/yaml",
        headers={
            "Content-Disposition": 'attachment; filename="backlog.yml"',
            "X-Johnny-Epic-Count": str(result.epic_count),
            "X-Johnny-Issue-Count": str(result.issue_count),
            "X-Johnny-Comment-Count": str(result.comment_count),
        },
    )


def _load_backlog(project_title: str, context: ProviderContext):
    return load_backlog_from_postgres(
        provider=context.provider,
        provider_account_username=context.provider_account_username,
        provider_project_title=project_title,
        database_url=None,
    )


def _parse_backlog_document(backlog_yaml: str):
    try:
        return load_backlog_yaml_text(backlog_yaml)
    except Exception as exc:
        raise BacklogDocumentError(str(exc)) from exc
