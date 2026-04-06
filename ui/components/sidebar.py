# ui/components/sidebar.py

import streamlit as st
from api_client import client


def render_sidebar():
    """
    Shared sidebar rendered on every page.
    Shows backend status, indexed repos, and cache stats.
    """
    with st.sidebar:
        st.image(
            "https://img.icons8.com/fluency/96/bot.png",
            width=60,
        )
        st.title("RAG Assistant")
        st.caption("GitHub Codebase Q&A")
        st.divider()

        # ── Backend status ─────────────────────────────────────────────────────
        st.subheader("🔌 Backend Status")
        health = client.health()

        if health.get("status") == "ok":
            st.markdown(
                '<span class="status-ok">● Connected</span>',
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            col1.metric("Uptime", f"{health.get('uptime_seconds', 0):.0f}s")
            col2.metric("Provider", health.get("llm_provider", "—").upper())
        else:
            st.markdown(
                '<span class="status-err">● Disconnected</span>',
                unsafe_allow_html=True,
            )
            st.warning("Backend not reachable. Is it running?")

        st.divider()

        # ── Indexed repos ──────────────────────────────────────────────────────
        st.subheader("📚 Indexed Repos")
        repos = client.list_repos()

        if repos:
            for repo in repos:
                st.markdown(f"✅ `{repo}`")
        else:
            st.info("No repositories indexed yet.")

        st.divider()

        # ── Cache stats ────────────────────────────────────────────────────────
        st.subheader("⚡ Cache")
        cache = client.get_cache_stats()
        if cache:
            hit_rate = cache.get("hit_rate_pct", 0)
            st.progress(
                int(hit_rate) / 100,
                text=f"Hit rate: {hit_rate}%",
            )
            col1, col2 = st.columns(2)
            col1.metric("Cached", cache.get("size", 0))
            col2.metric("Hits", cache.get("hits", 0))

        st.divider()
        st.caption("GitHub RAG Assistant v0.1.0")