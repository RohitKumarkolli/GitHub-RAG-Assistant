
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from app.core.cache import rag_cache
from app.core.config import settings
from app.schemas.common import HealthResponse
from app.schemas.rag import AskRequest, AskResponse
from app.schemas.repo import RepoLoadRequest, RepoLoadResponse
from app.schemas.search import IndexStats, SearchResponse
from app.services.chunker import CodeChunker
from app.services.embedder import CodeEmbedder
from app.services.rag_pipeline import RAGPipeline
from app.services.repo_loader import RepoLoader
from app.services.vector_store import FAISSVectorStore
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

_APP_START_TIME = time.time()

repo_loader  = RepoLoader()
chunker      = CodeChunker()
embedder     = CodeEmbedder()
vector_store = FAISSVectorStore()
rag          = RAGPipeline(embedder=embedder, vector_store=vector_store)



class SearchRequest(BaseModel):
    repo_name: str
    query: str
    top_k: Optional[int] = None

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Search query cannot be empty.")
        return v.strip()

    @field_validator("top_k")
    @classmethod
    def top_k_valid(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 20):
            raise ValueError("top_k must be between 1 and 20.")
        return v


class AskRequestValidated(AskRequest):

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question cannot be empty.")
        if len(v.strip()) < 5:
            raise ValueError("Question is too short (minimum 5 characters).")
        if len(v) > 1000:
            raise ValueError("Question is too long (maximum 1000 characters).")
        return v.strip()

    @field_validator("repo_name")
    @classmethod
    def repo_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("repo_name cannot be empty.")
        return v.strip()



@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Service health check",
)
async def health_check():
    
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        llm_provider=settings.LLM_PROVIDER,
        embedding_model=settings.EMBEDDING_MODEL,
        embedding_dim=embedder.embedding_dim,
        indexed_repos=vector_store.list_indexed_repos(),
        cache_enabled=settings.CACHE_ENABLED,
        cache_stats=rag_cache.stats(),
        uptime_seconds=round(time.time() - _APP_START_TIME, 1),
    )


@router.post(
    "/ingest-repo",
    response_model=IndexStats,
    tags=["Ingestion"],
    summary="Ingest a repository into the vector store",
)
async def ingest_repository(request: RepoLoadRequest):
    
    logger.info(
        f"Ingest repo — url={request.repo_url}, "
        f"local={request.local_path}"
    )
    try:
        load_result = repo_loader.load(
            repo_url=request.repo_url,
            local_path=request.local_path,
            branch=request.branch,
        )

        chunk_result = chunker.chunk_files(load_result.files)

        embed_result = embedder.embed_chunks(chunk_result.chunks)

        stats = vector_store.build_index(
            embedded_chunks=embed_result.embedded_chunks,
            repo_name=load_result.repo_name,
            overwrite=True,
        )

        invalidated = rag_cache.invalidate(load_result.repo_name)
        if invalidated:
            logger.info(
                f"Cache invalidated {invalidated} entries "
                f"for repo '{load_result.repo_name}'"
            )

        return stats

    except (FileNotFoundError, NotADirectoryError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/ask",
    response_model=AskResponse,
    tags=["RAG"],
    summary="Ask a question about an indexed repository",
)
async def ask_question(request: AskRequestValidated, req: Request):
    
    request_id = getattr(req.state, "request_id", "unknown")
    logger.info(
        f"ASK [req={request_id}] — "
        f"repo='{request.repo_name}', "
        f"question='{request.question[:80]}'"
    )

    cache_key = rag_cache.make_key(
        request.repo_name, request.question, request.top_k
    )
    cached = rag_cache.get(cache_key)
    if cached is not None:
        logger.info(
            f"Cache HIT [req={request_id}] — "
            f"returning cached answer instantly"
        )
        return cached

    try:
        response = rag.ask(request)

        rag_cache.set(cache_key, response)

        return response

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{e} — Make sure you have called "
                f"POST /ingest-repo for '{request.repo_name}' first."
            ),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in /ask [req={request_id}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/search",
    response_model=SearchResponse,
    tags=["Search"],
    summary="Semantic similarity search (no LLM)",
)
async def search_repository(request: SearchRequest):
    
    try:
        query_vector = embedder.embed_query(request.query)
        response = vector_store.similarity_search(
            query_vector=query_vector,
            repo_name=request.repo_name,
            top_k=request.top_k,
        )
        response.query = request.query
        return response
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/repos",
    tags=["Repository"],
    summary="List all indexed repositories",
)
async def list_indexed_repos():
    repos = vector_store.list_indexed_repos()
    return {
        "indexed_repos": repos,
        "total": len(repos),
    }


@router.get(
    "/repos/{repo_name}/stats",
    response_model=IndexStats,
    tags=["Repository"],
    summary="Get FAISS index stats for a repository",
)
async def get_repo_stats(repo_name: str):
    try:
        return vector_store.get_index_stats(repo_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/repos/{repo_name}",
    tags=["Repository"],
    summary="Delete a repository's index",
)
async def delete_repo_index(repo_name: str):
    
    deleted = vector_store.delete_index(repo_name)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No index found for '{repo_name}'."
        )
    rag_cache.invalidate(repo_name)
    return {
        "success": True,
        "message": f"Index for '{repo_name}' deleted successfully.",
    }


@router.get(
    "/cache/stats",
    tags=["Cache"],
    summary="Get cache statistics",
)
async def get_cache_stats():

    return rag_cache.stats()


@router.delete(
    "/cache",
    tags=["Cache"],
    summary="Clear the entire response cache",
)
async def clear_cache():
    rag_cache.clear()
    return {
        "success": True,
        "message": "Cache cleared successfully.",
    }