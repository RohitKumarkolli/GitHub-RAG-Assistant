# app/services/vector_store.py

import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import faiss
import numpy as np

from app.core.config import settings
from app.schemas.embeddings import EmbeddedChunk
from app.schemas.search import IndexStats, SearchResponse, SearchResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── Filenames inside each repo's vector store folder ──────────────────────────
FAISS_INDEX_FILE = "index.faiss"
METADATA_FILE    = "metadata.pkl"


class FAISSVectorStore:
    """
    Manages FAISS vector indices — one per repository.

    Responsibilities:
      - Build a FAISS index from EmbeddedChunk objects
      - Persist index + metadata to disk
      - Load existing index from disk
      - Perform fast similarity search
      - Manage multiple repo indices in memory

    Storage layout:
      vector_store/
        <repo_name>/
            index.faiss      ← FAISS binary index
            metadata.pkl     ← List[dict] chunk metadata (no vectors)
    """

    def __init__(self):
        self.store_dir = settings.VECTOR_STORE_DIR
        self.top_k     = settings.TOP_K_RESULTS
        self.min_score = settings.MIN_SIMILARITY_SCORE

        # In-memory cache: repo_name → (faiss.Index, List[metadata_dict])
        # Avoids reloading from disk on every search
        self._indices: Dict[str, Tuple[faiss.Index, List[dict]]] = {}

        logger.info(f"FAISSVectorStore initialised — store_dir={self.store_dir}")

    # ── Public: Indexing ───────────────────────────────────────────────────────

    def build_index(
        self,
        embedded_chunks: List[EmbeddedChunk],
        repo_name: str,
        overwrite: bool = True,
    ) -> IndexStats:
        """
        Build a FAISS index from a list of EmbeddedChunk objects and
        save it to disk.

        Args:
            embedded_chunks: Output from CodeEmbedder.embed_chunks()
            repo_name:       Name used for the storage folder
            overwrite:       If False and index exists, skip rebuilding

        Returns:
            IndexStats summarising the created index
        """
        repo_store_dir = self._get_repo_dir(repo_name)

        # ── Check if we should skip rebuilding ────────────────────────────────
        if not overwrite and self._index_exists(repo_name):
            logger.info(f"Index for '{repo_name}' exists — skipping rebuild.")
            return self.get_index_stats(repo_name)

        if not embedded_chunks:
            raise ValueError("Cannot build index from empty chunk list.")

        # ── Extract vectors as a float32 numpy matrix ─────────────────────────
        logger.info(
            f"Building FAISS index for '{repo_name}' "
            f"with {len(embedded_chunks)} vectors..."
        )
        t0 = time.time()

        vectors = np.array(
            [chunk.embedding for chunk in embedded_chunks],
            dtype=np.float32,           # FAISS requires float32
        )                               # shape: (N, embedding_dim)

        dim = vectors.shape[1]

        # ── Build the FAISS index ──────────────────────────────────────────────
        index = self._create_faiss_index(dim)
        index.add(vectors)              # Add all vectors in one call

        elapsed = time.time() - t0
        logger.info(
            f"✅ Index built in {elapsed:.2f}s — "
            f"{index.ntotal} vectors, dim={dim}"
        )

        # ── Build metadata store (everything except the vector) ───────────────
        # We store chunk metadata separately so we can return rich results
        # without having to decode FAISS's internal storage.
        metadata = [
            {
                "chunk_id":    c.chunk_id,
                "repo_name":   c.repo_name,
                "file_path":   c.file_path,
                "language":    c.language,
                "content":     c.content,
                "start_line":  c.start_line,
                "chunk_index": c.chunk_index,
            }
            for c in embedded_chunks
        ]

        # ── Persist to disk ────────────────────────────────────────────────────
        self._save_index(index, metadata, repo_name)

        # ── Cache in memory ────────────────────────────────────────────────────
        self._indices[repo_name] = (index, metadata)

        return self._build_stats(index, repo_name, dim)

    # ── Public: Search ─────────────────────────────────────────────────────────

    def similarity_search(
        self,
        query_vector: np.ndarray,
        repo_name: str,
        top_k: Optional[int] = None,
    ) -> SearchResponse:
        """
        Find the top-k most similar chunks for a query vector.

        Args:
            query_vector: 1D float32 array from CodeEmbedder.embed_query()
            repo_name:    Which repo's index to search
            top_k:        Override default TOP_K_RESULTS if provided

        Returns:
            SearchResponse with ranked SearchResult objects
        """
        k = top_k or self.top_k

        # ── Load index if not cached ───────────────────────────────────────────
        index, metadata = self._load_or_get_index(repo_name)

        # ── Prepare query vector ───────────────────────────────────────────────
        # FAISS expects shape (1, dim) and float32
        query = np.array([query_vector], dtype=np.float32)

        # ── Run FAISS search ───────────────────────────────────────────────────
        t0 = time.time()
        scores, indices = index.search(query, k)
        elapsed = (time.time() - t0) * 1000  # ms

        logger.debug(f"FAISS search completed in {elapsed:.2f}ms")

        # ── Build results ──────────────────────────────────────────────────────
        results: List[SearchResult] = []

        for score, idx in zip(scores[0], indices[0]):
            # FAISS returns -1 for padding if fewer than k results exist
            if idx == -1:
                continue

            # Filter by minimum similarity threshold
            if score < self.min_score:
                logger.debug(f"Skipping result idx={idx} score={score:.3f} (below threshold)")
                continue

            chunk_meta = metadata[idx]
            results.append(
                SearchResult(
                    chunk_id       = chunk_meta["chunk_id"],
                    repo_name      = chunk_meta["repo_name"],
                    file_path      = chunk_meta["file_path"],
                    language       = chunk_meta["language"],
                    content        = chunk_meta["content"],
                    start_line     = chunk_meta["start_line"],
                    chunk_index    = chunk_meta["chunk_index"],
                    similarity_score = round(float(score), 4),
                    relevance      = self._score_to_relevance(float(score)),
                )
            )

        logger.info(
            f"Search on '{repo_name}' returned {len(results)}/{k} results "
            f"(search took {elapsed:.1f}ms)"
        )

        return SearchResponse(
            query="",           # Caller fills this in (routes.py)
            repo_name=repo_name,
            total_results=len(results),
            results=results,
            message=f"Found {len(results)} relevant chunks.",
        )

    # ── Public: Utilities ──────────────────────────────────────────────────────

    def get_index_stats(self, repo_name: str) -> IndexStats:
        """Return statistics for an existing index."""
        index, _ = self._load_or_get_index(repo_name)
        dim = index.d
        return self._build_stats(index, repo_name, dim)

    def list_indexed_repos(self) -> List[str]:
        """Return all repo names that have a persisted index."""
        if not self.store_dir.exists():
            return []
        return [
            d.name
            for d in self.store_dir.iterdir()
            if d.is_dir() and self._index_exists(d.name)
        ]

    def delete_index(self, repo_name: str) -> bool:
        """Delete a repo's index from disk and memory cache."""
        repo_dir = self._get_repo_dir(repo_name)
        if repo_dir.exists():
            import shutil
            shutil.rmtree(repo_dir)
            self._indices.pop(repo_name, None)
            logger.info(f"Deleted index for '{repo_name}'.")
            return True
        return False

    # ── Private: FAISS index creation ─────────────────────────────────────────

    def _create_faiss_index(self, dim: int) -> faiss.Index:
        """
        Create a FAISS index of the configured type.

        IndexFlatIP = Exact Inner Product (cosine similarity when
        vectors are L2-normalised). Best choice for < 100k vectors.
        """
        if settings.FAISS_INDEX_TYPE == "flat":
            # Inner product index — equals cosine similarity for normalised vectors
            index = faiss.IndexFlatIP(dim)
            logger.debug(f"Created IndexFlatIP with dim={dim}")
        else:
            # Default fallback
            index = faiss.IndexFlatL2(dim)
            logger.debug(f"Created IndexFlatL2 with dim={dim}")
        return index

    # ── Private: Persistence ───────────────────────────────────────────────────

    def _get_repo_dir(self, repo_name: str) -> Path:
        """Returns and creates the storage directory for a repo."""
        path = self.store_dir / repo_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _index_exists(self, repo_name: str) -> bool:
        """Check if a persisted index exists for a repo."""
        repo_dir = self.store_dir / repo_name
        return (
            (repo_dir / FAISS_INDEX_FILE).exists()
            and (repo_dir / METADATA_FILE).exists()
        )

    def _save_index(
        self,
        index: faiss.Index,
        metadata: List[dict],
        repo_name: str,
    ) -> None:
        """Persist the FAISS index and metadata to disk."""
        repo_dir = self._get_repo_dir(repo_name)

        # Save FAISS binary index
        index_path = repo_dir / FAISS_INDEX_FILE
        faiss.write_index(index, str(index_path))

        # Save metadata as pickle
        meta_path = repo_dir / METADATA_FILE
        with open(meta_path, "wb") as f:
            pickle.dump(metadata, f)

        index_size_kb = index_path.stat().st_size / 1024
        logger.info(
            f"💾 Index saved to '{repo_dir}' — "
            f"index={index_size_kb:.1f} KB"
        )

    def _load_index(self, repo_name: str) -> Tuple[faiss.Index, List[dict]]:
        """Load a FAISS index and its metadata from disk."""
        if not self._index_exists(repo_name):
            raise FileNotFoundError(
                f"No index found for repo '{repo_name}'. "
                f"Run /ingest-repo first."
            )

        repo_dir = self._get_repo_dir(repo_name)

        logger.info(f"Loading index for '{repo_name}' from disk...")
        t0 = time.time()

        index = faiss.read_index(str(repo_dir / FAISS_INDEX_FILE))

        with open(repo_dir / METADATA_FILE, "rb") as f:
            metadata = pickle.load(f)

        elapsed = time.time() - t0
        logger.info(
            f"✅ Index loaded in {elapsed:.2f}s — "
            f"{index.ntotal} vectors"
        )
        return index, metadata

    def _load_or_get_index(
        self, repo_name: str
    ) -> Tuple[faiss.Index, List[dict]]:
        """
        Return index from memory cache if available,
        otherwise load from disk and cache it.
        """
        if repo_name not in self._indices:
            index, metadata = self._load_index(repo_name)
            self._indices[repo_name] = (index, metadata)
        return self._indices[repo_name]

    # ── Private: Helpers ───────────────────────────────────────────────────────

    def _build_stats(
        self, index: faiss.Index, repo_name: str, dim: int
    ) -> IndexStats:
        """Build an IndexStats object for a given index."""
        repo_dir  = self._get_repo_dir(repo_name)
        index_path = repo_dir / FAISS_INDEX_FILE
        size_kb   = index_path.stat().st_size / 1024 if index_path.exists() else 0.0

        return IndexStats(
            repo_name    = repo_name,
            total_vectors= index.ntotal,
            embedding_dim= dim,
            index_type   = settings.FAISS_INDEX_TYPE,
            index_size_kb= round(size_kb, 2),
            is_trained   = index.is_trained,
        )

    @staticmethod
    def _score_to_relevance(score: float) -> str:
        """
        Convert a cosine similarity score to a human-readable label.
        Thresholds tuned for code similarity search.
        """
        if score >= 0.7:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"