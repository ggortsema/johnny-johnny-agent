# ADR-003: REST API Is a Peer Adapter Over Application Workflows

**Status:** Accepted
**Date:** July 10, 2026
**Story:** `expose-backlog-workflows-through-rest-api`

## Context

Johnny-Johnny needs a server-mode interface for automation, future UI clients, webhooks, and chat integrations. The existing CLI already exposes PostgreSQL-backed backlog reads, targeted mutations, reconciliation, purge, and YAML import/export.

Implementing REST by invoking CLI commands would couple server behavior to terminal rendering, exit codes, process execution, and CLI-only option parsing. Reimplementing the business logic in HTTP handlers would create divergent persistence and provider-consistency behavior.

The server also needs an explicit, machine-readable distinction between preview and committing mutations.

## Decision

The versioned REST API at `/api/v1` is a peer presentation adapter to the CLI.

```text
CLI request ──┐
              ├── shared application workflow ── canonical domain
HTTP request ─┘              │
                             ├── PostgreSQL repository
                             └── provider adapter
```

REST handlers import and call the existing application workflows directly. They never shell out to `jj`.

### Typed Contracts

Requests and responses use explicit Pydantic models. Backlog items, comments, reconcile operations, purge scope, database readiness, and errors have stable JSON representations visible through OpenAPI.

### Explicit Mutation Mode

Every mutation declares one of:

```text
dry-run
confirmed
```

`dry-run` calls the preview workflow. `confirmed` calls the committing workflow. There is no implicit committing default.

### Location and Configuration

The HTTP path contains the stored provider project title. Query parameters select provider and provider account. The server resolves `DATABASE_URL` from its own environment; HTTP clients cannot supply database credentials or topology.

### Portable YAML Boundary

YAML import accepts an `application/yaml` request body. YAML export returns `application/yaml`. Normal runtime reads and mutations remain PostgreSQL-backed and do not use YAML as an intermediary.

### Security Boundary

The HTTP adapter authenticates Auth0 bearer access tokens and enforces route scopes before calling an application workflow. The security dependency belongs to the presentation boundary; the canonical domain and shared workflows remain identity-provider independent. Public health probes are minimal, and tests inject a verifier through the application factory rather than enabling a runtime bypass. See ADR-005.

### Error Mapping

Application and adapter failures map to one error envelope and stable status categories:

- invalid request
- not found
- conflict
- domain/document validation
- provider failure
- persistence unavailable
- cross-boundary consistency failure

### Synchronous Baseline

The v1 endpoints are synchronous because the underlying workflows are synchronous. Reconcile and purge retain bounded and full execution controls. Durable asynchronous operation resources remain a future evolution.

## Consequences

### Positive

- CLI and REST preserve one set of domain and consistency semantics.
- OpenAPI documents a machine-readable integration contract.
- Preview versus commit is explicit for automation clients.
- The server cannot be used to redirect database connectivity through request data.
- YAML remains an explicit exchange boundary.

### Costs

- Long reconcile and purge requests hold an HTTP connection until the bounded workflow completes.
- Protected routes now depend on Auth0 issuer-key availability when a required key is not cached.
- Provider-specific failures still originate in the provider adapter and require careful stable HTTP classification.
- Breaking v1 contract changes require an explicit versioning decision.

## Alternatives Rejected

### Shell out to the CLI

Rejected because process execution, terminal output, and exit-code parsing are not an application interface and would duplicate transport concerns.

### Duplicate workflow logic in route handlers

Rejected because it would allow CLI and REST behavior to diverge across PostgreSQL transactions, GitHub synchronization, compensation, and retry semantics.

### Implicitly commit based on HTTP method

Rejected because users and automation need an explicit preview/confirmation contract, especially for delete, import, reconcile, and purge.
