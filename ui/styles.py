import streamlit as st

_CSS = """
<style>
/* ── Google Fonts ──────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

/* ── Global font stack ─────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', system-ui, sans-serif;
}

/* ── App background — nebula gradient ──────────────────────────────────── */
.stApp {
    background:
        radial-gradient(ellipse 80% 50% at 50% 0%,
            rgba(30, 40, 80, 0.8) 0%,
            rgba(14, 17, 23, 1) 70%),
        radial-gradient(ellipse 40% 30% at 80% 20%,
            rgba(80, 30, 80, 0.2) 0%,
            transparent 60%),
        #0e1117;
    background-attachment: fixed;
}

/* ── Star field ─────────────────────────────────────────────────────────── */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    box-shadow:
        /* Layer 1 — bright, sparse */
        120px  80px 0 rgba(255,255,255,0.25),
        340px 160px 0 rgba(255,255,255,0.20),
        580px  40px 0 rgba(255,255,255,0.22),
        780px 220px 0 rgba(255,255,255,0.18),
        960px  90px 0 rgba(255,255,255,0.24),
       1140px 300px 0 rgba(255,255,255,0.20),
       1380px 140px 0 rgba(255,255,255,0.22),
       1560px 260px 0 rgba(255,255,255,0.16),
       1720px  60px 0 rgba(255,255,255,0.20),
       1880px 180px 0 rgba(255,255,255,0.18),
        /* Layer 2 — dimmer, medium density */
         60px 400px 0 rgba(255,255,255,0.13),
        200px 500px 0 rgba(255,255,255,0.11),
        420px 340px 0 rgba(255,255,255,0.14),
        660px 460px 0 rgba(255,255,255,0.10),
        840px 380px 0 rgba(255,255,255,0.13),
       1020px 520px 0 rgba(255,255,255,0.11),
       1220px 430px 0 rgba(255,255,255,0.12),
       1460px 490px 0 rgba(255,255,255,0.10),
       1640px 360px 0 rgba(255,255,255,0.13),
       1800px 560px 0 rgba(255,255,255,0.11),
        /* Layer 3 — faint, dense fill */
        150px 640px 0 rgba(255,255,255,0.08),
        310px 700px 0 rgba(255,255,255,0.07),
        490px 620px 0 rgba(255,255,255,0.09),
        710px 740px 0 rgba(255,255,255,0.07),
        890px 660px 0 rgba(255,255,255,0.08),
       1080px 720px 0 rgba(255,255,255,0.07),
       1260px 680px 0 rgba(255,255,255,0.09),
       1440px 760px 0 rgba(255,255,255,0.07),
       1620px 640px 0 rgba(255,255,255,0.08),
       1800px 700px 0 rgba(255,255,255,0.07);
}

/* ── Layout ─────────────────────────────────────────────────────────────── */
.block-container {
    padding-top: 2rem !important;
    position: relative;
    z-index: 1;
}

/* ── Highlight items ────────────────────────────────────────────────────── */
.highlight-item {
    border-left: 3px solid #4da6ff;
    padding: 0.5rem 0.8rem;
    margin-bottom: 0.6rem;
    background: linear-gradient(135deg, #1a1f2e 60%, #1e2540);
    border-radius: 0 6px 6px 0;
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    font-weight: 400;
    transition: transform 200ms cubic-bezier(0.4,0,0.2,1),
                box-shadow 200ms cubic-bezier(0.4,0,0.2,1),
                background 200ms cubic-bezier(0.4,0,0.2,1);
}
.highlight-item:hover {
    transform: translateX(4px);
    box-shadow: 0 0 12px rgba(77,166,255,0.15);
}

/* ── Eval banners ───────────────────────────────────────────────────────── */
.eval-banner-pass {
    background: #22c55e;
    color: #fff;
    padding: 0.8rem 1.2rem;
    border-radius: 6px;
    font-family: 'Inter', sans-serif;
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
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 1.1rem;
    text-align: center;
    margin-bottom: 1rem;
}

/* ── Tab bar ────────────────────────────────────────────────────────────── */
button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 500 !important;
    transition: color 180ms cubic-bezier(0.4,0,0.2,1),
                background 180ms cubic-bezier(0.4,0,0.2,1);
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(180deg, transparent 80%, rgba(77,166,255,0.15) 100%);
}

/* ── Primary "Run Analysis" button ─────────────────────────────────────── */
[data-testid="stBaseButton-primary"] button {
    background: linear-gradient(135deg, #2563eb, #4da6ff) !important;
    box-shadow: 0 0 18px rgba(77,166,255,0.3);
    border: none !important;
    transition: box-shadow 150ms cubic-bezier(0.4,0,0.2,1),
                transform 150ms cubic-bezier(0.4,0,0.2,1);
}
[data-testid="stBaseButton-primary"] button:hover {
    transform: translateY(-1px);
    box-shadow: 0 0 28px rgba(77,166,255,0.5) !important;
}

/* ── Chart / plot images ────────────────────────────────────────────────── */
[data-testid="stImage"] img {
    border-radius: 6px;
    border: 1px solid #2d3748;
    transition: transform 200ms cubic-bezier(0.4,0,0.2,1),
                border-color 200ms cubic-bezier(0.4,0,0.2,1);
}
[data-testid="stImage"] img:hover {
    transform: scale(1.03);
    border-color: #4da6ff;
}

/* ── Card depth ─────────────────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    box-shadow: 0 2px 16px rgba(0,0,0,0.4), 0 0 0 1px rgba(77,166,255,0.08);
}

/* ── Metric tiles ───────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1a1f2e, #1e2540);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    border: 1px solid rgba(77,166,255,0.12);
    box-shadow: 0 2px 12px rgba(0,0,0,0.3);
}

/* ── Section heading utility class ─────────────────────────────────────── */
.section-heading {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.3rem;
    font-weight: 600;
    color: #fafafa;
    margin-bottom: 0.75rem;
}

/* ── Sample prompt chip buttons ─────────────────────────────────────────── */
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
