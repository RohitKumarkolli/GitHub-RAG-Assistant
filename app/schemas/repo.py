
from pydantic import BaseModel, field_validator, HttpUrl
from typing import Optional
from pathlib import Path


class RepoLoadRequest(BaseModel):
    
    repo_url: Optional[str] = None          
    local_path: Optional[str] = None        
    branch: Optional[str] = "main"          

    @field_validator("repo_url", "local_path", mode="before")
    @classmethod
    def at_least_one_source(cls, v, info):
        return v

    def model_post_init(self, __context) -> None:
        if not self.repo_url and not self.local_path:
            raise ValueError("Provide either 'repo_url' or 'local_path'.")


class CodeFile(BaseModel):
    
    file_path: str          
    content: str            
    language: str           
    size_bytes: int         
    repo_name: str          


class RepoLoadResponse(BaseModel):
    
    repo_name: str
    total_files: int
    total_size_bytes: int
    files: list[CodeFile]
    message: str