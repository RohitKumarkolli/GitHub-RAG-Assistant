
import time
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.schemas.chunk import CodeChunk
from app.schemas.embeddings import EmbeddedChunk, EmbeddingResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CodeEmbedder:
    

    def __init__(
        self,
        model_name: str = settings.EMBEDDING_MODEL,
        device: str = settings.EMBEDDING_DEVICE,
        batch_size: int = settings.EMBEDDING_BATCH_SIZE,
        normalize: bool = settings.NORMALIZE_EMBEDDINGS,
    ):
        self.model_name = model_name
        self.batch_size = batch_size
        self.normalize = normalize

        logger.info(f"Loading embedding model '{model_name}' on device='{device}'...")
        t0 = time.time()

        self._model = SentenceTransformer(model_name, device=device)

        elapsed = time.time() - t0
        self.embedding_dim = self._model.get_sentence_embedding_dimension()

        logger.info(
            f"✅ Model loaded in {elapsed:.2f}s — "
            f"embedding_dim={self.embedding_dim}, "
            f"batch_size={batch_size}"
        )


    def embed_chunks(self, chunks: List[CodeChunk]) -> EmbeddingResult:
        
        if not chunks:
            logger.warning("embed_chunks called with empty list.")
            return EmbeddingResult(
                repo_name="unknown",
                total_chunks_embedded=0,
                embedding_dim=self.embedding_dim,
                model_name=self.model_name,
                embedded_chunks=[],
                message="No chunks provided.",
            )

        repo_name = chunks[0].repo_name
        logger.info(
            f"Embedding {len(chunks)} chunks from '{repo_name}' "
            f"in batches of {self.batch_size}..."
        )

        texts = [
            self._build_embed_text(chunk)
            for chunk in chunks
        ]

        t0 = time.time()
        vectors: np.ndarray = self._model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=True,     # Visible progress in terminal
            convert_to_numpy=True,
        )
        elapsed = time.time() - t0

        logger.info(
            f"Encoding complete in {elapsed:.2f}s — "
            f"shape={vectors.shape} "
            f"({elapsed/len(chunks)*1000:.1f} ms/chunk)"
        )

        embedded_chunks = self._build_embedded_chunks(chunks, vectors)

        assert vectors.shape[1] == self.embedding_dim, (
            f"Dimension mismatch: got {vectors.shape[1]}, "
            f"expected {self.embedding_dim}"
        )

        return EmbeddingResult(
            repo_name=repo_name,
            total_chunks_embedded=len(embedded_chunks),
            embedding_dim=self.embedding_dim,
            model_name=self.model_name,
            embedded_chunks=embedded_chunks,
            message=(
                f"Successfully embedded {len(embedded_chunks)} chunks "
                f"using '{self.model_name}'."
            ),
        )

    def embed_query(self, query: str) -> np.ndarray:
        
        logger.debug(f"Embedding query: '{query[:80]}...'")
        vector: np.ndarray = self._model.encode(
            [query],                            # Model expects a list
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
        )
        return vector[0]                        # Return 1D array


    @staticmethod
    def _build_embed_text(chunk: CodeChunk) -> str:
        
        return (
            f"# {chunk.language} {chunk.file_path}\n"
            f"{chunk.content}"
        )

    @staticmethod
    def _build_embedded_chunks(
        chunks: List[CodeChunk],
        vectors: np.ndarray,
    ) -> List[EmbeddedChunk]:
        
        embedded: List[EmbeddedChunk] = []
        for chunk, vector in zip(chunks, vectors):
            embedded.append(
                EmbeddedChunk(
                    chunk_id=chunk.chunk_id,
                    repo_name=chunk.repo_name,
                    file_path=chunk.file_path,
                    language=chunk.language,
                    chunk_index=chunk.chunk_index,
                    start_line=chunk.start_line,
                    content=chunk.content,
                    embedding=vector.tolist(),   # np.ndarray → List[float]
                )
            )
        return embedded