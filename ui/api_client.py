# ui/api_client.py

import requests
from typing import Optional
import streamlit as st

# Backend URL — overridden by environment variable in Docker
API_BASE_URL = "https://kollirohitkuamr-github-rag-api.hf.space"

def get_api_url() -> str:
    """Get API URL from Streamlit secrets or default."""
    try:
        return st.secrets.get("API_BASE_URL", API_BASE_URL)
    except Exception:
        return API_BASE_URL


class APIClient:
    """
    Wrapper around the FastAPI backend.
    All HTTP calls go through here — easy to swap base URL for deployment.
    """

    def __init__(self):
        self.base_url = get_api_url()
        self.timeout  = 300     # 5 min — ingestion can be slow

    # ── Health ─────────────────────────────────────────────────────────────────

    def health(self) -> dict:
        try:
            r = requests.get(f"{self.base_url}/health", timeout=10)
            return r.json()
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    # ── Ingestion ──────────────────────────────────────────────────────────────

    def ingest_repo(
        self,
        repo_url: Optional[str] = None,
        local_path: Optional[str] = None,
        branch: str = "main",
    ) -> dict:
        payload = {"branch": branch}
        if repo_url:
            payload["repo_url"] = repo_url
        if local_path:
            payload["local_path"] = local_path

        try:
            r = requests.post(
                f"{self.base_url}/ingest-repo",
                json=payload,
                timeout=self.timeout,
            )
            return {"success": r.status_code == 200, "data": r.json()}
        except Exception as e:
            return {"success": False, "data": {"detail": str(e)}}

    # ── RAG ────────────────────────────────────────────────────────────────────

    def ask(
        self,
        repo_name: str,
        question: str,
        top_k: Optional[int] = None,
        include_sources: bool = True,
    ) -> dict:
        payload = {
            "repo_name": repo_name,
            "question": question,
            "include_sources": include_sources,
        }
        if top_k:
            payload["top_k"] = top_k

        try:
            r = requests.post(
                f"{self.base_url}/ask",
                json=payload,
                timeout=self.timeout,
            )
            return {"success": r.status_code == 200, "data": r.json()}
        except Exception as e:
            return {"success": False, "data": {"detail": str(e)}}

    # ── Repos ──────────────────────────────────────────────────────────────────

    def list_repos(self) -> list:
        try:
            r = requests.get(f"{self.base_url}/repos", timeout=10)
            return r.json().get("indexed_repos", [])
        except Exception:
            return []

    def get_repo_stats(self, repo_name: str) -> dict:
        try:
            r = requests.get(f"{self.base_url}/repos/{repo_name}/stats", timeout=10)
            return r.json()
        except Exception as e:
            return {"detail": str(e)}

    def delete_repo(self, repo_name: str) -> dict:
        try:
            r = requests.delete(f"{self.base_url}/repos/{repo_name}", timeout=10)
            return {"success": r.status_code == 200, "data": r.json()}
        except Exception as e:
            return {"success": False, "data": {"detail": str(e)}}

    # ── Cache ──────────────────────────────────────────────────────────────────

    def get_cache_stats(self) -> dict:
        try:
            r = requests.get(f"{self.base_url}/cache/stats", timeout=10)
            return r.json()
        except Exception:
            return {}

    def clear_cache(self) -> bool:
        try:
            r = requests.delete(f"{self.base_url}/cache", timeout=10)
            return r.status_code == 200
        except Exception:
            return False


# Singleton — import this everywhere in the UI
client = APIClient()
