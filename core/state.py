# core/state.py
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, List


# --- 1) State contract (schema) ---
STATE_KEYS: Tuple[str, ...] = (
    "run_id",
    "user_prompt",
    "intent",
    "raw_csv_path",
    "enriched_csv_path",
    "plot_paths",
    "html_url",
    "started_at_unix",
    "finished_at_unix",
    "logs",
    "analysis_plan_path",
    "analysis_md_path",
)


def new_state(user_prompt: str) -> Dict[str, Any]:
    """
    Create a fresh, schema-aligned state dict for one run.
    """
    return {
        "run_id": uuid.uuid4().hex[:10],  # short id for logs/UI
        "user_prompt": user_prompt,
        "intent": None,
        "raw_csv_path": None,
        "enriched_csv_path": None,
        "plot_paths": [],
        "html_url": None,
        "started_at_unix": int(time.time()),
        "finished_at_unix": None,
        "logs": [],
        "analysis_plan_path": None,
        "analysis_md_path": None,

    }


# --- 2) Logging helper ---
def log_event(
    state: Dict[str, Any],
    event: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append a structured log entry to state["logs"].
    Logs are for humans/UX, not for driving logic.
    """
    state["logs"].append(
        {
            "ts": time.strftime("%H:%M:%S"),
            "event": event,
            "payload": payload or {},
        }
    )


# --- 3) State update helper (auto logs changed keys) ---
def update_state(
    state: Dict[str, Any],
    updates: Dict[str, Any],
    *,
    reason: str = "state.update",
    log_values: bool = False,
    allow_new_keys: bool = False,
) -> List[str]:
    """
    Update state in one place and automatically log which keys changed.

    - changed_keys are always logged.
    - values are NOT logged by default (keep logs small & safe).
    - allow_new_keys=False enforces the state contract.

    Returns: list of changed keys
    """
    changed_keys: List[str] = []

    for k, v in updates.items():
        if (not allow_new_keys) and (k not in STATE_KEYS):
            raise KeyError(
                f"Key '{k}' not in STATE_KEYS. "
                f"Either add it intentionally or set allow_new_keys=True."
            )

        old = state.get(k, None)
        if old != v:
            state[k] = v
            changed_keys.append(k)

    payload: Dict[str, Any] = {"changed_keys": changed_keys, "reason": reason}

    # Optional: log small values for specific safe fields
    if log_values and changed_keys:
        payload["values"] = {k: state.get(k) for k in changed_keys}

    log_event(state, "state.update", payload)

    return changed_keys
