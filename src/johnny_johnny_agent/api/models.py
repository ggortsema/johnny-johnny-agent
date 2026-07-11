"""Typed HTTP contracts for the Johnny-Johnny REST API."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ApiModel(BaseModel):
    """Base model with strict, predictable request parsing."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


class ExecutionMode(StrEnum):
    DRY_RUN = "dry-run"
    CONFIRMED = "confirmed"


class ServiceStatusResponse(ApiModel):
    service: str
    version: str
    status: str


class ServiceReadinessResponse(ApiModel):
    service: str
    version: str
    status: str
    checks: dict[str, str]


class AuthenticatedPrincipalResponse(ApiModel):
    subject: str
    client_id: str | None = None
    scopes: list[str]


class AssistantResponseRequest(ApiModel):
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def require_non_blank_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Text must contain at least one non-whitespace character.")
        return text


class TokenUsageResponse(ApiModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class AssistantResponsePayload(ApiModel):
    response_id: str
    text: str
    model: str
    usage: TokenUsageResponse


class ProjectResponse(ApiModel):
    provider: str
    title: str
    number: int | None = None
    url: str | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class CommentResponse(ApiModel):
    id: str
    body: str
    source: str
    created_at: str | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class BacklogItemSummaryResponse(ApiModel):
    id: str
    type: str
    title: str
    repository: str
    status: str
    issue_state: str
    order: int
    parent_epic_id: str | None = None
    issue_count: int | None = None


class BacklogItemResponse(ApiModel):
    id: str
    type: str
    title: str
    repository: str
    status: str
    issue_state: str
    order: int
    description: str
    acceptance_criteria: list[str]
    comments: list[CommentResponse]
    labels: list[str]
    assignees: list[str]
    milestone: str | None = None
    provider_metadata: dict[str, Any]
    parent_epic_id: str | None = None
    issues: list["BacklogItemResponse"] = Field(default_factory=list)


class BacklogSummaryResponse(ApiModel):
    project: ProjectResponse
    epic_count: int
    issue_count: int
    acceptance_criterion_count: int
    comment_count: int
    label_count: int
    assignee_count: int


class BacklogItemListResponse(ApiModel):
    project: ProjectResponse
    items: list[BacklogItemSummaryResponse]
    count: int


class MutationRequest(ApiModel):
    mode: ExecutionMode


class CreateEpicRequest(MutationRequest):
    id: str | None = None
    title: str = Field(min_length=1)
    repository: str = Field(min_length=1)
    description: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)


class CreateIssueRequest(MutationRequest):
    id: str | None = None
    parent_epic_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    repository: str | None = None
    description: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)


class UpdateBacklogItemRequest(MutationRequest):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    acceptance_criteria: list[str] | None = None
    comment: str | None = None

    @model_validator(mode="after")
    def require_change(self) -> "UpdateBacklogItemRequest":
        if not any(
            value is not None
            for value in (
                self.title,
                self.description,
                self.status,
                self.acceptance_criteria,
                self.comment,
            )
        ):
            raise ValueError("At least one backlog item change is required.")
        return self


class MoveIssueRequest(MutationRequest):
    target_epic_id: str = Field(min_length=1)


class ItemMutationResponse(ApiModel):
    mode: ExecutionMode
    committed: bool
    item: BacklogItemResponse
    parent_epic_id: str | None = None


class MoveIssueResponse(ApiModel):
    mode: ExecutionMode
    committed: bool
    item: BacklogItemResponse
    source_epic: BacklogItemSummaryResponse
    target_epic: BacklogItemSummaryResponse


class DeleteIssueResponse(ApiModel):
    mode: ExecutionMode
    committed: bool
    issue: BacklogItemResponse
    parent_epic: BacklogItemSummaryResponse
    github_issue_deleted: bool | None = None


class ReconcileRequest(MutationRequest):
    max_operations: int | None = Field(default=None, ge=1)
    all_operations: bool = Field(default=False, alias="all")

    @model_validator(mode="after")
    def validate_scope(self) -> "ReconcileRequest":
        if self.all_operations and self.max_operations is not None:
            raise ValueError("Use either all or max_operations, not both.")
        return self

    @property
    def operation_limit(self) -> int | None:
        return None if self.all_operations else (self.max_operations or 100)


class ReconcileOperationResponse(ApiModel):
    kind: str
    item_id: str
    title: str
    parent_epic_id: str | None = None
    comment_id: str | None = None
    current_status: str | None = None
    desired_status: str | None = None


class ReconcileResponse(ApiModel):
    mode: ExecutionMode
    committed: bool
    operations: list[ReconcileOperationResponse]
    total_operation_count: int
    execution_operation_count: int
    remaining_operation_count: int
    executed_group_count: int
    hydrated_item_count: int
    complete: bool


class PurgeRequest(MutationRequest):
    max_issues: int | None = Field(default=None, ge=1)
    all_issues: bool = Field(default=False, alias="all")

    @model_validator(mode="after")
    def validate_scope(self) -> "PurgeRequest":
        if self.all_issues and self.max_issues is not None:
            raise ValueError("Use either all or max_issues, not both.")
        return self

    @property
    def issue_limit(self) -> int | None:
        return None if self.all_issues else (self.max_issues or 50)


class PurgeIssueResponse(ApiModel):
    id: str | None = None
    number: int | None = None
    title: str | None = None
    url: str | None = None


class PurgeResponse(ApiModel):
    mode: ExecutionMode
    committed: bool
    project_title: str
    issues: list[PurgeIssueResponse]
    total_issue_count: int
    selected_issue_count: int
    deleted_issue_count: int
    remaining_issue_count: int
    cleared_item_count: int
    projection_metadata_cleared: bool
    complete: bool


class BacklogImportResponse(ApiModel):
    mode: ExecutionMode
    committed: bool
    project: ProjectResponse
    provider_account_username: str
    epic_count: int
    issue_count: int
    acceptance_criterion_count: int
    comment_count: int
    label_count: int
    assignee_count: int
    verified: bool | None = None


class ErrorDetail(ApiModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(ApiModel):
    error: ErrorDetail
