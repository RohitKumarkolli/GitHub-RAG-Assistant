
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List


class Settings(BaseSettings):

    APP_NAME: str = "GitHub RAG Assistant"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    REPOS_DIR: Path = BASE_DIR / "data" / "repos"
    VECTOR_STORE_DIR: Path = BASE_DIR / "vector_store"

    SUPPORTED_EXTENSIONS: List[str] = [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".html",
        ".cpp", ".c", ".go", ".rb", ".rs", ".md", ".css"
        ".txt", ".yaml", ".yml", ".json", ".toml", ".sh",
    ]
    EXCLUDED_DIRS: List[str] = [
        ".git", "__pycache__", "node_modules", ".venv",
        "venv", "env", ".env", "dist", "build", ".idea",
        ".vscode", "*.egg-info", ".mypy_cache", ".pytest_cache",
    ]
    MAX_FILE_SIZE_BYTES: int = 500_000

    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE: int = 32
    NORMALIZE_EMBEDDINGS: bool = True
    EMBEDDING_DEVICE: str = "cpu"

    TOP_K_RESULTS: int = 5
    MIN_SIMILARITY_SCORE: float = 0.0
    FAISS_INDEX_TYPE: str = "flat"

    LLM_PROVIDER: str = "groq"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MAX_TOKENS: int = 1024
    GROQ_TEMPERATURE: float = 0.2

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-haiku-20240307"
    ANTHROPIC_MAX_TOKENS: int = 1024

    HF_LLM_MODEL: str = "google/flan-t5-large"
    HF_MAX_NEW_TOKENS: int = 512
    HF_DEVICE: str = "cpu"

    MAX_CONTEXT_CHARS: int = 6000

    CACHE_ENABLED: bool = True

    CACHE_TTL_SECONDS: int = 3600

    CACHE_MAX_SIZE: int = 100

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
settings.REPOS_DIR.mkdir(parents=True, exist_ok=True)
settings.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)