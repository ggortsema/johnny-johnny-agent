# Johnny-Johnny Agent

Johnny-Johnny Agent is the Python runtime for **Johnny-Johnny**, a
personal engineering assistant designed to help automate software
engineering work.

Johnny-Johnny is **not** a chatbot. Conversations are simply one
interface to a growing collection of reusable engineering capabilities.

Its long-term purpose is to become an engineering companion capable of
helping with project management, documentation, GitHub, email,
scheduling, job searches, knowledge management, and future AI-assisted
workflows.

------------------------------------------------------------------------

# Vision

Johnny-Johnny is built around a few core principles:

-   Build reusable capabilities before user interfaces.
-   Treat the CLI as the primary public interface.
-   Keep business logic independent from presentation layers.
-   Prefer deterministic workflows whenever possible.
-   Use AI where reasoning adds value.
-   Make every capability reusable from:
    -   CLI
    -   FastAPI
    -   Future chat interfaces
    -   LangGraph
    -   Future desktop/web applications

------------------------------------------------------------------------

# Current Capability

## Backlog-as-Code

The first capability is a complete **Backlog-as-Code** engine.

The canonical Source of Truth (SSOT) is:

    backlog.yml

GitHub Projects are treated as a **projection** of the canonical
backlog.

    backlog.yml
          │
          ▼
    Validate
          ▼
    Canonical Domain Model
          ▼
    Planner
          ▼
    Execution Plan
          ▼
    GitHub Projection

GitHub is **never** the authoritative data source.

------------------------------------------------------------------------

# Current CLI

## API

``` bash
jj serve
```

Starts the FastAPI server.

------------------------------------------------------------------------

## Validate

``` bash
jj backlog validate \
  --file data/input/backlog/backlog-v1-from-github.yml
```

Validates the canonical backlog against the JSON schema.

------------------------------------------------------------------------

## Inspect

``` bash
jj backlog inspect \
  --file data/input/backlog/backlog-v1-from-github.yml
```

Loads the canonical backlog and displays a summary.

------------------------------------------------------------------------

## Pull

``` bash
jj backlog pull \
  --project "MycroftAI Engineering Roadmap"
```

Exports the current GitHub Project projection as JSON.

Information includes:

-   Project metadata
-   Issue metadata
-   Issue body
-   Johnny metadata
-   Labels
-   Assignees
-   Milestones
-   Repository
-   Timestamps

------------------------------------------------------------------------

## Reconcile

Preview:

``` bash
jj backlog reconcile \
  --file data/input/backlog/backlog-v1-from-github.yml \
  --dry-run
```

Execute:

``` bash
jj backlog reconcile \
  --file data/input/backlog/backlog-v1-from-github.yml \
  --confirm
```

The reconciliation planner currently performs:

-   Create epics
-   Create issues
-   Attach sub-issues
-   Populate GitHub Project

------------------------------------------------------------------------

## Purge

Preview:

``` bash
jj backlog purge \
  --project "MycroftAI Engineering Roadmap"
```

Execute:

``` bash
jj backlog purge \
  --project "MycroftAI Engineering Roadmap" \
  --confirm
```

Only Johnny-managed issues containing the hidden metadata block are
removed.

------------------------------------------------------------------------

# Current Architecture

    src/
        johnny_johnny_agent/
            api/
            cli/
            domain/
            capabilities/
                backlog_sync/
                github/

Current backlog synchronization consists of:

-   Canonical domain model
-   YAML loader
-   JSON Schema validation
-   Planner
-   GitHub renderer
-   GitHub executor
-   Pull/export
-   Purge

------------------------------------------------------------------------

# Planned Capabilities

Johnny-Johnny will continue to grow through independent capabilities.

Current roadmap includes:

-   Backlog-as-Code
-   GitHub automation
-   Gmail integration
-   Calendar integration
-   Documentation generation
-   Resume management
-   Job search helpers
-   Knowledge management
-   Retrieval-Augmented Generation (RAG)
-   Long-term memory
-   Engineering workflow automation

------------------------------------------------------------------------

# Relationship to the Ecosystem

    MycroftAI
    │
    ├── StyxCD
    │      └── Kharon
    │
    └── Johnny-Johnny

## MycroftAI

The company.

Owns products and internal engineering tools.

## StyxCD

A deterministic software delivery platform focused on workflow planning,
deployment orchestration, and operational visibility.

## Kharon

The AI assistant for StyxCD.

Kharon understands StyxCD workflows, documentation, deployment
architecture, and operational concepts.

## Johnny-Johnny

A personal engineering assistant.

Johnny helps engineers---not just StyxCD.

Examples:

-   Manage backlogs
-   Synchronize GitHub
-   Read and summarize Gmail
-   Update resumes
-   Search for jobs
-   Organize engineering knowledge
-   Automate repetitive workflows

Johnny serves the engineer.

Kharon serves StyxCD.

------------------------------------------------------------------------

# Development Philosophy

The project intentionally grows through small, validated vertical
slices.

Every capability follows the same pattern:

    CLI
        ↓
    Application Service
        ↓
    Domain Model
        ↓
    Provider Adapter

Provider-specific implementation details remain behind adapters while
the public interface remains stable.

------------------------------------------------------------------------

# Current Status

Johnny-Johnny has successfully completed its first major milestone:

-   Canonical backlog model
-   GitHub projection
-   Full reconciliation workflow
-   Provider export
-   Safe purge
-   FastAPI interface
-   Typer CLI

The next milestone is **safe mutation of the canonical backlog**,
allowing engineers to add, update, and reorganize work by editing the
SSOT and reconciling the provider projection.

------------------------------------------------------------------------

# License

TBD
