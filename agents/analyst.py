# agents/analyst.py
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, List

import pandas as pd

from core.state import log_event, update_state
from tools.analysis_tools import REGISTRY
from tools.plan_runtime import parse_plan_json, execute_plan


class AnalystAgent:
    """
    AnalystAgent:
      1) Uses an LLM to generate an executable JSON plan using ONLY tools in REGISTRY
      2) Executes that plan deterministically via the plan runtime (tools mutate context)
      3) Writes artifacts (plan JSON, markdown report, plots) and updates shared state
    """

    def __init__(self, backend: Any):
        """
        backend can be:
          - an object with .generate(messages) -> str
          - OR a callable(messages) -> str
        """
        self.backend = backend

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        log_event(state, "agent.start", {"agent": "AnalystAgent"})

        enriched_csv_path = state.get("enriched_csv_path")
        if not enriched_csv_path:
            raise ValueError("AnalystAgent requires state['enriched_csv_path'] but it was missing/None.")

        # Ensure reports folders exist
        plots_dir = Path("reports") / "plots"
        plans_dir = Path("reports") / "plans"
        plots_dir.mkdir(parents=True, exist_ok=True)
        plans_dir.mkdir(parents=True, exist_ok=True)

        # Load dataset deterministically (this should be UTF-8 normalized already)
        log_event(state, "tool.start", {"tool": "read_enriched_csv", "path": enriched_csv_path})
        df = pd.read_csv(enriched_csv_path)
        log_event(state, "tool.end", {"tool": "read_enriched_csv", "rows": len(df), "cols": list(df.columns)})

        # Build runtime context
        context: Dict[str, Any] = {
            "df": df,
            "tables": {},
            "artifacts": {"plots": [], "md": None},
        }

        # 1) PLAN (LLM): prompt -> JSON plan
        prompt = self._build_planner_prompt(
            user_prompt=state.get("user_prompt", ""),
            run_id=state.get("run_id", "run"),
        )

        provider = getattr(self.backend, "provider", None)
        model = getattr(self.backend, "model", None)

        log_event(state, "llm.call", {"provider": provider or "unknown", "model": model or "unknown"})
        plan_text = self._llm_generate(prompt)
        log_event(state, "llm.response", {"chars": len(plan_text)})

        # parse JSON (with guard for code fences)
        cleaned = self._extract_json(plan_text)

        try:
            plan = parse_plan_json(cleaned)
        except Exception as e:
            # fallback plan = safe, minimal "time trends" plan
            log_event(state, "plan.parse_failed", {"error": str(e)})
            plan = self._fallback_plan(run_id=state.get("run_id", "run"))

        # Save plan to file for replay/debug
        plan_path = plans_dir / f"{state.get('run_id', 'run')}_analysis_plan.json"
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)

        update_state(state, {"analysis_plan_path": str(plan_path)}, reason="analysis.plan.saved")

        # 2) EXECUTE (Python runtime): validate + execute steps
        log_event(state, "tool.start", {"tool": "execute_plan", "steps": len(plan.get("steps", []))})
        execute_plan(state=state, plan=plan, context=context)
        log_event(state, "tool.end", {"tool": "execute_plan"})

        # Pull outputs from context and update shared state
        md_path = context["artifacts"].get("md")
        new_plots: List[str] = context["artifacts"].get("plots", [])

        if md_path:
            update_state(state, {"analysis_md_path": md_path}, reason="analysis.report.written")

        # extend plot_paths (do NOT overwrite)
        old_plots = state.get("plot_paths") or []
        combined = old_plots + new_plots
        update_state(state, {"plot_paths": combined}, reason="analysis.plots.added")

        elapsed_ms = int((time.time() - start) * 1000)
        log_event(state, "agent.end", {"agent": "AnalystAgent", "elapsed_ms": elapsed_ms})
        return state

    # -------------------------
    # Planner prompt
    # -------------------------

    def _build_planner_prompt(self, user_prompt: str, run_id: str) -> str:
        tools_doc_lines = []
        tools_doc_lines.append("You can ONLY use tools listed below. Do NOT invent tools.")
        tools_doc_lines.append("")
        for name, spec in REGISTRY.items():
            tools_doc_lines.append(f"- {name}: {spec.description}")
            if spec.args_schema:
                tools_doc_lines.append(f"  args: {json.dumps(spec.args_schema)}")
            else:
                tools_doc_lines.append("  args: {}")
        tools_doc = "\n".join(tools_doc_lines)

        # IMPORTANT: we force output paths into reports/...
        return f"""
You are an Analyst Planner. Your job: output a JSON plan that will be executed by a Python runtime.

User objective:
{user_prompt}

Available tools:
{tools_doc}

Hard requirements:
- Output MUST be valid JSON only (no markdown, no backticks).
- Use ONLY the tools listed above.
- Every step must be an object with:
  - "tool": tool name
  - "args": object (may be empty)
- Your plan should produce:
  - at least one plot saved under "reports/plots/"
  - a markdown report saved under "reports/analysis_summary.md"
- Prefer using derived dataset columns like "Year" and "Success" when available.
- Keep it simple and robust.

Return JSON with shape:
{{
  "version": "v1",
  "objective": "...",
  "steps": [
    {{"tool": "select_base_df", "args": {{}}}},
    ...
  ]
}}

Run id (for naming if needed): {run_id}
""".strip()

    def _llm_generate(self, prompt: str) -> str:
        # Use OpenAI-style messages (already used in your supervisor/backend)
        messages = [
            {"role": "system", "content": "You output strict JSON plans for a deterministic analysis runtime."},
            {"role": "user", "content": prompt},
        ]

        # backend can be callable or have .generate()
        if callable(self.backend):
            return self.backend(messages)
        if hasattr(self.backend, "generate"):
            return self.backend.generate(messages)
        raise TypeError("backend must be callable(messages)->str or have .generate(messages)->str")
    
    def _llm_generate(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": "You output strict JSON plans for a deterministic analysis runtime."},
            {"role": "user", "content": prompt},
        ]

        # 1) Callable backend
        if callable(self.backend):
            return self.backend(messages)

        # 2) Your backend uses .chat()
        if hasattr(self.backend, "chat"):
            return self.backend.chat(messages)

        # 3) Some backends might use .generate()
        if hasattr(self.backend, "generate"):
            return self.backend.generate(messages)

        raise TypeError("backend must be callable(messages)->str or have .chat/.generate(messages)->str")

    # -------------------------
    # JSON extraction + fallback
    # -------------------------

    def _extract_json(self, text: str) -> str:
        """
        Some models wrap JSON in ```json ...```.
        Try to extract the first JSON object.
        """
        text = text.strip()

        # Remove fenced code blocks if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        # If it already looks like JSON, return
        if text.startswith("{") and text.endswith("}"):
            return text

        # Try to find the first {...} object
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            return m.group(0)

        return text

    def _fallback_plan(self, run_id: str) -> Dict[str, Any]:
        """
        Safe fallback if plan parsing fails.
        Assumes Year + Success columns exist from derive_features().
        Produces:
          - launches per year plot
          - success rate per year plot
          - markdown summary referencing both
        """
        return {
            "version": "v1",
            "objective": "Fallback analysis: launches and success rate over time",
            "steps": [
                {"tool": "select_base_df", "args": {}},
                {
                    "tool": "group_count",
                    "args": {"input": "df", "group_by": ["Year"], "save_as": "launches_by_year"},
                },
                {
                    "tool": "plot_line",
                    "args": {
                        "table": "launches_by_year",
                        "x": "Year",
                        "y": "count",
                        "title": "Launches per Year",
                        "out_path": "reports/plots/launches_per_year.png",
                    },
                },
                {
                    "tool": "group_success_rate",
                    "args": {"input": "df", "group_by": ["Year"], "success_col": "Success", "save_as": "success_rate_by_year"},
                },
                {
                    "tool": "plot_line",
                    "args": {
                        "table": "success_rate_by_year",
                        "x": "Year",
                        "y": "success_rate",
                        "title": "Success Rate per Year",
                        "out_path": "reports/plots/success_rate_per_year.png",
                    },
                },
                {
                    "tool": "write_markdown",
                    "args": {
                        "title": "Analysis Summary",
                        "tables": ["launches_by_year", "success_rate_by_year"],
                        "plot_paths": None,
                        "out_path": "reports/analysis_summary.md",
                    },
                },
            ],
        }
