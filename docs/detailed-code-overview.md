# Agentic Space Explorer — Detailed Code Overview

This document combines a beginner-friendly walkthrough of the codebase with a structured explanation of its key features, approach, architecture, and design considerations. It is intended as a single reference for anyone new to the project or returning after a break.

---

## 1. What Is This Project?

**Agentic Space Explorer** is a multi-agent data analysis system built from first principles — no agent framework, no hidden orchestration magic. You give it a natural language question about space missions (e.g. "Show me launch trends by decade"), and a pipeline of AI agents plans, executes, evaluates, and reports the answer.

The domain (space missions) is a vehicle for the real goal: **demonstrating how agentic AI systems actually work under the hood** — state sharing, tool execution, LLM planning, observability, and failure handling — before introducing any framework abstraction.

A follow-up repository will re-implement the same architecture using Google ADK primitives, enabling a direct comparison between "built from scratch" and "framework-powered" agentic systems.

---

## 2. Project Philosophy

Most agent frameworks abstract away the hardest parts: how state is shared across steps, how tools mutate the world safely, how to log and debug long-running workflows, and how to reason about partial failures. By removing that "magic," this project makes every moving part visible and therefore transferable.

The central design decision is:

> **The LLM only plans. Python executes.**

If an output must be correct (a number, a chart, a file), a deterministic Python function produces it. The LLM's job is solely to decide *what* steps to take, expressed as a JSON plan. It never touches data or files directly.

---

## 3. File and Folder Map

```
agentic-space-explorer/
│
├── supervisor.py              # Entry point. Orchestrates all agents.
├── llm_backend.py             # All Gemini API calls go through here.
│
├── core/
│   └── state.py               # Shared working memory between agents.
│
├── agents/
│   ├── data_engineer.py       # Loads and enriches the CSV data.
│   ├── analyst.py             # Plans analysis with LLM, then runs it.
│   └── eval_agent.py          # Checks whether the output is good.
│
├── tools/
│   ├── data_tools.py          # Load CSV, derive features (Year, Decade, etc.)
│   ├── analysis_tools.py      # 12 tools: group_count, plot_bar, write_markdown…
│   └── plan_runtime.py        # Validates and executes LLM-generated plans.
│
├── data/
│   ├── space_missions.csv             # 3700+ rows of raw mission data.
│   ├── space_missions_raw.csv         # UTF-8 normalized copy.
│   └── space_missions_enriched.csv    # With derived features added.
│
├── reports/                   # All generated output (plots, markdown, eval).
│   ├── plans/                 # Saved analysis plans (JSON).
│   ├── plots/                 # Generated visualizations (PNG).
│   └── eval_*.json            # Evaluation metadata per run.
│
└── docs/                      # Human-facing design documents (not loaded at runtime).
```

---

## 4. Role of Each Main File

| File | Role |
|---|---|
| `supervisor.py` | The conductor. Calls agents in order, holds the run lifecycle. |
| `llm_backend.py` | Thin wrapper around Google Gemini. Agents never touch the SDK directly. |
| `core/state.py` | A shared Python dict with a strict schema, passed between every agent. |
| `agents/data_engineer.py` | Loads the CSV and adds computed columns (`Year`, `Decade`, `Success`). |
| `agents/analyst.py` | Asks Gemini to generate a JSON plan, then executes it step by step. |
| `agents/eval_agent.py` | Checks output quality with hard-coded rules, then an LLM critique. |
| `tools/analysis_tools.py` | The toolbox: deterministic functions for aggregating data and making charts. |
| `tools/plan_runtime.py` | Takes the LLM's JSON plan and executes it, one step at a time. |

---

## 5. System Architecture

### The Five Roles

```
┌─────────────────────────────────────────────────────┐
│                    SUPERVISOR                        │
│  owns run lifecycle · creates state · calls agents  │
└─────────────────────┬───────────────────────────────┘
                      │ sequential
        ┌─────────────┼──────────────┐
        ▼             ▼              ▼
  DataEngineer     Analyst        EvalAgent
  (load+enrich)  (plan+execute)  (check+critique)
        │             │              │
        └─────────────┼──────────────┘
                      ▼
              SHARED STATE (dict)
         run_id · paths · logs · eval_pass
                      │
                      ▼
          TOOLS (deterministic functions)
     group_count · plot_bar · write_markdown …
                      │
                      ▼
                 FILES ON DISK
         reports/plots/ · reports/analysis.md
```

Each role has a strict contract:

- **Supervisor** — orchestrates only, never analyzes data
- **Agents** — specialists with one responsibility each, never call each other directly
- **Tools** — do work, never call the LLM, never touch global state
- **Shared State** — minimal inter-agent contract (paths and metadata only)
- **Logs** — append-only receipts for humans, never drive logic

---

## 6. End-to-End Request Trace

Say you call `Supervisor.run("Show me launch trends by decade")`. Here is exactly what happens at each step.

### Step 1 — Supervisor creates shared state

`supervisor.py` calls `new_state(user_prompt)` from `core/state.py`. This produces a dict:

```python
{
  "run_id": "a3f8...",
  "user_prompt": "Show me launch trends by decade",
  "raw_csv_path": None,    # filled in by DataEngineer
  "enriched_csv_path": None,
  "plot_paths": [],
  "analysis_plan_path": None,
  "analysis_md_path": None,
  "eval_md_path": None,
  "eval_pass": None,
  "logs": [],
  "started_at_unix": 1712345678,
  ...
}
```

`new_state()` only takes `user_prompt` as input — everything else is either auto-generated (`run_id`, `started_at_unix`) or initialized as `None`/empty to be filled by agents.

---

### Step 2 — DataEngineerAgent

`agents/data_engineer.py` calls two tools from `tools/data_tools.py`:

1. `load_space_missions()` — reads `data/space_missions.csv`, normalizes encoding (UTF-8/cp1252/latin-1), writes a clean copy. Stores the path in `state["raw_csv_path"]`.
2. `derive_features()` — adds `Year`, `Decade`, and `Success` (boolean) columns. Stores path in `state["enriched_csv_path"]`.

State now points at an enriched CSV on disk.

---

### Step 3 — AnalystAgent (two phases)

**Phase 1 — LLM generates a plan**

`agents/analyst.py` builds a detailed prompt listing all 12 tools from the registry plus the user's question, then calls `llm_backend.py → Gemini`. Gemini returns a JSON plan:

```json
{
  "steps": [
    {"tool": "select_base_df", "args": {}},
    {"tool": "eda_probe_suite", "args": {"input": "df"}},
    {"tool": "group_count", "args": {"group_by": "Decade", "save_as": "by_decade"}},
    {"tool": "plot_bar", "args": {"table": "by_decade", "x": "Decade", "y": "count", "title": "Launches by Decade", "out_path": "reports/plots/by_decade.png"}},
    {"tool": "write_markdown", "args": {"title": "Space Trends", "tables": ["by_decade"], "plot_paths": ["reports/plots/by_decade.png"], "out_path": "reports/analysis_summary.md"}}
  ]
}
```

**Phase 2 — Runtime executes the plan**

`tools/plan_runtime.py` validates the JSON (all tools must exist in `REGISTRY`, all steps must have valid args), then loops through each step, looks up the tool function, and calls it. Each tool reads and writes a local `context` dict:

```python
context = {
    "df": <enriched DataFrame>,
    "tables": {"by_decade": <aggregated df>},
    "artifacts": {
        "plots": ["reports/plots/by_decade.png"],
        "md": "reports/analysis_summary.md"
    }
}
```

After execution, `state["plot_paths"]` and `state["analysis_md_path"]` are updated with the real file paths.

---

### Step 4 — EvalAgent

`agents/eval_agent.py` runs in two phases:

**Deterministic checks:**
- Do the plan file, markdown file, and ≥3 plots exist on disk?
- Are file sizes non-trivially small?
- Does the plan JSON parse cleanly?
- Did a time-scoped question actually use `filter_year_range`?
- Did a counts-over-time step avoid using `plot_line` when `plot_bar` is more appropriate?

**LLM critique:**
- Sends the issues list + a snippet of the output markdown to Gemini
- Asks: *"Does this output actually answer the user's question?"*
- Gemini returns structured JSON: `{pass, summary, issues, suggested_fixes}`

The agent writes `reports/eval.md` (human-readable) and `reports/eval_{run_id}.json` (structured), and sets `state["eval_pass"]` to `True` or `False`.

---

### Step 5 — Supervisor wraps up

Back in `supervisor.py`, the Supervisor sends the final state summary to Gemini to produce a short plain-English message summarizing what was done and whether it passed evaluation. It then returns the full `state` dict to the caller, with all artifact paths populated.

---

## 7. The Tool Registry

`tools/analysis_tools.py` defines 12 deterministic tools. Each is a `ToolSpec` (name, description, args schema, function) registered in `REGISTRY`.

| Tool | Purpose |
|---|---|
| `select_base_df` | Assert the base DataFrame is loaded |
| `describe_schema` | List columns and data types |
| `group_count` | Group rows and count |
| `group_success_rate` | Group and compute success rate |
| `filter_year_range` | Filter by start/end year |
| `eda_probe_suite` | Surface surprising insights (big changes, outliers) |
| `plot_line` | Line chart |
| `plot_bar` | Bar chart (supports top-N) |
| `plot_histogram` | Histogram of a numeric column |
| `plot_stacked_area` | Stacked area chart for composition over time |
| `write_markdown` | Generate a markdown report with tables and plots |

The registry is the system's **capability boundary** — the LLM can only reference tools that exist here. Adding a new capability means adding one tool; nothing else changes.

---

## 8. Key Design Considerations

### 8.1 State Schema Discipline

`STATE_KEYS` is treated as an API contract, not a scratchpad. A field only belongs in shared state if multiple agents need it. The rule:

> *"If another agent or the UI needs to rely on this field being present and stable, it belongs in `STATE_KEYS`."*

Intermediate values (aggregated tables, working DataFrames) stay in the local `context` dict inside the analyst's runtime — never promoted to shared state.

State stores **paths and identifiers**, not large objects. This keeps state serializable, loggable, and cacheable.

---

### 8.2 Logging Discipline

Six event types are always logged: `run.start/end`, `agent.start/end`, `tool.start/end`, `llm.call/response`, `state.update`, `error`.

Payloads are intentionally small — model names, file paths, key lists. Never full DataFrames or HTML blobs. Logs are described in the docs as "receipts, not a database."

State updates are logged **diff-style**: only changed keys are recorded, along with a reason string. This avoids noise and makes it trivial to reconstruct exactly what each agent modified.

Logs serve three purposes:
1. **Debugging** — what happened, where, why?
2. **Demo narrative** — show agentic steps clearly in a UI
3. **Recovery** — identify which step failed

Logs never drive logic — they are purely observational.

---

### 8.3 Plans Are Data, Not Code

The LLM's output is a JSON list of `{tool, args}` steps. This means a plan can be:
- **Validated** before execution (schema + tool existence checks)
- **Saved to disk** at `reports/plans/` for replay or audit
- **Inspected** independently of execution — what did the LLM decide?
- **Versioned** in git alongside the code

A plan file is how you debug *what the LLM decided*, separately from *what the runtime did*. The two are always traceable independently.

---

### 8.4 Tool Registry as a Safety Rail

The plan validator rejects any step referencing a tool not in `REGISTRY` before a single line of analysis runs. This prevents the LLM from hallucinating actions, keeps execution grounded in known capabilities, and makes the system extensible in a controlled way. The validator also checks that each step's args conform to the tool's schema.

---

### 8.5 Failure Is a First-Class Outcome

The runtime assumes plans may be invalid, tools may fail, and inputs may be missing. Plans are validated before execution. Errors surface with context-rich log events (`error` type with exception message and stage). A failed run is still useful if its logs explain exactly where and why it broke.

---

### 8.6 Context vs Shared State

The system maintains two distinct working memories:

| | Shared State | Runtime Context |
|---|---|---|
| Scope | Entire run, all agents | Single AnalystAgent execution |
| Contents | Paths, metadata, eval flags | DataFrames, tables, artifact paths |
| Mutability | Updated by agents via `update_state()` | Mutated in-place by tools |
| Purpose | Inter-agent contract | Tool working memory |
| Persists after run? | Yes (returned to caller) | No (local to one execution) |

---

## 9. LLM Backend Design

`llm_backend.py` centralizes all Gemini API calls. Agents call `backend.chat(messages)` — they never import or configure the Gemini SDK directly. This means:

- Switching models or providers requires changing one file
- Temperature, retry logic, and prompt formatting are consistent everywhere
- Agents remain model-agnostic by design

Default model: `gemini-2.5-flash-lite`. Default temperature: `0.2` (low randomness for reproducibility).

---

## 10. How the Docs Are Used

The three files in `docs/` are **human-facing design documents**. They are not parsed or loaded at runtime. They encode the intent and constraints that shaped the code.

| Doc file | What it covers |
|---|---|
| `key-considerations.md` | Logging rules, state hygiene, schema discipline |
| `key-considerations-state.md` | How to decide what belongs in `STATE_KEYS`, why `new_state()` takes only `user_prompt` |
| `key-principles-tool-registry-runtime.md` | 10 principles behind the tool registry, plan execution, and context design |
| `README.md` | Project philosophy, roadmap, and mapping to Google ADK |

These docs are the "why" behind the code — most valuable when extending the system, onboarding a new contributor, or porting to a framework.

---

## 11. Mental Model Summary

```
User question
     ↓
  Supervisor  (creates state, orchestrates)
     ↓
  DataEngineer  (CSV → enriched CSV on disk)
     ↓
  Analyst
    ├── LLM writes a JSON plan  (decides WHAT)
    └── plan_runtime executes it  (Python does HOW)
         └── tools produce files (plots, markdown)
     ↓
  EvalAgent  (rules + LLM critique → pass/fail)
     ↓
  State returned with paths to all artifacts
```

Six concepts are sufficient to fully explain any run:

- **LLM** = planner (decides what to do)
- **Tool Registry** = allowed capabilities
- **Runtime** = executor (does the work deterministically)
- **Context** = working memory for one execution
- **Shared State** = durable contract between agents
- **Logs** = execution truth

If you can explain a run using only these six concepts, the system is well-designed.

---

## 12. Roadmap and Future Direction

This repository is **MVP 1** — a framework-free agentic core focused on clarity over optimization.

Completed:
- Repository structure and environment setup
- Deterministic data tools (load + feature engineering)
- LLM backend abstraction
- Supervisor orchestration loop
- Explicit shared state contract with diff-based logging
- DataEngineer, Analyst, and EvalAgent implementations
- Plan validation and execution runtime
- Self-evaluation with deterministic + LLM critique

Planned:
- Minimal UI (log viewer and report output)
- ADK-based reimplementation (follow-up repository)

The architecture is deliberately designed to map cleanly onto Google ADK:

| This project | Google ADK equivalent |
|---|---|
| Supervisor | Root / coordinator agent |
| Agents | Specialized ADK agents |
| Tools | ADK tool functions |
| Shared State | InvocationContext / run-scoped data |
| Logs | Traces + UI-friendly events |
