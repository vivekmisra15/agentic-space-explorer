import json
import os
from pathlib import Path

import streamlit as st


# ---------------------------------------------------------------------------
# Highlights
# ---------------------------------------------------------------------------

def parse_highlights(md_path: str) -> list[str]:
    """Extract bullet items from the '## Key highlights' section."""
    if not md_path or not os.path.exists(md_path):
        return []
    with open(md_path, "r") as f:
        lines = f.readlines()

    in_section = False
    highlights = []
    for line in lines:
        stripped = line.strip()
        if stripped.lower() == "## key highlights":
            in_section = True
            continue
        if in_section:
            if stripped.startswith("##"):
                break
            if stripped.startswith("- "):
                highlights.append(stripped[2:])
    return highlights


def render_highlights(md_path: str):
    if not md_path:
        st.info("No highlights available.")
        return
    highlights = parse_highlights(md_path)
    if not highlights:
        st.info("No highlights available.")
        return

    st.subheader("Key Highlights")
    for h in highlights:
        st.markdown(
            f'<div class="highlight-item">{h}</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _caption_from_path(path: str) -> str:
    """Derive a human-readable caption from a plot filename."""
    name = Path(path).stem  # e.g. "launches_1960s"
    return name.replace("_", " ").title()


def render_charts(plot_paths: list[str]):
    existing = [p for p in plot_paths if os.path.exists(p)]
    if not existing:
        st.info("No charts generated.")
        return

    st.subheader("Charts")
    for i in range(0, len(existing), 3):
        cols = st.columns(3)
        for col, path in zip(cols, existing[i : i + 3]):
            with col:
                st.image(path, caption=_caption_from_path(path), use_container_width=True)


# ---------------------------------------------------------------------------
# Analysis Report
# ---------------------------------------------------------------------------

def render_analysis_report(md_path: str):
    if not md_path or not os.path.exists(md_path):
        st.info("No analysis report generated.")
        return
    content = Path(md_path).read_text()
    if not content.strip():
        st.info("No analysis report generated.")
        return
    with st.container(border=True):
        st.markdown(content)


# ---------------------------------------------------------------------------
# Eval Card
# ---------------------------------------------------------------------------

def render_eval_card(state: dict):
    eval_pass = state.get("eval_pass")
    eval_json_path = state.get("eval_json_path")

    # Badge
    if eval_pass is True:
        st.markdown('<span class="badge-pass">PASS</span>', unsafe_allow_html=True)
    elif eval_pass is False:
        st.markdown('<span class="badge-fail">FAIL</span>', unsafe_allow_html=True)
    else:
        st.warning("Evaluation did not run.")
        return

    # Try to parse the full eval JSON for details
    if not eval_json_path or not os.path.exists(eval_json_path):
        return

    try:
        with open(eval_json_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    summary = data.get("summary", "")
    if summary:
        st.markdown(f"**Summary:** {summary}")

    issues = data.get("issues", [])
    if issues:
        st.markdown("**Issues:**")
        for issue in issues:
            st.markdown(f"- {issue}")
    else:
        st.markdown("No issues found.")

    fixes = data.get("suggested_fixes", [])
    if fixes:
        st.markdown("**Suggested fixes:**")
        for fix in fixes:
            st.markdown(f"- {fix}")


# ---------------------------------------------------------------------------
# Debug / Artifact View
# ---------------------------------------------------------------------------

def render_debug(state: dict):
    with st.expander("Developer / Artifact View", expanded=False):
        tab_logs, tab_state, tab_plan, tab_paths = st.tabs(
            ["Logs", "State", "Plan", "Paths"]
        )

        with tab_logs:
            logs = state.get("logs", [])
            if logs:
                rows = [
                    {
                        "ts": e.get("ts", ""),
                        "event": e.get("event", ""),
                        "payload": json.dumps(e.get("payload", {}), default=str),
                    }
                    for e in logs
                ]
                st.dataframe(rows, use_container_width=True)
            else:
                st.info("No logs recorded.")

        with tab_state:
            # Exclude logs from the snapshot to keep it readable
            snapshot = {k: v for k, v in state.items() if k != "logs"}
            st.json(snapshot)

        with tab_plan:
            plan_path = state.get("analysis_plan_path")
            if plan_path and os.path.exists(plan_path):
                try:
                    with open(plan_path, "r") as f:
                        st.json(json.load(f))
                except (json.JSONDecodeError, OSError):
                    st.warning("Could not parse analysis plan.")
            else:
                st.info("No analysis plan available.")

        with tab_paths:
            path_keys = [
                "raw_csv_path",
                "enriched_csv_path",
                "analysis_plan_path",
                "analysis_md_path",
                "eval_md_path",
                "eval_json_path",
            ]
            for key in path_keys:
                val = state.get(key)
                if val:
                    st.text(f"{key}: {val}")
            plot_paths = state.get("plot_paths", [])
            if plot_paths:
                st.text(f"plot_paths ({len(plot_paths)} files):")
                for p in plot_paths:
                    st.text(f"  {p}")
