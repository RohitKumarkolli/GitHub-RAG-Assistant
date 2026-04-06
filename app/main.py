# app/main.py

import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import router
from app.api.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.schemas.common import ErrorResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Application factory — creates and configures FastAPI."""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
## GitHub Repository RAG Assistant 🤖

A production-grade Retrieval-Augmented Generation system for querying codebases.

### Workflow
1. **POST /api/v1/ingest-repo** — Clone and index a GitHub repository
2. **POST /api/v1/ask** — Ask questions about the indexed code
3. **POST /api/v1/search** — Raw semantic search without LLM

### Features
- 🔍 Semantic code search using HuggingFace embeddings
- 🧠 LLM-powered answers (Groq / Anthropic / HuggingFace)
- ⚡ Response caching for instant repeated queries
- 📁 Persistent FAISS vector store (survives restarts)
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "Health",      "description": "Service status and uptime"},
            {"name": "Ingestion",   "description": "Load and index repositories"},
            {"name": "RAG",         "description": "Ask questions about code"},
            {"name": "Search",      "description": "Raw semantic search"},
            {"name": "Repository",  "description": "Manage indexed repositories"},
            {"name": "Cache",       "description": "Manage response cache"},
        ],
    )

    # ── Middleware (order matters — outermost runs first) ──────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],        # Tighten this in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ─────────────────────────────────────────────────────────────────
    app.include_router(router, prefix="/api/v1")

    # ── Global error handlers ──────────────────────────────────────────────────

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="NotFound",
                detail=f"Route '{request.url.path}' does not exist.",
                path=str(request.url.path),
            ).model_dump(),
        )

    @app.exception_handler(405)
    async def method_not_allowed_handler(request: Request, exc):
        return JSONResponse(
            status_code=405,
            content=ErrorResponse(
                error="MethodNotAllowed",
                detail=(
                    f"Method '{request.method}' is not allowed "
                    f"on '{request.url.path}'."
                ),
                path=str(request.url.path),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            f"Unhandled {type(exc).__name__} "
            f"[req={request_id}] on {request.url.path}: {exc}"
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=type(exc).__name__,
                detail=str(exc),
                request_id=request_id,
                path=str(request.url.path),
            ).model_dump(),
        )

    # ── Lifecycle events ───────────────────────────────────────────────────────

    @app.on_event("startup")
    async def on_startup():
        logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting up...")
        logger.info(f"📁 Repos dir     : {settings.REPOS_DIR}")
        logger.info(f"📦 Vector store  : {settings.VECTOR_STORE_DIR}")
        logger.info(f"🤖 LLM provider  : {settings.LLM_PROVIDER}")
        logger.info(f"⚡ Cache enabled : {settings.CACHE_ENABLED}")

    @app.on_event("shutdown")
    async def on_shutdown():
        logger.info("🛑 Application shutting down...")

    return app

app = create_app()