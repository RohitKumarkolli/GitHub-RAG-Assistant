
from pydantic import BaseModel
from typing import List, Optional


class SearchResult(BaseModel):
    
    chunk_id: str
    repo_name: str
    file_path: str
    language: str
    content: str
    start_line: int
    chunk_index: int

    similarity_score: float

    relevance: str          


class SearchResponse(BaseModel):
    
    query: str
    repo_name: str
    total_results: int
    results: List[SearchResult]
    message: str


class IndexStats(BaseModel):
    
    repo_name: str
    total_vectors: int
    embedding_dim: int
    index_type: str
    index_size_kb: float
    is_trained: bool