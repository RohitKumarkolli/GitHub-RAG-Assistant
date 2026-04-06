
from pydantic import BaseModel
from typing import Optional


class CodeChunk(BaseModel):
    
    chunk_id: str           
    repo_name: str          
    file_path: str          
    language: str           
    content: str            
    chunk_index: int        
    total_chunks: int       
    start_line: int         
    size_chars: int         


class ChunkingResult(BaseModel):
    
    repo_name: str
    total_files_processed: int
    total_chunks: int
    avg_chunk_size_chars: float
    chunks: list[CodeChunk]
    message: str