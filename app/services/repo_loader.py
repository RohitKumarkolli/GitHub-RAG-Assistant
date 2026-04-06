
import shutil
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import git  

from app.core.config import settings
from app.schemas.repo import CodeFile, RepoLoadResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",    ".js": "javascript", ".ts": "typescript",
    ".jsx": "jsx",      ".tsx": "tsx",       ".java": "java",
    ".cpp": "cpp",      ".c": "c",           ".go": "go",
    ".rb": "ruby",      ".rs": "rust",       ".md": "markdown",
    ".txt": "text",     ".yaml": "yaml",     ".yml": "yaml",
    ".json": "json",    ".toml": "toml",     ".sh": "shell",
}


class RepoLoader:
    """
    Handles all repository ingestion logic:
      1. Clone a GitHub repo  OR  validate a local path
      2. Walk the directory tree
      3. Filter files by extension and size
      4. Read and return structured CodeFile objects
    """

    def __init__(self):
        self.repos_dir = settings.REPOS_DIR
        self.supported_ext = set(settings.SUPPORTED_EXTENSIONS)
        self.excluded_dirs = set(settings.EXCLUDED_DIRS)
        self.max_file_size = settings.MAX_FILE_SIZE_BYTES


    def load(
        self,
        repo_url: Optional[str] = None,
        local_path: Optional[str] = None,
        branch: str = "main",
    ) -> RepoLoadResponse:
        """
        Main entry point. Resolves source, scans files, returns structured data.
        Args:
            repo_url:   GitHub HTTPS URL (e.g. https://github.com/user/repo)
            local_path: Absolute or relative path to a local repository
            branch:     Git branch to clone (ignored for local paths)

        Returns:
            RepoLoadResponse with metadata and list of CodeFile objects
        """
        if repo_url:
            repo_path, repo_name = self._clone_repo(repo_url, branch)
        elif local_path:
            repo_path, repo_name = self._validate_local_path(local_path)
        else:
            raise ValueError("Provide either repo_url or local_path.")

        logger.info(f"Scanning repository: '{repo_name}' at {repo_path}")
        code_files = self._scan_files(repo_path, repo_name)

        total_size = sum(f.size_bytes for f in code_files)
        logger.info(
            f" Loaded {len(code_files)} files "
            f"({total_size / 1024:.1f} KB) from '{repo_name}'"
        )

        return RepoLoadResponse(
            repo_name=repo_name,
            total_files=len(code_files),
            total_size_bytes=total_size,
            files=code_files,
            message=f"Successfully loaded {len(code_files)} files from '{repo_name}'.",
        )


    def _clone_repo(self, repo_url: str, branch: str) -> tuple[Path, str]:
        
        repo_name = self._extract_repo_name(repo_url)
        clone_path = self.repos_dir / repo_name

        if clone_path.exists():
            logger.info(f"Repo '{repo_name}' already cloned. Pulling latest changes...")
            try:
                repo = git.Repo(clone_path)
                repo.remotes.origin.pull()
                logger.info(f"Pull successful for '{repo_name}'.")
            except git.GitCommandError as e:
                logger.warning(f"Pull failed (using cached version): {e}")
        else:
            logger.info(f"Cloning '{repo_url}' → branch='{branch}' → {clone_path}")
            try:
                git.Repo.clone_from(
                    url=repo_url,
                    to_path=clone_path,
                    branch=branch,
                    depth=1,          
                )
                logger.info(f"Clone complete: {clone_path}")
            except git.GitCommandError as e:
                if clone_path.exists():
                    shutil.rmtree(clone_path)
                raise RuntimeError(f"Failed to clone repository: {e}") from e

        return clone_path, repo_name

    def _validate_local_path(self, local_path: str) -> tuple[Path, str]:
        
        path = Path(local_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Local path not found: {path}")
        if not path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")

        logger.info(f"Using local repository at: {path}")
        return path, path.name


    def _scan_files(self, repo_path: Path, repo_name: str) -> List[CodeFile]:
        
        code_files: List[CodeFile] = []
        skipped_count = 0

        for file_path in repo_path.rglob("*"):
            if file_path.is_dir():
                continue

            if any(excluded in file_path.parts for excluded in self.excluded_dirs):
                continue

            if file_path.suffix.lower() not in self.supported_ext:
                skipped_count += 1
                continue

            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                logger.debug(f"Skipping large file: {file_path} ({file_size} bytes)")
                skipped_count += 1
                continue

            if file_size == 0:
                skipped_count += 1
                continue

            content = self._read_file(file_path)
            if content is None:
                skipped_count += 1
                continue

            relative_path = str(file_path.relative_to(repo_path))
            language = EXTENSION_TO_LANGUAGE.get(file_path.suffix.lower(), "unknown")

            code_files.append(
                CodeFile(
                    file_path=relative_path,
                    content=content,
                    language=language,
                    size_bytes=file_size,
                    repo_name=repo_name,
                )
            )

        logger.info(
            f"Scan complete — {len(code_files)} files loaded, "
            f"{skipped_count} files skipped."
        )
        return code_files

    def _read_file(self, file_path: Path) -> Optional[str]:
        
        try:
            return file_path.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError:
            logger.debug(f"Skipping binary/non-UTF8 file: {file_path}")
            return None
        except OSError as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return None

    @staticmethod
    def _extract_repo_name(repo_url: str) -> str:
        """
        Extracts a clean folder name from a GitHub URL.
        Example:
            "https://github.com/tiangolo/fastapi.git" → "fastapi"
            "https://github.com/tiangolo/fastapi"     → "fastapi"
        """
        
        parsed = urlparse(repo_url)
        name = parsed.path.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name