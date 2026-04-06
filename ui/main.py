# ui/main.py

import streamlit as st
import sys
import os

# ── Fix import path for Streamlit Cloud ───────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from components.styles import apply_styles
from components.sidebar import render_sidebar
from api_client import client

st.set_page_config(
    page_title="GitHub RAG Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_styles()
render_sidebar()

st.title("🤖 GitHub RAG Assistant")
st.markdown(
    "**Ask questions about any GitHub repository in plain English.**  \n"
    "Powered by semantic search + LLM generation."
)
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="rag-card">
        <h3>1️⃣ Ingest</h3>
        <p>Paste a GitHub URL to clone, chunk, embed, and index your repo.</p>
        <small>→ Go to <b>Ingest Repo</b> page</small>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="rag-card">
        <h3>2️⃣ Ask</h3>
        <p>Ask any question about the code. Get answers with source references.</p>
        <small>→ Go to <b>Ask</b> page</small>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="rag-card">
        <h3>3️⃣ Manage</h3>
        <p>View index stats, clear cache, and delete repositories.</p>
        <small>→ Go to <b>Manage</b> page</small>
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.info("👈 Use the sidebar to navigate between pages.")
