# ui/components/styles.py

CUSTOM_CSS = """
<style>
    /* Main background */
    .stApp { background-color: #0f1117; }

    /* Cards */
    .rag-card {
        background: #1e2130;
        border: 1px solid #2d3250;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }

    /* Source reference chips */
    .source-chip {
        display: inline-block;
        background: #2d3250;
        color: #7c8cf8;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.78rem;
        margin: 2px 3px;
        font-family: monospace;
    }

    /* Relevance badges */
    .badge-high   { background:#1a4731; color:#4ade80; border-radius:5px; padding:2px 8px; font-size:0.75rem; }
    .badge-medium { background:#3d2f10; color:#fbbf24; border-radius:5px; padding:2px 8px; font-size:0.75rem; }
    .badge-low    { background:#3b1f1f; color:#f87171; border-radius:5px; padding:2px 8px; font-size:0.75rem; }

    /* Chat bubbles */
    .user-bubble {
        background: #2d3250;
        border-radius: 12px 12px 2px 12px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        text-align: right;
    }
    .bot-bubble {
        background: #1a2035;
        border: 1px solid #2d3250;
        border-radius: 12px 12px 12px 2px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
    }

    /* Status indicators */
    .status-ok  { color: #4ade80; font-weight: bold; }
    .status-err { color: #f87171; font-weight: bold; }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
</style>
"""


def apply_styles():
    """Call this at the top of every page."""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)