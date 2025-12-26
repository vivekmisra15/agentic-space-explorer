# Agentic Space Explorer — from First Principles

Agentic Space Explorer is a **framework-free agentic AI system** built from first principles to explore how multi-step AI workflows actually work under the hood.

Instead of relying on agent frameworks or orchestration libraries, this project **implements the core building blocks explicitly** — shared state, tools, orchestration, and logging — to make agentic behavior **transparent, debuggable, and understandable**.

The domain is space missions (because it’s fun and concrete), but the real goal is learning:  
to understand what makes an AI system *agentic* before introducing frameworks.

---

## Why This Project Exists

Most agent frameworks abstract away the hardest parts:

- How state is shared across steps
- How agents coordinate deterministically
- How to log and debug long-running workflows
- How tools mutate the world safely
- How to reason about failures and partial progress

This project asks a different question:

> **What does an agentic system look like if you build it yourself?**

By removing framework “magic,” the architecture becomes explicit — and therefore transferable to any runtime (Google ADK, LangGraph, custom infra, etc.).

---

## Why No Framework (Yet)?

This repository is **intentionally framework-free**.

That is a feature, not a limitation.

Design goals:
- Make agent behavior observable and explainable
- Control shared state explicitly
- Produce UI-friendly, human-readable logs
- Avoid hidden lifecycle hooks or implicit state
- Create a clear mental model that survives framework changes

Frameworks like **Google ADK** are excellent — but they are most valuable **after** you understand the primitives they orchestrate.

A follow-up repository will re-implement this same architecture using ADK primitives.

---

## High-Level Architecture

The system is organized around a small set of explicit roles:

### Supervisor
- Owns the run lifecycle
- Initializes shared state
- Orchestrates agents deterministically
- Logs lifecycle milestones

### Agents
- Specialists that operate on shared state
- Each agent has a single responsibility
- Agents do not call each other directly

### Tools
- Deterministic, side-effecting functions
- One clear purpose per tool
- Return references (paths, IDs), not large objects

### Shared State
- A minimal, explicit contract between steps
- Only contains data that multiple agents depend on
- Designed for introspection, replay, and debugging

### Logs
- Human-readable execution trace
- Focused on lifecycle events, tool calls, and state changes
- Designed for future UI consumption

This separation keeps the system understandable as it grows.

---

## Data Flow (Conceptual)

1. User provides a natural language question
2. Supervisor creates a new run and shared state
3. Agents execute in sequence, enriching state
4. Tools fetch data and produce artifacts
5. State updates are logged with clear reasons
6. Final outputs are produced (reports, charts, etc.)

At every step, the system remains inspectable.

---

## Project Status & Roadmap

This project is being built incrementally in public.

### MVP 1 — Framework-Free Agentic Core (this repository)

**Goal:** demonstrate agentic workflows *from first principles*

Planned steps:
- ✅ Repository structure & environment setup
- ✅ Deterministic data tools (load + feature engineering)
- ✅ LLM backend abstraction
- ✅ Supervisor orchestration loop
- ✅ Explicit shared state contract
- ✅ Diff-based state update logging
- ⏳ DataEngineer agent (tool execution + state mutation)
- ⏳ Analyst agent (analysis & insight generation)
- ⏳ Storyteller agent (narrative + report generation)
- ⏳ Minimal UI (log viewer / report output)

**Current status:**  
> Core orchestration, state management, and logging are complete.  
> First agent implementation is in progress.

This status line is intentionally short and will be updated as the project evolves.

---

## Relationship to Google ADK (Future Work)

This architecture is deliberately designed to map cleanly onto Google ADK concepts:

- Supervisor → root / coordinator agent
- Agents → specialized ADK agents
- Tools → ADK tool functions
- State → InvocationContext / run-scoped data
- Logs → traces + UI-friendly events

A **follow-up repository** will implement the same workflow using ADK primitives, allowing a direct comparison between:
- “from-scratch agentic systems”
- “framework-powered agentic systems”

---

## Who This Is For

- Developers learning how agentic systems actually work
- Practitioners evaluating agent frameworks
- People who want to debug and reason about AI workflows
- Anyone curious about AI orchestration beyond single prompts

If you’re looking for a polished product demo, this isn’t it.  
If you want to **understand agentic AI**, you’re in the right place.

---

## Documentation

- `docs/key-considerations.md` — architectural philosophy and design choices
- `docs/key-considerations-state.md` — state management and logging mechanics

---

## Disclaimer

This is an educational MVP, not a production system.

Clarity, observability, and learning are prioritized over abstraction and optimization.

