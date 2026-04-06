
from pydantic import BaseModel
from typing import List
import numpy as np


class EmbeddedChunk(BaseModel):
    
    chunk_id: str
    repo_name: str
    file_path: str
    language: str
    chunk_index: int
    start_line: int

    content: str                    

    embedding: List[float]

    class Config:
        arbitrary_types_allowed = True


class EmbeddingResult(BaseModel):
    
    repo_name: str
    total_chunks_embedded: int
    embedding_dim: int              
    model_name: str
    embedded_chunks: List[EmbeddedChunk]
    message: str