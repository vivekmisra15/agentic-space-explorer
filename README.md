# Agentic Space Explorer — from First Principles

Agentic Space Explorer is a **framework-free agentic AI system** built from first principles to explore how multi-step AI workflows actually work under the hood.

Instead of relying on agent frameworks or orchestration libraries, this project **implements the core building blocks explicitly** — shared state, tools, orchestration, and logging — to make agentic behavior **transparent, debuggable, and understandable**.

The domain is space missions (because it's fun and concrete), but the real goal is learning:
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

By removing framework "magic," the architecture becomes explicit — and therefore transferable to any runtime (Google ADK, LangGraph, custom infra, etc.).

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

## Running the App

```bash
# Set up environment
python3.13 -m venv venv
venv/bin/pip install -r requirements.txt

# Add your Gemini API key
cp .env.example .env   # then fill in GEMINI_API_KEY

# Launch the Streamlit UI
venv/bin/streamlit run app.py
```

---

## High-Level Architecture

The system is organized around a small set of explicit roles:

### Supervisor
- Owns the run lifecycle
- Initializes shared state
- Orchestrates agents deterministically
- Logs lifecycle milestones

### Agents

Three specialist agents run in sequence. Each reads from and writes to shared state; none call each other directly.

**DataEngineer** — loads the raw CSV (with multi-encoding fallback: UTF-8 → cp1252 → latin-1), derives enriched columns (`Year`, `Decade`, `Success`, `EnrichedAtUnix`), and writes two versioned files to `data/`.

**Analyst** — two-phase LLM planner and executor. First, it sends a prompt to Gemini along with the full tool registry; Gemini returns a JSON step-by-step plan. Then the agent validates and executes each step using 11 deterministic tools. Outputs include aggregation tables, four chart types (PNG + interactive Plotly sidecar), and a markdown report — all written to `reports/`.

**EvalAgent** — runs 10 deterministic checks (files exist, ≥3 plots, time-scoped questions used `filter_year_range`, etc.), then sends the full context to Gemini for an LLM critique. Writes `eval.md` and a structured JSON file to `reports/evals/`.

### Tools
- Deterministic, side-effecting functions
- One clear purpose per tool
- Return references (paths, IDs), not large objects
- 11 tools covering: data inspection, aggregation, filtering, four chart types, and report writing

### Shared State
- A minimal, explicit contract between steps
- Only contains paths and IDs — never large objects
- Designed for introspection, replay, and debugging

### Logs
- Human-readable execution trace
- Six event types: `run.start/end`, `agent.start/end`, `tool.start/end`, `llm.call/response`, `state.update`, `error`
- Observation only — no logic reads from them

---

## User Interface

The Streamlit app (`app.py`) renders results in a **three-tab layout** after each run:

- **Insights** — supervisor overview, key highlights in a two-column card grid, interactive chart gallery (click a thumbnail to expand a full Plotly chart)
- **Report** — full analysis markdown with business-friendly table and column descriptions injected inline
- **Evaluation & Debug** — pass/fail eval banner, issues list, raw developer artifact view

The UI uses a space-themed dark design with a nebula gradient background, Orbitron/Inter fonts, and subtle hover animations throughout.

---

## Data Flow

1. User types a natural language question in the Streamlit UI
2. Supervisor initializes a new run and shared state dict
3. **DataEngineer** loads and enriches the CSV; writes data files; stores paths in state
4. **Analyst** asks Gemini to plan a tool sequence, then executes it step-by-step; generates charts, tables, and a markdown report
5. **EvalAgent** runs deterministic checks and an LLM critique; writes `eval.md`
6. Supervisor appends a final summary message to state
7. Streamlit renders results across the three tabs

At every step, the system remains inspectable.

---

## Project Status & Roadmap

### MVP 1 — Framework-Free Agentic Core ✅ Complete

- ✅ Repository structure & environment setup
- ✅ Deterministic data tools (load + feature engineering)
- ✅ LLM backend abstraction (Gemini, model-agnostic interface)
- ✅ Supervisor orchestration loop
- ✅ Explicit shared state contract
- ✅ Diff-based state update logging
- ✅ DataEngineer agent (CSV load, encoding fallback, feature engineering)
- ✅ Analyst agent (LLM planner + 11-tool executor, charts, markdown report)
- ✅ EvalAgent (10 deterministic checks + LLM critique)
- ✅ Streamlit UI (3-tab layout, interactive Plotly charts, space-themed design)

**Current status:**
> MVP 1 is complete and running end-to-end.
> The full pipeline — from user query through data engineering, analysis, evaluation, and UI rendering — is operational.

---

## Relationship to Google ADK (Future Work)

This architecture is deliberately designed to map cleanly onto Google ADK concepts:

- Supervisor → root / coordinator agent
- Agents → specialized ADK agents
- Tools → ADK tool functions
- State → InvocationContext / run-scoped data
- Logs → traces + UI-friendly events

A **follow-up repository** will implement the same workflow using ADK primitives, allowing a direct comparison between:
- "from-scratch agentic systems"
- "framework-powered agentic systems"

---

## Who This Is For

- Developers learning how agentic systems actually work
- Practitioners evaluating agent frameworks
- People who want to debug and reason about AI workflows
- Anyone curious about AI orchestration beyond single prompts

If you're looking for a polished product demo, this isn't it.
If you want to **understand agentic AI**, you're in the right place.

---

## Documentation

- `docs/key-considerations.md` — architectural philosophy and design choices
- `docs/key-considerations-state.md` — state management and logging mechanics

---

## Disclaimer

This is an educational MVP, not a production system.

Clarity, observability, and learning are prioritized over abstraction and optimization.
