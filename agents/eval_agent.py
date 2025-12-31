# agents/eval_agent.py

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from core.state import log_event, update_state


class EvalAgent:
    """
    EvalAgent = lightweight deterministic checker + one LLM critique call.

    It does NOT redo analysis.
    It evaluates whether the produced artifacts and analysis align with the user prompt,
    and writes an eval report.
    """

    def __init__(self, backend: Any, reports_dir: str = "reports"):
        self.backend = backend
        self.reports_dir = reports_dir

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        run_id = state.get("run_id", "unknown")

        log_event(state, "agent.start", {"agent": "EvalAgent"})

        os.makedirs(self.reports_dir, exist_ok=True)

        # ---- 1) Deterministic checks
        issues = self._deterministic_checks(state)

        # ---- 2) LLM critique (adds richer issues + summary)
        eval_json = self._llm_critique(state, issues)

        # ---- 3) Write eval artifacts
        eval_md_path = os.path.join(self.reports_dir, "eval.md")
        eval_json_path = os.path.join(self.reports_dir, f"eval_{run_id}.json")

        with open(eval_json_path, "w", encoding="utf-8") as f:
            json.dump(eval_json, f, indent=2, ensure_ascii=False)

        md = self._render_eval_md(state, eval_json)
        with open(eval_md_path, "w", encoding="utf-8") as f:
            f.write(md)

        # ---- 4) Update shared state
        update_state(
            state,
            {
                "eval_md_path": eval_md_path,
                "eval_json_path": eval_json_path,
                "eval_pass": bool(eval_json.get("pass", False)),
            },
            reason="eval.complete",
        )

        elapsed_ms = int((time.time() - start) * 1000)
        log_event(
            state,
            "agent.end",
            {"agent": "EvalAgent", "elapsed_ms": elapsed_ms, "pass": bool(eval_json.get("pass", False))},
        )
        return state

    def _deterministic_checks(self, state: Dict[str, Any]) -> List[str]:
        issues: List[str] = []

        user_prompt = (state.get("user_prompt") or "").strip()
        plan_path = state.get("analysis_plan_path")
        md_path = state.get("analysis_md_path")
        plot_paths = state.get("plot_paths") or []

        # Existence checks
        if not plan_path or not os.path.exists(plan_path):
            issues.append(f"Missing analysis plan JSON at state['analysis_plan_path']: {plan_path}")

        if not md_path or not os.path.exists(md_path):
            issues.append(f"Missing analysis markdown at state['analysis_md_path']: {md_path}")
        else:
            if os.path.getsize(md_path) < 50:
                issues.append("Analysis markdown is unusually small (<50 bytes).")

        if not plot_paths or len(plot_paths) < 3:
            issues.append(f"Expected >=3 plots but found {len(plot_paths)} in state['plot_paths'].")

        for p in plot_paths:
            if not os.path.exists(p):
                issues.append(f"Plot path missing on disk: {p}")

        # Plan parse + heuristic checks
        plan = None
        if plan_path and os.path.exists(plan_path):
            try:
                with open(plan_path, "r", encoding="utf-8") as f:
                    plan = json.load(f)
            except Exception as e:
                issues.append(f"Analysis plan JSON could not be parsed: {e}")

        # If user asks for decade / year range, ensure filter_year_range exists
        if plan and self._looks_like_time_scoped_prompt(user_prompt):
            steps = plan.get("steps", [])
            uses_filter = any(s.get("tool") == "filter_year_range" for s in steps)
            if not uses_filter:
                issues.append("User prompt appears time-scoped but plan did not call filter_year_range.")

        # Simple “taste” heuristic: counts-by-year should not be plotted as line
        if plan:
            steps = plan.get("steps", [])
            # detect: group_count by ["Year"] into table X, then plot_line using y=count from X
            year_count_tables = set()
            for s in steps:
                if s.get("tool") == "group_count":
                    args = s.get("args", {})
                    gb = args.get("group_by") or []
                    if len(gb) == 1 and str(gb[0]).lower() == "year":
                        year_count_tables.add(args.get("save_as"))
            for s in steps:
                if s.get("tool") == "plot_line":
                    args = s.get("args", {})
                    if args.get("table") in year_count_tables and str(args.get("y", "")).lower() in ("count", "launches"):
                        issues.append("Counts-by-year plotted as a line; prefer bar or histogram for counts.")

        return issues

    def _looks_like_time_scoped_prompt(self, prompt: str) -> bool:
        p = prompt.lower()
        # crude but effective for MVP
        return ("1960" in p or "1970" in p or "1980" in p or "1990" in p or "2000" in p or "2010" in p or "2020" in p
                or "decade" in p or "from " in p or "between " in p or "vs" in p or "compare" in p)

    def _llm_critique(self, state: Dict[str, Any], deterministic_issues: List[str]) -> Dict[str, Any]:
        user_prompt = (state.get("user_prompt") or "").strip()
        plan_path = state.get("analysis_plan_path")
        md_path = state.get("analysis_md_path")
        plot_paths = state.get("plot_paths") or []

        plan_text = ""
        if plan_path and os.path.exists(plan_path):
            try:
                plan_text = open(plan_path, "r", encoding="utf-8").read()
            except Exception:
                plan_text = ""

        md_head = ""
        if md_path and os.path.exists(md_path):
            try:
                md_head = open(md_path, "r", encoding="utf-8").read(1500)
            except Exception:
                md_head = ""

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict evaluator for an agentic analytics workflow.\n"
                    "Your job: judge whether the analysis artifacts and narrative plausibly answer the user's question.\n"
                    "Return STRICT JSON only, no markdown.\n"
                    "Schema:\n"
                    "{"
                    "\"pass\": boolean, "
                    "\"summary\": string, "
                    "\"issues\": [string], "
                    "\"suggested_fixes\": [string]"
                    "}\n"
                    "Be concise, practical, and grounded in the provided artifacts."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"USER PROMPT:\n{user_prompt}\n\n"
                    f"DETERMINISTIC ISSUES FOUND:\n{json.dumps(deterministic_issues, indent=2)}\n\n"
                    f"PLAN JSON (may be truncated):\n{plan_text[:8000]}\n\n"
                    f"PLOTS:\n{json.dumps(plot_paths, indent=2)}\n\n"
                    f"ANALYSIS MARKDOWN (head):\n{md_head}\n"
                ),
            },
        ]

        # Backend uses .chat() in your project; fall back to callable/generate if needed
        if hasattr(self.backend, "chat"):
            raw = self.backend.chat(messages)
        elif callable(self.backend):
            raw = self.backend(messages)
        elif hasattr(self.backend, "generate"):
            raw = self.backend.generate(messages)
        else:
            # If no LLM available, fall back to deterministic only
            return {
                "pass": len(deterministic_issues) == 0,
                "summary": "LLM critique unavailable; deterministic checks only.",
                "issues": deterministic_issues,
                "suggested_fixes": [],
            }

        # Parse JSON safely
        try:
            parsed = json.loads(raw)
        except Exception:
            # If model returns non-JSON, degrade gracefully
            parsed = {
                "pass": len(deterministic_issues) == 0,
                "summary": "LLM returned non-JSON; used deterministic checks.",
                "issues": deterministic_issues,
                "suggested_fixes": [],
                "raw_llm": raw[:2000],
            }

        # Merge deterministic issues into model issues (dedupe)
        model_issues = parsed.get("issues") or []
        merged = list(dict.fromkeys([*deterministic_issues, *model_issues]))

        parsed["issues"] = merged
        # If either says fail, fail
        if deterministic_issues and parsed.get("pass") is True:
            parsed["pass"] = False

        return parsed

    def _render_eval_md(self, state: Dict[str, Any], eval_json: Dict[str, Any]) -> str:
        user_prompt = state.get("user_prompt", "")
        plan_path = state.get("analysis_plan_path", "")
        md_path = state.get("analysis_md_path", "")
        plot_paths = state.get("plot_paths") or []

        lines: List[str] = []
        lines.append("# Eval Report")
        lines.append("")
        lines.append(f"**Run ID:** {state.get('run_id','')}")
        lines.append("")
        lines.append(f"**User prompt:** {user_prompt}")
        lines.append("")
        lines.append(f"**Pass:** {eval_json.get('pass', False)}")
        lines.append("")
        lines.append("## Summary")
        lines.append(eval_json.get("summary", ""))
        lines.append("")
        lines.append("## Issues")
        issues = eval_json.get("issues") or []
        if not issues:
            lines.append("- None")
        else:
            for i in issues:
                lines.append(f"- {i}")
        lines.append("")
        lines.append("## Suggested fixes")
        fixes = eval_json.get("suggested_fixes") or []
        if not fixes:
            lines.append("- None")
        else:
            for f in fixes:
                lines.append(f"- {f}")
        lines.append("")
        lines.append("## Artifacts")
        lines.append(f"- Plan: `{plan_path}`")
        lines.append(f"- Analysis markdown: `{md_path}`")
        if plot_paths:
            lines.append("- Plots:")
            for p in plot_paths:
                lines.append(f"  - `{p}`")
        else:
            lines.append("- Plots: none found in state")
        lines.append("")
        return "\n".join(lines)
