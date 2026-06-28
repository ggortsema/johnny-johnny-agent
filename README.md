# Johnny-Johnny Agent

Johnny-Johnny Agent is the Python runtime for the Johnny-Johnny personal engineering assistant.

Its goal is to provide a growing collection of reusable services that help software engineers automate repetitive work, organize knowledge, manage projects, and interact with the tools they use every day.

Rather than being a traditional chatbot, Johnny-Johnny is intended to become an engineering utility capable of performing useful work through a collection of focused capabilities. Conversations are simply one interface to those capabilities.

---

## Vision

Johnny-Johnny is built around a few core principles:

- Build reusable services before user interfaces.
- Keep business logic independent from presentation layers.
- Prefer deterministic engineering workflows whenever possible.
- Use AI where reasoning adds value, not where deterministic solutions are more appropriate.
- Design capabilities that can be reused by humans, APIs, and autonomous workflows alike.

---

## Initial Capability

The first capability under development is **Backlog-as-Code Synchronization**.

The synchronization engine maintains a provider-independent canonical backlog model while supporting synchronization with project management platforms.

The initial provider is:

- GitHub Projects

Future providers may include:

- Jira
- Azure DevOps
- Bitbucket
- Linear

The long-term synchronization model is:

```text
Project Management Platform
            │
            ▼
    Canonical Backlog Model
            │
     ┌──────┼─────────┐
     ▼      ▼         ▼
backlog.yml backlog.md sync-report.md
            │
            ▼
 Provider Synchronization
```

---

## Planned Capabilities

Johnny-Johnny is intended to grow into a general-purpose engineering assistant with capabilities including:

- Backlog synchronization
- GitHub automation
- Documentation generation
- Gmail integration
- Calendar integration
- Knowledge management
- Retrieval-Augmented Generation (RAG)
- Long-term memory
- Planning and reasoning
- Engineering workflow automation
- Additional provider integrations

---

## Architecture

The project is built around reusable Python services.

Interfaces such as:

- Command-line tools
- FastAPI
- LangGraph
- Future desktop or web applications

consume the same service layer.

Keeping the business logic independent of any interface allows the same capabilities to be reused in multiple environments without duplication.

---

## Current Status

This repository has intentionally been restarted from a clean foundation.

The first milestone is to build the Backlog-as-Code synchronization engine as a standalone library before exposing it through APIs, command-line tools, or autonomous agents.

Development is intentionally incremental, with each capability validated before expanding into broader agent functionality.

---

## Relationship to StyxCD and Kharon

Johnny-Johnny is part of a broader engineering ecosystem, but each project has a distinct responsibility.

### StyxCD

StyxCD is a deterministic software delivery platform focused on workflow orchestration, application deployment, and operational visibility.

### Kharon

Kharon is an AI engineering assistant built specifically for StyxCD.

It helps users understand, operate, and troubleshoot StyxCD through context-aware documentation, planning, and operational guidance.

### Johnny-Johnny

Johnny-Johnny is a broader personal engineering assistant.

Rather than serving a single product, it provides reusable engineering capabilities that can interact with many different systems including GitHub, cloud providers, productivity tools, and StyxCD itself.

The relationship between the three projects can be viewed as:

```text
Johnny-Johnny
Personal Engineering Assistant
            │
            ▼
        Kharon
  StyxCD AI Assistant
            │
            ▼
        StyxCD
Deterministic Delivery Platform
```

---

## License

TBD
