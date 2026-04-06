# ui/pages/3_Manage.py

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api_client import client
from components.styles import apply_styles
from components.sidebar import render_sidebar

st.set_page_config(
    page_title="Manage — RAG Assistant",
    page_icon="⚙️",
    layout="wide",
)
apply_styles()
render_sidebar()

st.title("⚙️ Manage Repositories")
st.divider()

repos = client.list_repos()

st.subheader("📊 Indexed Repositories")
if not repos:
    st.info("No repositories indexed yet.")
else:
    for repo in repos:
        with st.expander(f"📚 {repo}", expanded=True):
            stats = client.get_repo_stats(repo)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Vectors",    f"{stats.get('total_vectors', 0):,}")
            col2.metric("Dimensions", stats.get("embedding_dim", 384))
            col3.metric("Index Size", f"{stats.get('index_size_kb', 0):.1f} KB")
            col4.metric("Trained",    "✅" if stats.get("is_trained") else "❌")

            if st.button(f"🗑️ Delete '{repo}'", key=f"del_{repo}", type="secondary"):
                result = client.delete_repo(repo)
                if result["success"]:
                    st.success(f"Deleted '{repo}'.")
                    st.rerun()
                else:
                    st.error(result["data"].get("detail", "Delete failed."))

st.divider()
st.subheader("⚡ Cache Management")
cache = client.get_cache_stats()
if cache:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cached",    cache.get("size", 0))
    col2.metric("Hit Rate",  f"{cache.get('hit_rate_pct', 0)}%")
    col3.metric("Hits",      cache.get("hits", 0))
    col4.metric("Misses",    cache.get("misses", 0))

    if st.button("🗑️ Clear Cache", type="secondary"):
        if client.clear_cache():
            st.success("Cache cleared.")
            st.rerun()

st.divider()
st.subheader("🔌 Backend Info")
health = client.health()
if health.get("status") == "ok":
    col1, col2, col3 = st.columns(3)
    col1.metric("LLM",       health.get("llm_provider", "—").upper())
    col2.metric("Embedding", health.get("embedding_model", "—").split("/")[-1])
    col3.metric("Uptime",    f"{health.get('uptime_seconds', 0):.0f}s")
