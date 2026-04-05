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

/* Pass / fail badges */
.badge-pass {
    background: #22c55e;
    color: #fff;
    padding: 3px 12px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.85rem;
}
.badge-fail {
    background: #ef4444;
    color: #fff;
    padding: 3px 12px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.85rem;
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
