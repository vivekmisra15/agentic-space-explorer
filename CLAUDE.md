# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Set up environment
python3.13 -m venv venv
venv/bin/pip install -r requirements.txt

# Run the integration test (full pipeline)
venv/bin/python test_supervisor.py

# Run data tools smoke tests
venv/bin/python tools/test_data_tools.py

# Run a quick end-to-end flow manually
venv/bin/python -c "from supervisor import Supervisor; print(Supervisor().run('Your question here'))"
```

## Architecture

This is a **framework-free, from-first-principles agentic system**. The core philosophy: **the LLM only plans, Python executes.** No LangChain, no ADK — all orchestration is explicit.

### Pipeline

```
User question → Supervisor → DataEngineerAgent → AnalystAgent → EvalAgent → state dict
```

**`supervisor.py`** owns the run lifecycle. It creates a shared state dict, calls the three agents in sequence, appends a final supervisor message, and returns the complete state.

**`llm_backend.py`** is the single point for all Gemini API calls. All agents go through it so the system stays model-agnostic. It converts OpenAI-style messages to plain-text prompts and reads `GEMINI_API_KEY` from `.env`.

### Agents

- **`agents/data_engineer.py`** — Loads the raw CSV (trying UTF-8 → cp1252 → latin-1) and derives `Year`, `Decade`, `Success`, `EnrichedAtUnix` columns. Writes two files to `data/` and stores their paths in state.
- **`agents/analyst.py`** — Two-phase: (1) builds a prompt from `REGISTRY` tool specs, calls Gemini, gets back a JSON plan; (2) validates and executes the plan step-by-step using `plan_runtime.execute_plan`. Maintains a local `context` dict (base df + derived tables + artifact paths) that is passed to every tool but never written to shared state — only file paths go into state.
- **`agents/eval_agent.py`** — Runs 10 deterministic checks (files exist, ≥3 plots, time-scoped questions used `filter_year_range`, etc.), then sends a summary to Gemini for an LLM critique. Merges both and writes `reports/evals/eval.md` + `reports/evals/eval_{run_id}.json`.

### Shared State (`core/state.py`)

State is the only communication channel between agents. The **`STATE_KEYS`** dict is the strict schema — agents must only write keys defined there. The rule: state stores **paths and IDs, never large objects**. `update_state()` logs a diff of which keys changed and why.

### Tool System (`tools/`)

**`tools/analysis_tools.py`** defines 12 deterministic tools as `ToolSpec` dataclasses (name, description, args_schema, fn). All tools mutate the runtime `context` in place and log side effects to disk. Tools are grouped:
- Data inspection: `select_base_df`, `describe_schema`
- Aggregation: `group_count`, `group_success_rate`, `filter_year_range`, `eda_probe_suite`
- Visualization: `plot_line`, `plot_bar`, `plot_histogram`, `plot_stacked_area`
- Reporting: `write_markdown`

The `REGISTRY` list exported from this file is the **capability boundary** — the LLM can only reference tools that exist here. Adding a new capability means adding one `ToolSpec` to `REGISTRY`, nothing else.

**`tools/plan_runtime.py`** validates the JSON plan (tool names exist, steps are well-formed) before executing it. If validation fails, `analyst.py` falls back to a safe default plan.

### Logging

Six event types are logged into `state["logs"]`: `run.start/end`, `agent.start/end`, `tool.start/end`, `llm.call/response`, `state.update`, `error`. Logs are observation-only — no logic reads from them.

## Configuration

- **`.env`** — requires `GEMINI_API_KEY`. Copy `.env.example` to get started.
- Default model: `gemini-2.5-flash-lite`. Override via `Supervisor(model="...")`.
- Generated outputs go to `reports/` (gitignored). Source data lives in `data/space_missions.csv`.
