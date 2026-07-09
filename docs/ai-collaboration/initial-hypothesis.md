# Initial Hypothesis

## Background

This repository began as an engineering project.

Over time, an unexpected pattern emerged.

Many of the practices that made development more effective were not improvements to the software itself, but improvements to the collaboration between the human engineer and the AI assistant.

These practices were discovered through repeated engineering work rather than designed up front.

This document captures the initial hypothesis that may eventually grow into a more formal body of knowledge.

---

## Initial Hypothesis

Effective collaboration with AI is less about prompt engineering and more about engineering shared context.

As projects become larger and longer lived, the quality of collaboration depends increasingly on establishing shared context, preserving engineering decisions, and maintaining continuity across sessions.

Prompting remains important, but prompts become significantly less important as shared context increases.

---

## Observation

Most discussions around AI focus on this model:

```text
Human
    ↓
Prompt
    ↓
AI
    ↓
Answer
```

Our experience has been different.

The collaboration has gradually evolved into something closer to:

```text
Working Agreement
        ↓
Engineering Principles
        ↓
Current Story
        ↓
Shared Domain Model
        ↓
Tests
        ↓
Implementation
        ↓
Documentation
        ↓
Session Wrap-Up / Handoff
```

The prompt becomes only one small part of a much larger engineering process.

---

## Working Hypothesis

The primary challenge of long-term AI collaboration is not generating code.

It is establishing, maintaining, and evolving shared engineering context.

Examples include:

- Working agreements
- Engineering principles
- Domain language
- Architecture decisions
- Testing strategy
- Documentation
- Session continuity
- Handoffs
- Project history

These artifacts reduce communication overhead in much the same way that shared practices improve collaboration on high-performing engineering teams.

---

## Emerging Principle

Instead of asking:

> "How do I write better prompts?"

A more valuable question may be:

> "How do we build and preserve better shared context?"

---

## AI Collaboration Engineering

One possible name for this emerging discipline is:

**AI Collaboration Engineering**

Possible areas of study include:

- Establishing shared context
- Working agreements
- Session lifecycle
- Engineering rituals
- Documentation strategy
- Testing with AI
- Architecture discussions
- Context preservation
- Handoff strategies
- Division of responsibilities between human and AI

Whether this becomes a distinct discipline remains to be seen.

For now, it remains a hypothesis worth exploring.

---

## Goal

This folder documents observations made while building real software.

Rather than beginning with a predefined methodology, it captures practices that repeatedly prove valuable during day-to-day engineering work.

Only ideas that continue to demonstrate practical value should become part of the evolving collaboration model.