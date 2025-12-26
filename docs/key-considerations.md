# Key Considerations (MVP v1)

This document captures practical rules used in the Agentic Space Explorer MVP.
The goal is to keep the system debuggable, demo-friendly, and extensible.

---

## What to Log (and what NOT to log)

Logs exist for:
1) Debugging (what happened, where, why?)
2) Demo narrative (show agentic steps clearly)
3) Recovery (identify which step failed)

### The 6 event types to always log
- `run.start` / `run.end`
- `agent.start` / `agent.end`
- `tool.start` / `tool.end`
- `llm.call` / `llm.response`
- `state.update` (log changed keys, not full state)
- `error` (exception type + message + stage)

### Payload rules (keep logs small)
Good payloads:
- model name, agent/tool name, durations
- `changed_keys` lists
- small identifiers (paths, URLs, counts)

Avoid:
- full DataFrames
- full HTML output
- full Plotly JSON blobs

Think of logs as **receipts**, not a database.

---

## State vs Logs

### State = shared working memory
State should contain only values that downstream steps need.

MVP state keys (contract):
- `user_prompt`
- `intent`
- `raw_csv_path`
- `enriched_csv_path`
- `plot_paths`
- `html_url`

State should store **paths/IDs**, not large objects.

### Logs = append-only trace for humans
Logs should never drive logic.
They help you understand what happened.

---

## Schema Discipline (avoids state explosion)

Rules:
- Treat state like an API (add keys intentionally).
- Prefer file paths over large in-memory objects.
- When updating state, log which keys changed (diff-style).
- If a state key is not consumed later, it probably should not exist.

---

## Why an LLM Backend Adapter Exists

The LLM backend (Gemini adapter) centralizes SDK calls:
- Agents/Supervisor stay provider-agnostic.
- Changing model/providers becomes easier.
- Prompts and response handling become consistent.

---

## Scaling Beyond MVP

For larger systems:
- Keep state schema explicit (or typed).
- Keep logs event-coded + diff-based.
- Use workflow orchestration primitives (sequential/parallel) instead of ad-hoc routing.
- Consider externalizing state (Redis/DB) and logs (event stream) once needed.
