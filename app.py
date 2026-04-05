import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from supervisor import Supervisor
from ui.styles import inject_css
from ui.components import render_header, render_query_input, render_agent_timing
from ui.renderers import (
    render_highlights,
    render_chart_gallery,
    render_analysis_report,
    render_eval_card,
    render_debug,
)

# --- Page config (must be first st call) ---
st.set_page_config(
    page_title="Agentic Space Explorer",
    page_icon="\U0001f680",
    layout="wide",
)
inject_css()

# --- Session state init ---
if "app_state" not in st.session_state:
    st.session_state["app_state"] = "idle"
if "result" not in st.session_state:
    st.session_state["result"] = None
if "error_msg" not in st.session_state:
    st.session_state["error_msg"] = None
if "auto_run" not in st.session_state:
    st.session_state["auto_run"] = False
if "selected_chart_idx" not in st.session_state:
    st.session_state["selected_chart_idx"] = 0

# --- Header + Input ---
render_header()
query, should_run = render_query_input()

# --- Run pipeline ---
if should_run and query:
    st.session_state["app_state"] = "running"
    st.session_state["error_msg"] = None
    st.session_state["selected_chart_idx"] = 0

    with st.status("Running analysis pipeline...", expanded=True) as status:
        try:
            st.write("**Stage 1/3** — Data Engineering: loading and enriching dataset")
            st.write("**Stage 2/3** — Analysis: planning and executing analysis")
            st.write("**Stage 3/3** — Evaluation: checking output quality")

            result = Supervisor(model="gemini-2.5-flash-lite").run(query)

            st.session_state["result"] = result
            st.session_state["app_state"] = "completed"
            status.update(label="Analysis complete!", state="complete")
        except Exception as e:
            st.session_state["app_state"] = "error"
            st.session_state["error_msg"] = str(e)
            status.update(label=f"Pipeline failed: {e}", state="error")

# --- Error display ---
if st.session_state["app_state"] == "error":
    st.error(f"Pipeline failed: {st.session_state['error_msg']}")

# --- Results (three-tab layout) ---
if st.session_state["app_state"] == "completed" and st.session_state["result"]:
    result = st.session_state["result"]

    # Agent timing — always visible above tabs
    render_agent_timing(result.get("logs", []))
    st.divider()

    # Three tabs
    tab_insights, tab_report, tab_eval = st.tabs(
        ["Insights", "Report", "Evaluation & Debug"]
    )

    with tab_insights:
        # Supervisor overview message
        sup_msg = result.get("supervisor_message", "")
        if sup_msg:
            st.markdown(
                f'<p style="color:#888; font-size:0.9rem;">{sup_msg}</p>',
                unsafe_allow_html=True,
            )

        render_highlights(result.get("analysis_md_path"))
        st.divider()
        render_chart_gallery(result.get("plot_paths", []))

    with tab_report:
        render_analysis_report(result.get("analysis_md_path"))

    with tab_eval:
        render_eval_card(result)
        st.divider()
        render_debug(result)
