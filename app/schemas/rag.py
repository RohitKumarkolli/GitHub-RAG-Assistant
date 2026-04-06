
from pydantic import BaseModel
from typing import List, Optional
from app.schemas.search import SearchResult


class AskRequest(BaseModel):
    
    repo_name: str                      
    question: str                       
    top_k: Optional[int] = None         
    include_sources: bool = True        


class SourceReference(BaseModel):
    
    file_path: str
    language: str
    start_line: int
    similarity_score: float
    relevance: str
    snippet: str


class AskResponse(BaseModel):
    question: str
    answer: str                         
    repo_name: str
    sources: List[SourceReference]      
    total_sources_used: int
    model_used: str                     
    retrieval_scores: List[float]       
    message: str


class RAGDebugInfo(BaseModel):
    
    prompt_length_chars: int
    chunks_retrieved: int
    chunks_used_in_prompt: int          
    query_vector_norm: float            