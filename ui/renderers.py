import json
import os
import re
from pathlib import Path

import plotly.io as pio
import streamlit as st


# ---------------------------------------------------------------------------
# Table / column metadata for business-friendly labels
# ---------------------------------------------------------------------------

TABLE_METADATA = {
    "eda_insights": "Key anomalies detected — year-over-year spikes and drops in launch activity.",
    "launches_per_year": "Total orbital launch attempts per calendar year.",
    "success_rate_over_time": "Mission success rate trend across all years.",
    "success_rate_by_year": "Mission success rate grouped by year.",
    "company_success_rates": "Per-company mission success rate across all time.",
}

COLUMN_METADATA = {
    "insight_type": "Category of anomaly (spike = sharp increase, drop = sharp decrease)",
    "launches_yoy_delta": "Change in launches vs. the previous year",
    "success_rate": "Fraction of missions that succeeded (0.0–1.0)",
    "label": "The year this anomaly occurred",
    "count": "Number of launches in the group",
}


# ---------------------------------------------------------------------------
# Highlights
# ---------------------------------------------------------------------------

def _sanitize_highlight(text: str) -> str:
    """Strip backtick-wrapped tokens and clean up whitespace."""
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    return text if len(text) >= 10 else ""


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
                cleaned = _sanitize_highlight(stripped[2:])
                if cleaned:
                    highlights.append(cleaned)
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

    if len(highlights) >= 4:
        # 2-column card grid
        for i in range(0, len(highlights), 2):
            cols = st.columns(2)
            for col_idx, h in enumerate(highlights[i : i + 2]):
                with cols[col_idx]:
                    st.markdown(
                        f'<div class="highlight-item">{h}</div>',
                        unsafe_allow_html=True,
                    )
    else:
        for h in highlights:
            st.markdown(
                f'<div class="highlight-item">{h}</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Chart Gallery
# ---------------------------------------------------------------------------

def _caption_from_path(path: str) -> str:
    """Derive a human-readable caption from a plot filename."""
    name = Path(path).stem
    return name.replace("_", " ").title()


def _select_chart(idx: int):
    """Callback for thumbnail button clicks."""
    st.session_state["selected_chart_idx"] = idx


def render_chart_gallery(plot_paths: list[str]):
    """Render a thumbnail row + full-width selected chart (Plotly if available)."""
    existing = [p for p in plot_paths if os.path.exists(p)]
    if not existing:
        st.info("No charts generated.")
        return

    st.subheader("Charts")

    # Clamp selected index
    selected = st.session_state.get("selected_chart_idx", 0)
    if selected >= len(existing):
        st.session_state["selected_chart_idx"] = 0
        selected = 0

    # --- Thumbnail row ---
    cols_per_row = min(len(existing), 6)
    for row_start in range(0, len(existing), cols_per_row):
        row_paths = existing[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col_idx, path in enumerate(row_paths):
            abs_idx = row_start + col_idx
            is_selected = abs_idx == selected
            with cols[col_idx]:
                st.image(path, caption=_caption_from_path(path), use_container_width=True)
                st.button(
                    "Selected" if is_selected else "View",
                    key=f"thumb_{abs_idx}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                    on_click=_select_chart,
                    args=(abs_idx,),
                )

    # --- Full-width selected chart ---
    st.divider()
    selected_path = existing[selected]
    plotly_path = selected_path.replace(".png", ".plotly.json")

    st.markdown(f"**{_caption_from_path(selected_path)}**")

    if os.path.exists(plotly_path):
        with open(plotly_path, "r") as f:
            fig = pio.from_json(f.read())
        fig.update_layout(
            paper_bgcolor="#0e1117",
            plot_bgcolor="#0e1117",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.image(selected_path, use_container_width=True)


# ---------------------------------------------------------------------------
# Analysis Report (with table metadata)
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
        lines = content.split("\n")
        buffer = []

        for line in lines:
            table_match = re.match(r'^### `(\w+)`', line)
            if table_match:
                # Flush buffered lines
                if buffer:
                    st.markdown("\n".join(buffer))
                    buffer = []
                # Render table heading with metadata
                table_name = table_match.group(1)
                st.markdown(f"### `{table_name}`")
                desc = TABLE_METADATA.get(
                    table_name,
                    table_name.replace("_", " ").title(),
                )
                st.caption(desc)

                # Column guide expander for known columns
                matching = {
                    col: desc
                    for col, desc in COLUMN_METADATA.items()
                }
                if matching:
                    with st.expander("Column guide", expanded=False):
                        for col, col_desc in matching.items():
                            st.markdown(f"- **{col}**: {col_desc}")
            else:
                buffer.append(line)

        # Flush remaining
        if buffer:
            st.markdown("\n".join(buffer))


# ---------------------------------------------------------------------------
# Eval Card
# ---------------------------------------------------------------------------

def render_eval_card(state: dict):
    eval_pass = state.get("eval_pass")
    eval_json_path = state.get("eval_json_path")

    # Banner
    if eval_pass is True:
        st.markdown(
            '<div class="eval-banner-pass">Quality Check Passed</div>',
            unsafe_allow_html=True,
        )
    elif eval_pass is False:
        st.markdown(
            '<div class="eval-banner-fail">Quality Issues Detected</div>',
            unsafe_allow_html=True,
        )
    else:
        st.warning("Evaluation did not run.")
        return

    # Parse eval JSON for details
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
