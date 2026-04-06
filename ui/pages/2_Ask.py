# ui/pages/2_Ask.py

import streamlit as st
import requests
import streamlit as st
from api_client import client
from components.styles import apply_styles
from components.sidebar import render_sidebar
import requests

st.set_page_config(
    page_title="Ask — RAG Assistant",
    page_icon="💬",
    layout="wide",
)
apply_styles()
render_sidebar()

API_BASE_URL = st.secrets["API_BASE_URL"]

def ask_question(question):
    response = requests.post(
        f"{API_BASE_URL}/ask",
        json={"question": question}
    )
    return response.json()


API_BASE_URL = st.secrets["API_BASE_URL"]

def ask_question(question):
    response = requests.post(
        f"{API_BASE_URL}/ask",
        json={"question": question}
    )
    return response.json()

st.title("Ask Questions")

query = st.text_input("Enter your question")

if st.button("Ask"):
    with st.spinner("Thinking..."):
        result = ask_question(query)
        st.write(result)
st.markdown("Ask any question in plain English — get answers grounded in source code.")
st.divider()

# ── Initialise chat history ────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Settings bar ──────────────────────────────────────────────────────────────
repos = client.list_repos()

if not repos:
    st.warning(
        "No repositories indexed yet. "
        "Go to **📥 Ingest Repo** first."
    )
    st.stop()

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    selected_repo = st.selectbox("📚 Repository", repos)

with col2:
    top_k = st.slider("Context chunks", min_value=1, max_value=10, value=5)

with col3:
    show_sources = st.toggle("Show sources", value=True)

st.divider()

# ── Chat history display ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show sources for assistant messages
        if msg["role"] == "assistant" and msg.get("sources") and show_sources:
            with st.expander(
                f"📎 {len(msg['sources'])} source(s) used", expanded=False
            ):
                for src in msg["sources"]:
                    relevance_class = f"badge-{src['relevance']}"
                    st.markdown(
                        f"<span class='source-chip'>📄 {src['file_path']}</span>"
                        f"<span class='source-chip'>line {src['start_line']}</span>"
                        f"<span class='{relevance_class}'>{src['relevance']}</span>"
                        f"<span class='source-chip'>score {src['similarity_score']:.2f}</span>",
                        unsafe_allow_html=True,
                    )
                    st.code(src["snippet"], language=src["language"])
                    st.divider()

# ── Chat input ─────────────────────────────────────────────────────────────────
if prompt := st.chat_input(
    f"Ask about '{selected_repo}'... (e.g. How does authentication work?)"
):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate answer
    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            result = client.ask(
                repo_name=selected_repo,
                question=prompt,
                top_k=top_k,
                include_sources=show_sources,
            )

        if result["success"]:
            data     = result["data"]
            answer   = data.get("answer", "No answer returned.")
            sources  = data.get("sources", [])
            model    = data.get("model_used", "unknown")
            cached   = "⚡ cached" if data.get("message", "").startswith("Cache") else ""

            st.markdown(answer)
            st.caption(f"🤖 {model} {cached}")

            # Show sources inline
            if sources and show_sources:
                with st.expander(
                    f"📎 {len(sources)} source(s) used", expanded=False
                ):
                    for src in sources:
                        relevance_class = f"badge-{src['relevance']}"
                        st.markdown(
                            f"<span class='source-chip'>📄 {src['file_path']}</span>"
                            f"<span class='source-chip'>line {src['start_line']}</span>"
                            f"<span class='{relevance_class}'>{src['relevance']}</span>"
                            f"<span class='source-chip'>score {src['similarity_score']:.2f}</span>",
                            unsafe_allow_html=True,
                        )
                        st.code(src["snippet"], language=src["language"])
                        st.divider()

            # Save to history
            st.session_state.messages.append({
                "role":    "assistant",
                "content": answer,
                "sources": sources,
            })

        else:
            error = result["data"].get("detail", "Unknown error")
            st.error(f"❌ {error}")

# ── Clear chat ─────────────────────────────────────────────────────────────────
if st.session_state.messages:
    if st.button("🗑️ Clear chat history", type="secondary"):
        st.session_state.messages = []
        st.rerun()
