# ui/components/sidebar.py

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api_client import client


def render_sidebar():
    with st.sidebar:
        st.title("🤖 RAG Assistant")
        st.caption("GitHub Codebase Q&A")
        st.divider()

        st.subheader("🔌 Backend Status")
        health = client.health()

        if health.get("status") == "ok":
            st.markdown('<span style="color:#4ade80">● Connected</span>',
                        unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            col1.metric("Uptime", f"{health.get('uptime_seconds', 0):.0f}s")
            col2.metric("LLM", health.get("llm_provider", "—").upper())
        else:
            st.markdown('<span style="color:#f87171">● Disconnected</span>',
                        unsafe_allow_html=True)
            st.warning("Backend not reachable.")

        st.divider()

        st.subheader("📚 Indexed Repos")
        repos = client.list_repos()
        if repos:
            for repo in repos:
                st.markdown(f"✅ `{repo}`")
        else:
            st.info("No repos indexed yet.")

        st.divider()

        st.subheader("⚡ Cache")
        cache = client.get_cache_stats()
        if cache:
            hit_rate = cache.get("hit_rate_pct", 0)
            st.progress(int(hit_rate) / 100, text=f"Hit rate: {hit_rate}%")
            col1, col2 = st.columns(2)
            col1.metric("Cached", cache.get("size", 0))
            col2.metric("Hits", cache.get("hits", 0))

        st.divider()
        st.caption("GitHub RAG Assistant v0.1.0")
