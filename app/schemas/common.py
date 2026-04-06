
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class APIResponse(BaseModel):
    
    success: bool
    message: str
    data: Optional[Any] = None
    request_id: Optional[str] = None
    timestamp: str = ""

    def model_post_init(self, __context) -> None:
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


class ErrorResponse(BaseModel):
    success: bool = False
    error: str                      
    detail: str                     
    request_id: Optional[str] = None
    path: Optional[str] = None
    timestamp: str = ""

    def model_post_init(self, __context) -> None:
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
    embedding_model: str
    embedding_dim: int
    indexed_repos: list[str]
    cache_enabled: bool
    cache_stats: dict
    uptime_seconds: float