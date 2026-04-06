# ui/pages/2_Ask.py

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api_client import client
from components.styles import apply_styles
from components.sidebar import render_sidebar

st.set_page_config(
    page_title="Ask — RAG Assistant",
    page_icon="💬",
    layout="wide",
)
apply_styles()
render_sidebar()

st.title("💬 Ask About the Code")
st.markdown("Ask any question in plain English — answers grounded in source code.")
st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []

repos = client.list_repos()

if not repos:
    st.warning("No repositories indexed yet. Go to **📥 Ingest Repo** first.")
    st.stop()

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    selected_repo = st.selectbox("📚 Repository", repos)
with col2:
    top_k = st.slider("Context chunks", min_value=1, max_value=10, value=5)
with col3:
    show_sources = st.toggle("Show sources", value=True)

st.divider()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources") and show_sources:
            with st.expander(f"📎 {len(msg['sources'])} source(s)", expanded=False):
                for src in msg["sources"]:
                    st.markdown(
                        f"`📄 {src['file_path']}` | "
                        f"line `{src['start_line']}` | "
                        f"score `{src['similarity_score']:.2f}` | "
                        f"**{src['relevance']}**"
                    )
                    st.code(src["snippet"], language=src["language"])
                    st.divider()

if prompt := st.chat_input(f"Ask about '{selected_repo}'..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            result = client.ask(
                repo_name=selected_repo,
                question=prompt,
                top_k=top_k,
                include_sources=show_sources,
            )

        if result["success"]:
            data    = result["data"]
            answer  = data.get("answer", "No answer returned.")
            sources = data.get("sources", [])
            model   = data.get("model_used", "unknown")

            st.markdown(answer)
            st.caption(f"🤖 {model}")

            if sources and show_sources:
                with st.expander(f"📎 {len(sources)} source(s)", expanded=False):
                    for src in sources:
                        st.markdown(
                            f"`📄 {src['file_path']}` | "
                            f"line `{src['start_line']}` | "
                            f"score `{src['similarity_score']:.2f}` | "
                            f"**{src['relevance']}**"
                        )
                        st.code(src["snippet"], language=src["language"])
                        st.divider()

            st.session_state.messages.append({
                "role": "assistant", "content": answer, "sources": sources,
            })
        else:
            st.error(f"❌ {result['data'].get('detail', 'Unknown error')}")

if st.session_state.messages:
    if st.button("🗑️ Clear chat", type="secondary"):
        st.session_state.messages = []
        st.rerun()
