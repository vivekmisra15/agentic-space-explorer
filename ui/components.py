import streamlit as st

SAMPLE_PROMPTS = [
    "What were the most interesting decades for space launches?",
    "Which companies had the highest launch success rates?",
    "How did launch frequency change after the Cold War?",
    "What surprising patterns appear in mission success over time?",
]


def render_header():
    st.markdown("""
    <div style="
        padding: 2.5rem 0 1.5rem 0;
        box-shadow: 0 8px 40px 0 rgba(77,166,255,0.08);
        margin-bottom: 0.5rem;
    ">
        <h1 style="
            font-family: 'Orbitron', sans-serif;
            font-size: 2.6rem;
            font-weight: 700;
            background: linear-gradient(135deg, #4da6ff, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 0 0 0.6rem 0;
            letter-spacing: 0.04em;
        ">Agentic Space Explorer</h1>
        <div style="
            height: 1px;
            background: linear-gradient(90deg, transparent, #4da6ff, transparent);
            margin-bottom: 0.75rem;
        "></div>
        <p style="
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            font-weight: 300;
            color: #aabbcc;
            margin: 0;
            letter-spacing: 0.02em;
        ">Ask a question about space missions and watch a multi-agent AI workflow investigate it.</p>
    </div>
    """, unsafe_allow_html=True)


def _set_chip(prompt: str):
    """Callback for sample prompt chip clicks."""
    st.session_state["user_query"] = prompt
    st.session_state["auto_run"] = True


def render_query_input() -> tuple[str, bool]:
    """Render the query input box, run button, and sample chips.

    Returns (query_text, should_run).
    """
    query = st.text_input(
        "Your question",
        key="user_query",
        placeholder="e.g. Show me the most interesting insights from the 1960s",
    )

    run_clicked = st.button("Run Analysis", type="primary", use_container_width=True)

    # Sample prompt chips
    cols = st.columns(len(SAMPLE_PROMPTS))
    for col, prompt in zip(cols, SAMPLE_PROMPTS):
        with col:
            st.button(
                prompt,
                key=f"chip_{prompt[:20]}",
                on_click=_set_chip,
                args=(prompt,),
                use_container_width=True,
            )

    # Consume auto_run flag
    auto_run = st.session_state.get("auto_run", False)
    if auto_run:
        st.session_state["auto_run"] = False

    should_run = run_clicked or auto_run
    return query, should_run


def render_agent_timing(logs: list):
    """Parse agent.end events from logs and display elapsed times."""
    timings = {}
    for entry in logs:
        if entry.get("event") == "agent.end":
            payload = entry.get("payload", {})
            agent = payload.get("agent", "Unknown")
            elapsed_ms = payload.get("elapsed_ms", 0)
            timings[agent] = elapsed_ms

    if not timings:
        return

    cols = st.columns(len(timings))
    for col, (agent, ms) in zip(cols, timings.items()):
        # Friendly label: strip "Agent" suffix
        label = agent.replace("Agent", "").strip()
        with col:
            st.metric(label=label, value=f"{ms / 1000:.1f}s")
