# ui/pages/1_Ingest.py

import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api_client import client
from components.styles import apply_styles
from components.sidebar import render_sidebar

st.set_page_config(
    page_title="Ingest Repo — RAG Assistant",
    page_icon="📥",
    layout="wide",
)
apply_styles()
render_sidebar()

st.title("📥 Ingest Repository")
st.markdown("Clone a GitHub repo and build its vector index.")
st.divider()

source = st.radio("Repository source", ["GitHub URL", "Local Path"], horizontal=True)

with st.form("ingest_form"):
    if source == "GitHub URL":
        repo_url   = st.text_input("GitHub Repository URL",
                                    placeholder="https://github.com/tiangolo/fastapi")
        branch     = st.text_input("Branch", value="main")
        local_path = None
    else:
        local_path = st.text_input("Local Repository Path",
                                    placeholder="/path/to/your/repo")
        repo_url   = None
        branch     = "main"

    submitted = st.form_submit_button("🚀 Start Ingestion", use_container_width=True)

if submitted:
    if not repo_url and not local_path:
        st.error("Please provide a GitHub URL or local path.")
    else:
        with st.status("Ingesting repository...", expanded=True) as status:
            st.write("📡 Connecting to backend...")
            st.write("🔄 Cloning repository...")
            st.write("✂️  Chunking code files...")
            st.write("🔢 Generating embeddings...")
            st.write("💾 Building FAISS index...")

            result = client.ingest_repo(
                repo_url=repo_url,
                local_path=local_path,
                branch=branch,
            )

        if result["success"]:
            status.update(label="✅ Ingestion complete!", state="complete")
            data = result["data"]
            st.success(f"Repository **{data.get('repo_name')}** indexed!")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📄 Vectors",    f"{data.get('total_vectors', 0):,}")
            col2.metric("📐 Dimensions", data.get("embedding_dim", 384))
            col3.metric("💾 Index Size", f"{data.get('index_size_kb', 0):.1f} KB")
            col4.metric("🗂️  Type",      data.get("index_type", "flat").upper())
            st.balloons()
        else:
            status.update(label="❌ Ingestion failed", state="error")
            st.error(f"Error: {result['data'].get('detail', 'Unknown error')}")

st.divider()
st.subheader("🌟 Quick Examples")
st.caption("Copy any URL above and paste into the form.")

examples = [
    ("FastAPI",   "https://github.com/tiangolo/fastapi",  "master"),
    ("Flask",     "https://github.com/pallets/flask",     "main"),
    ("Requests",  "https://github.com/psf/requests",      "main"),
    ("Rich",      "https://github.com/Textualize/rich",   "master"),
    ("Pydantic",  "https://github.com/pydantic/pydantic", "main"),
]

cols = st.columns(len(examples))
for col, (name, url, _) in zip(cols, examples):
    with col:
        st.markdown(f"**{name}**")
        st.code(url, language=None)
