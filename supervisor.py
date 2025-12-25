# supervisor.py
from __future__ import annotations

from typing import Dict, Any

from llm_backend import GeminiBackend
from core.state import new_state, log_event, update_state


class Supervisor:
    """
    Supervisor = orchestrator + shared-state owner.

    MVP stage:
      - prove the loop works
      - produce logs for the UI
      - later: sequence DataEngineer -> Analyst -> Storyteller deterministically
    """

    def __init__(self, model: str = "gemini-2.5-flash-lite"):
        self.backend = GeminiBackend(model=model)

    def run(self, user_prompt: str) -> Dict[str, Any]:
        # --- Create shared state (schema-aligned)
        state = new_state(user_prompt)

        log_event(state, "run.start", {"run_id": state["run_id"]})

        # --- Build messages for the LLM
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Supervisor in an agentic workflow demo. "
                    "For now, briefly acknowledge the user's question and outline "
                    "the next steps: (1) data preparation, "
                    "(2) analysis + charts, "
                    "(3) storytelling + publish report."
                ),
            },
            {"role": "user", "content": user_prompt},
        ]

        # --- Call the LLM
        log_event(
            state,
            "llm.call",
            {"provider": "gemini", "model": self.backend.model},
        )

        response_text = self.backend.chat(messages)

        log_event(state, "llm.response", {"chars": len(response_text)})


        # overwrite with actual finish time (kept explicit for clarity)
        update_state(
            state,
            {"finished_at_unix": int(__import__("time").time())},
            reason="run.complete",
        )

        # Supervisor message is not part of shared agent state yet
        state["supervisor_message"] = response_text

        log_event(state, "run.end", {"run_id": state["run_id"]})

        return state
