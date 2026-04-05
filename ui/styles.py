import streamlit as st

_CSS = """
<style>
/* Tighten top padding */
.block-container {
    padding-top: 2rem !important;
}

/* Highlight items — blue left accent border */
.highlight-item {
    border-left: 3px solid #4da6ff;
    padding: 0.5rem 0.8rem;
    margin-bottom: 0.6rem;
    background: #1a1f2e;
    border-radius: 0 6px 6px 0;
    font-size: 0.95rem;
}

/* Eval banner — full-width colored bar */
.eval-banner-pass {
    background: #22c55e;
    color: #fff;
    padding: 0.8rem 1.2rem;
    border-radius: 6px;
    font-weight: 600;
    font-size: 1.1rem;
    text-align: center;
    margin-bottom: 1rem;
}
.eval-banner-fail {
    background: #ef4444;
    color: #fff;
    padding: 0.8rem 1.2rem;
    border-radius: 6px;
    font-weight: 600;
    font-size: 1.1rem;
    text-align: center;
    margin-bottom: 1rem;
}

/* Tab bar — larger text, active accent */
button[data-baseweb="tab"] {
    font-size: 1.05rem !important;
    font-weight: 500 !important;
}

/* Rounded borders on plot images */
[data-testid="stImage"] img {
    border-radius: 6px;
    border: 1px solid #2d3748;
}

/* Sample prompt chip buttons — smaller, pill-like */
div.chip-row button {
    font-size: 0.82rem !important;
    padding: 0.25rem 0.7rem !important;
    border-radius: 20px !important;
}
</style>
"""


def inject_css():
    """Inject custom CSS once at app startup."""
    st.markdown(_CSS, unsafe_allow_html=True)
