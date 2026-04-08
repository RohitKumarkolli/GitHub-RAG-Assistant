---
title: GitHub RAG Assistant API
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---
> **Ask questions about any GitHub repository in plain English — powered by semantic search + LLM generation.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red?logo=streamlit)](https://streamlit.io)
[![FAISS](https://img.shields.io/badge/FAISS-Vector_Store-orange)](https://github.com/facebookresearch/faiss)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Table of Contents

- [What is this?](#-what-is-this)
- [Demo](#-demo)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start (Local)](#-quick-start-local)
- [Docker Setup](#-docker-setup)
- [Streamlit Community Deployment](#-deploy-to-streamlit-community-cloud)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [How RAG Works](#-how-rag-works)
- [Milestones](#-milestones-built)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🎯 What is this?

The **GitHub RAG Assistant** is a production-grade **Retrieval-Augmented Generation (RAG)** system that lets you have a conversation with any codebase.

### What it does:
- 📥 **Clones** any public GitHub repository (or reads a local path)
- ✂️  **Chunks** code files intelligently — preserving function and class boundaries
- 🔢 **Embeds** chunks into 384-dimensional vectors using HuggingFace
- 💾 **Indexes** vectors in a persistent FAISS database
- 💬 **Answers** your natural language questions using LLM + retrieved context
- 📎 **Cites** exact file paths and line numbers in every answer

### Example questions you can ask:
```
"How does dependency injection work in this codebase?"
"Where is authentication handled?"
"What does the UserService class do?"
"How are database connections managed?"
"What is the entry point of this application?"
```

---

## 🎬 Demo

| Page | Description |
|------|-------------|
| ![Ingest](https://via.placeholder.com/400x200/1e2130/7c8cf8?text=📥+Ingest+Repo) | Paste a GitHub URL, watch it clone + index |
| ![Ask](https://via.placeholder.com/400x200/1e2130/4ade80?text=💬+Ask+Questions) | Chat interface with source references |
| ![Manage](https://via.placeholder.com/400x200/1e2130/fbbf24?text=⚙️+Manage+Repos) | Stats, cache control, repo management |

> **Live Demo**: [GitHub-RAG-Assistant.streamlit.app](https://app-rag-assistant-7.streamlit.app) 

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    STREAMLIT UI (Port 8501)                  │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────────────┐  │
│  │ 1_Ingest │   │    2_Ask     │   │     3_Manage        │  │
│  │  (form)  │   │   (chat)     │   │  (stats/delete)     │  │
│  └────┬─────┘   └──────┬───────┘   └──────────┬──────────┘  │
│       └────────────────┴──────────────────────┘             │
│                    api_client.py                             │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST
┌──────────────────────────▼──────────────────────────────────┐
│                   FASTAPI BACKEND (Port 8000)                │
│                                                              │
│  /ingest-repo  ──►  RepoLoader → Chunker → Embedder → FAISS │
│  /ask          ──►  Embedder → FAISS.search → Groq LLM      │
│  /search       ──►  Embedder → FAISS.search                 │
│  /health       ──►  Status + cache stats                     │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ FAISS    │  │HuggingFace│  │  Groq    │  │  TTL Cache │  │
│  │ (disk)   │  │Embeddings │  │  LLM API │  │ (memory)   │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### RAG Pipeline Flow

```
User Question
      │
      ▼
Embed Query ──► FAISS Search ──► Top-K Chunks
                                      │
                                      ▼
                              Build Prompt
                          (system + context + question)
                                      │
                                      ▼
                              Groq LLM API
                                      │
                                      ▼
                         Answer + Source References
```

---

## 🧩 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Streamlit 1.35 | Multi-page chat UI |
| **Backend** | FastAPI 0.111 | REST API server |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Text → 384-dim vectors |
| **Vector DB** | FAISS (CPU) | Fast similarity search |
| **LLM** | Groq (`llama-3.3-70b-versatile`) | Answer generation |
| **Git** | GitPython | Repo cloning |
| **Chunking** | LangChain + custom regex | Structure-aware splitting |
| **Validation** | Pydantic v2 | Request/response schemas |
| **Deployment** | Docker + Streamlit Cloud | Container + cloud hosting |

---

## 📁 Project Structure

```
github-rag-assistant/
│
├── app/                            # FastAPI backend
│   ├── api/
│   │   ├── middleware.py           # Request timing, IDs, security headers
│   │   └── routes.py               # All API endpoints
│   ├── core/
│   │   ├── cache.py                # In-memory TTL response cache
│   │   └── config.py               # Centralised settings (env-driven)
│   ├── schemas/
│   │   ├── chunk.py                # CodeChunk models
│   │   ├── common.py               # Shared response models
│   │   ├── embeddings.py           # EmbeddedChunk models
│   │   ├── rag.py                  # AskRequest / AskResponse
│   │   ├── repo.py                 # RepoLoadRequest / CodeFile
│   │   └── search.py               # SearchResult / IndexStats
│   ├── services/
│   │   ├── chunker.py              # 3-tier code chunking
│   │   ├── embedder.py             # HuggingFace batch embedding
│   │   ├── prompt_builder.py       # Prompt engineering
│   │   ├── rag_pipeline.py         # Full RAG orchestration
│   │   ├── repo_loader.py          # Git clone + file scanning
│   │   └── vector_store.py         # FAISS index management
│   ├── utils/
│   │   └── logger.py               # Structured logging
│   └── main.py                     # FastAPI app factory
│
├── ui/                             # Streamlit frontend
│   ├── pages/
│   │   ├── 1_Ingest.py             # Repository ingestion page
│   │   ├── 2_Ask.py                # Chat / Q&A page
│   │   └── 3_Manage.py             # Management dashboard
│   ├── components/
│   │   ├── sidebar.py              # Shared sidebar component
│   │   └── styles.py               # Custom dark theme CSS
│   ├── api_client.py               # HTTP client for FastAPI
│   └── main.py                     # Streamlit entry point
│
├── docker/
│   ├── Dockerfile.api              # Backend container
│   └── Dockerfile.ui               # Frontend container
│
├── data/
│   └── repos/                      # Cloned repositories (git-ignored)
│
├── vector_store/                   # FAISS indices (git-ignored)
│
├── docker-compose.yml              # Local orchestration
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── .gitignore
└── README.md
```

---

## ⚡ Quick Start (Local)

### Prerequisites

- Python 3.11+
- Git
- 4 GB RAM minimum (for embedding model)
- A free [Groq API key](https://console.groq.com)

### 1. Clone this repository

```bash
git clone https://github.com/YOUR_USERNAME/github-rag-assistant.git
cd github-rag-assistant
```

### 2. Create virtual environment

```bash
python -m venv venv

# Activate:
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
# Copy the template
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
DEBUG=False
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here   # Get free at https://console.groq.com
GROQ_MODEL=llama-3.3-70b-versatile
```

### 5. Start the FastAPI backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
🚀 GitHub RAG Assistant v0.1.0 starting up...
✅ Groq client ready — model='llama-3.3-70b-versatile'
```

### 6. Start the Streamlit UI (new terminal)

```bash
streamlit run ui/main.py
```

### 7. Open your browser

| Service | URL |
|---------|-----|
| **Streamlit UI** | http://localhost:8501 |
| **FastAPI Docs** | http://localhost:8000/docs |
| **API Health** | http://localhost:8000/api/v1/health |

### 8. Use the app

1. Go to **📥 Ingest Repo** → paste a GitHub URL → click **Start Ingestion**
2. Go to **💬 Ask** → select the repo → type your question
3. Get answers with source file references! 🎉

---

## 🐳 Docker Setup

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — add your GROQ_API_KEY
```

### 2. Build and run

```bash
docker-compose up --build
```

First run downloads the embedding model (~90 MB) — takes 2-3 minutes.

### 3. Open your browser

- **UI** → http://localhost:8501
- **API Docs** → http://localhost:8000/docs

### Useful Docker commands

```bash
# Run in background
docker-compose up -d --build

# View backend logs
docker-compose logs -f api

# View frontend logs
docker-compose logs -f ui

# Stop everything
docker-compose down

# Stop and remove volumes (full reset)
docker-compose down -v

# Rebuild after code changes
docker-compose up --build --force-recreate
```

---

## ☁️ Deploy to Streamlit Community Cloud

> **Note:** Streamlit Community Cloud only hosts the **UI**. The FastAPI backend needs to run separately (locally, on a VPS, or Railway/Render).

### Option A — UI on Streamlit Cloud + API on Railway (Recommended Free Setup)

#### Step 1 — Deploy the FastAPI backend on Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Select your repository
3. Set the **Start Command**:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Add environment variables in Railway dashboard:
   ```
   LLM_PROVIDER=groq
   GROQ_API_KEY=your_groq_api_key
   GROQ_MODEL=llama-3.3-70b-versatile
   DEBUG=False
   ```
5. Copy your Railway deployment URL (e.g. `https://your-app.railway.app`)

#### Step 2 — Deploy the UI on Streamlit Community Cloud

1. **Push your project to GitHub** (see section below)

2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**

3. Fill in the form:
   ```
   Repository:  YOUR_USERNAME/github-rag-assistant
   Branch:      main
   Main file:   ui/main.py
   ```

4. Click **Advanced settings** → add **Secrets**:
   ```toml
   API_BASE_URL = "https://your-app.railway.app/api/v1"
   ```

5. Click **Deploy** → your app will be live at:
   ```
   https://your-username-github-rag-assistant.streamlit.app
   ```

---

#### Step 3 — Create `ui/api_client.py` secrets support

Make sure your `ui/api_client.py` reads from Streamlit secrets:

```python
def get_api_url() -> str:
    try:
        return st.secrets.get("API_BASE_URL", "http://localhost:8000/api/v1")
    except Exception:
        return "http://localhost:8000/api/v1"
```

---

### Option B — Full local backend + Streamlit Cloud UI (for testing)

If your FastAPI is running locally and you have a public IP (or use [ngrok](https://ngrok.com)):

```bash
# Expose local API publicly using ngrok (free)
ngrok http 8000
# Copy the https URL e.g. https://abc123.ngrok.io
```

Then in Streamlit Cloud secrets:
```toml
API_BASE_URL = "https://abc123.ngrok.io/api/v1"
```

---

### 📋 Required Files for Streamlit Cloud

Make sure these files exist in your repo root:

```
✅ ui/main.py              ← Entry point
✅ requirements.txt         ← Dependencies (add streamlit + requests)
✅ .gitignore               ← Excludes .env, venv, data/, vector_store/
```

Create a `packages.txt` in root for system dependencies:
```
# packages.txt
git
```

---

## 🌐 Pushing to GitHub

### First time setup

```bash
# 1. Initialise git (if not already done)
git init

# 2. Add all files
git add .

# 3. Check what's being committed (verify .env is NOT listed)
git status

# 4. First commit
git commit -m "🚀 Initial commit — GitHub RAG Assistant"

# 5. Create repo on GitHub at https://github.com/new
#    Name: github-rag-assistant
#    Visibility: Public (required for Streamlit Community Cloud free tier)

# 6. Add remote and push
git remote add origin https://github.com/YOUR_USERNAME/github-rag-assistant.git
git branch -M main
git push -u origin main
```

### Verify `.gitignore` is correct

These must **never** be committed:

```gitignore
# Secrets
.env

# Python
venv/
__pycache__/
*.pyc

# Generated data (too large for GitHub)
data/repos/
vector_store/
*.faiss
*.pkl
```

### Subsequent updates

```bash
git add .
git commit -m "✨ Add new feature"
git push
```

---

## 📡 API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive docs: `http://localhost:8000/docs`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service status, uptime, cache stats |
| `POST` | `/ingest-repo` | Clone + index a repository |
| `POST` | `/ask` | Ask a question (RAG) |
| `POST` | `/search` | Raw semantic search (no LLM) |
| `GET` | `/repos` | List indexed repositories |
| `GET` | `/repos/{name}/stats` | Index statistics |
| `DELETE` | `/repos/{name}` | Delete a repo index |
| `GET` | `/cache/stats` | Cache hit rate + size |
| `DELETE` | `/cache` | Clear all cached answers |

### Example: Ingest a repository

```bash
curl -X POST http://localhost:8000/api/v1/ingest-repo \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/tiangolo/fastapi",
    "branch": "master"
  }'
```

### Example: Ask a question

```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name": "fastapi",
    "question": "How does dependency injection work?",
    "top_k": 5,
    "include_sources": true
  }'
```

---

## ⚙️ Configuration

All settings live in `.env`. Full reference:

```env
# ── Application ──────────────────────────────────────────────
DEBUG=False
APP_NAME="GitHub RAG Assistant"

# ── LLM Provider ─────────────────────────────────────────────
# Options: groq | anthropic | huggingface
LLM_PROVIDER=groq

# ── Groq (free tier — recommended) ───────────────────────────
GROQ_API_KEY=gsk_...
# Available models:
# llama-3.3-70b-versatile   ← best quality (recommended)
# llama-3.1-8b-instant      ← fastest
# gemma2-9b-it              ← alternative
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_MAX_TOKENS=1024
GROQ_TEMPERATURE=0.2

# ── Anthropic (optional, paid) ────────────────────────────────
# ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=claude-3-haiku-20240307

# ── Embedding Model ───────────────────────────────────────────
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32
EMBEDDING_DEVICE=cpu           # cpu | cuda | mps

# ── Chunking ──────────────────────────────────────────────────
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# ── Retrieval ─────────────────────────────────────────────────
TOP_K_RESULTS=5
MIN_SIMILARITY_SCORE=0.0

# ── Cache ─────────────────────────────────────────────────────
CACHE_ENABLED=True
CACHE_TTL_SECONDS=3600         # 1 hour
CACHE_MAX_SIZE=100
```

---

## 🧠 How RAG Works

RAG (Retrieval-Augmented Generation) grounds LLM answers in **real source code** instead of hallucinating.

```
WITHOUT RAG:
  Question → LLM → Answer based on training data (may hallucinate)

WITH RAG:
  Question → Embed → Search → Retrieve relevant chunks
                                        ↓
                              LLM answers ONLY using
                              the actual code context
                                        ↓
                              Accurate answer + citations
```

### Step-by-step:

| Step | What happens |
|------|-------------|
| **1. Ingest** | Repo is cloned, files scanned, code split into chunks |
| **2. Embed** | Each chunk converted to a 384-dim vector via `all-MiniLM-L6-v2` |
| **3. Store** | Vectors saved in a FAISS index on disk |
| **4. Query** | User question embedded into same vector space |
| **5. Search** | FAISS finds top-5 most similar chunks (cosine similarity) |
| **6. Prompt** | Chunks assembled into a structured prompt with rules |
| **7. Generate** | Groq LLM reads context + question → generates grounded answer |
| **8. Respond** | Answer returned with source file + line number citations |

---

## 🪜 Milestones Built

This project was built step-by-step through 9 milestones:

| # | Milestone | What was built |
|---|-----------|---------------|
| 1 | **Project Setup** | FastAPI skeleton, config, logging |
| 2 | **Repo Loader** | GitPython cloning, file scanning |
| 3 | **Code Chunking** | Structure-aware splitting per language |
| 4 | **Embeddings** | HuggingFace batch encoding |
| 5 | **Vector Store** | FAISS index + persistence |
| 6 | **RAG Pipeline** | Full retrieve → prompt → generate flow |
| 7 | **FastAPI Integration** | Middleware, caching, validation |
| 8 | **Groq Integration** | Switched from Anthropic to free Groq API |
| 9 | **UI + Docker** | Streamlit UI + Docker deployment |

---

## 🔧 Troubleshooting

### ❌ `TypeError: Client.__init__() got an unexpected keyword argument 'proxies'`

```bash
pip uninstall anthropic httpx -y
pip install "anthropic>=0.40.0" "httpx>=0.27.0"
```

### ❌ `model_decommissioned` error from Groq

Update your model in `.env`:
```env
GROQ_MODEL=llama-3.3-70b-versatile
```

### ❌ All chunks scored below threshold (0 results returned)

The question may be metadata-based ("how many files?") rather than code-based. RAG answers questions about **code logic**, not file system structure. Try:
```
✅ "How does authentication work?"
✅ "What does the UserService class do?"
❌ "How many files are there?"
```

Or lower the threshold in `.env`:
```env
MIN_SIMILARITY_SCORE=0.0
```

### ❌ Streamlit can't connect to backend

Ensure FastAPI is running on port 8000:
```bash
curl http://localhost:8000/api/v1/health
```

If using Docker, check both containers are up:
```bash
docker-compose ps
docker-compose logs api
```

### ❌ Ingestion is very slow

- First run downloads the embedding model (~90 MB) — normal
- Large repos (10k+ files) take 5-10 minutes to embed — normal
- Use `depth=1` shallow clone (already configured) for speed

### ❌ Out of memory during embedding

Reduce batch size in `.env`:
```env
EMBEDDING_BATCH_SIZE=8
```

---

## 🤝 Contributing

Contributions are welcome!

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/github-rag-assistant.git

# 3. Create a feature branch
git checkout -b feature/my-new-feature

# 4. Make your changes

# 5. Commit with a descriptive message
git commit -m "✨ Add support for private repositories"

# 6. Push and open a Pull Request
git push origin feature/my-new-feature
```

### Ideas for contributions:
- 🔒 Private repository support (GitHub token auth)
- 🌐 Multi-repo search (search across multiple indexed repos)
- 📊 Answer quality metrics and evaluation
- 🔄 Auto re-indexing when repo updates
- 💾 Redis cache backend for multi-instance deployments
- 🌍 Support for GitLab / Bitbucket URLs

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [Streamlit](https://streamlit.io/) — Rapid UI for ML apps
- [LangChain](https://langchain.com/) — LLM orchestration utilities
- [FAISS](https://github.com/facebookresearch/faiss) — Facebook AI Similarity Search
- [Sentence Transformers](https://www.sbert.net/) — State-of-the-art embeddings
- [Groq](https://groq.com/) — Ultra-fast free LLM inference
- [HuggingFace](https://huggingface.co/) — Open-source ML models

---

<div align="center">

**Built with ❤️ as a production-level MLOps learning project**

⭐ Star this repo if you found it useful!

</div>
