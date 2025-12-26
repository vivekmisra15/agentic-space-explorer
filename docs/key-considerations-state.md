# Key Considerations: State Management & Logging

This document explains the design decisions behind **state management** and **event logging**
in the *Agentic Space Explorer* MVP.

The goal is to keep the system:

- debuggable
- extensible
- agent-friendly
- understandable to humans

---

## 1. How to Decide `STATE_KEYS`

### Mental model

Think of `STATE_KEYS` as the **minimum shared contract** between all agents and workflow steps.

If multiple agents, the Supervisor, or the UI need to **rely on a field being present and stable**,
it belongs in `STATE_KEYS`.

If something is:
- temporary
- agent-local
- not needed by downstream steps

→ it should **not** go into shared state.

---

### Start from the lifecycle of a run

#### What do you know at the start?

These fields are always known when a run begins:

- `run_id` — unique identifier for the run
- `user_prompt` — the user’s natural language request
- `started_at_unix` — timestamp when execution begins

---

#### What might get added in the middle?

These are typically produced by agents or tools:

- `intent` — classified user goal (e.g. timeline, comparison, exploration)
- `raw_csv_path` — location of fetched raw data
- `enriched_csv_path` — post-cleaning / feature-engineered dataset
- `plot_paths` — generated charts or visual artifacts

---

#### What do you output at the end?

These represent final deliverables:

- `html_url` — published report or dashboard
- `finished_at_unix` — timestamp when the workflow completes

---

#### What meta-information do you always want?

For observability and debugging:

- `logs` — human-readable execution trace

---

### Inclusion rules for `STATE_KEYS`

Only include fields that:

- are meaningful to **multiple steps or agents**, or
- you want to **persist, inspect, replay, or audit** later

Avoid using shared state as a dumping ground.

Example:
- `supervisor_message` is intentionally **not** in `STATE_KEYS`
  because it is not yet part of the inter-agent contract.

---

### Concrete rule of thumb

> **“If another agent or the UI needs to rely on this field being present and stable,
> it belongs in `STATE_KEYS`.”**

You should expect to **iterate** on this list as the workflow matures.
Future stable additions might include:
- `summary`
- `cost_estimate`
- `confidence_score`

---

## 2. Why `new_state()` Only Takes `user_prompt`

At run start, the **only required external input** is the user’s question.

Everything else is either:

### Auto-generated internally

- `run_id` — created via `uuid.uuid4()`
- `started_at_unix` — current time from `time.time()`

### Placeholders for later pipeline steps

- `intent`
- `raw_csv_path`
- `enriched_csv_path`
- `html_url` → initialized as `None`
- `plot_paths`, `logs` → initialized as empty lists

This enforces a clean separation between:

#### External inputs vs derived values

- **External inputs**: things the caller must provide (today: `user_prompt`)
- **Derived values**: everything computed inside the system

---

### How this evolves cleanly

If you later want to accept additional inputs (e.g. `user_id`, `org_id`),
you extend the signature intentionally:

```python
def new_state(user_prompt: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "run_id": uuid.uuid4().hex[:10],
        "user_prompt": user_prompt,
        "intent": None,
        "raw_csv_path": None,
        "enriched_csv_path": None,
        "plot_paths": [],
        "html_url": None,
        "started_at_unix": int(time.time()),
        "finished_at_unix": None,
        "logs": [],
        "user_id": user_id,
    }
