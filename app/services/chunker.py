
import re
import hashlib
from typing import List, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.schemas.repo import CodeFile
from app.schemas.chunk import CodeChunk, ChunkingResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


LANGUAGE_SPLIT_PATTERNS: dict[str, list[str]] = {
    "python": [
        r"\nclass\s+\w+",           # class MyClass:
        r"\ndef\s+\w+",             # def my_function(
        r"\nasync\s+def\s+\w+",     # async def my_coroutine(
    ],
    "javascript": [
        r"\nclass\s+\w+",           # class MyClass
        r"\nfunction\s+\w+",        # function myFunc(
        r"\nconst\s+\w+\s*=\s*(?:async\s*)?\(",  # const fn = (
        r"\nmodule\.exports",       # module.exports =
    ],
    "typescript": [
        r"\nclass\s+\w+",
        r"\nfunction\s+\w+",
        r"\nconst\s+\w+\s*=\s*(?:async\s*)?\(",
        r"\ninterface\s+\w+",       # interface MyInterface
        r"\ntype\s+\w+\s*=",        # type MyType =
        r"\nexport\s+(?:default\s+)?(?:class|function|const)",
    ],
    "java": [
        r"\n\s*public\s+class\s+\w+",
        r"\n\s*(?:public|private|protected)\s+\w+\s+\w+\s*\(",
        r"\n\s*interface\s+\w+",
    ],
    "go": [
        r"\nfunc\s+\w+",            # func myFunc(
        r"\ntype\s+\w+\s+struct",   # type MyStruct struct
        r"\ntype\s+\w+\s+interface",
    ],
    "rust": [
        r"\nfn\s+\w+",              # fn my_function(
        r"\npub\s+fn\s+\w+",        # pub fn my_function(
        r"\nstruct\s+\w+",
        r"\nimpl\s+\w+",
        r"\ntrait\s+\w+",
    ],
    "cpp": [
        r"\nclass\s+\w+",
        r"\n\w+\s+\w+::\w+\s*\(",   # ReturnType ClassName::method(
        r"\nvoid\s+\w+\s*\(",
    ],
}

SIMPLE_SPLIT_LANGUAGES = {"markdown", "text", "yaml", "json", "toml", "shell"}


class CodeChunker:
    

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        
        self._recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

        logger.info(
            f"CodeChunker initialized — chunk_size={chunk_size}, "
            f"overlap={chunk_overlap}"
        )


    def chunk_files(self, code_files: List[CodeFile]) -> ChunkingResult:
        
        all_chunks: List[CodeChunk] = []
        repo_name = code_files[0].repo_name if code_files else "unknown"

        logger.info(f"Starting chunking for {len(code_files)} files...")

        for code_file in code_files:
            try:
                file_chunks = self._chunk_single_file(code_file)
                all_chunks.extend(file_chunks)
            except Exception as e:
                logger.warning(f"Failed to chunk {code_file.file_path}: {e}")
                continue

        total = len(all_chunks)
        avg_size = (
            sum(c.size_chars for c in all_chunks) / total if total > 0 else 0
        )

        logger.info(
            f"✅ Chunking complete — {total} chunks from "
            f"{len(code_files)} files (avg {avg_size:.0f} chars/chunk)"
        )

        return ChunkingResult(
            repo_name=repo_name,
            total_files_processed=len(code_files),
            total_chunks=total,
            avg_chunk_size_chars=round(avg_size, 2),
            chunks=all_chunks,
            message=f"Generated {total} chunks from {len(code_files)} files.",
        )


    def _chunk_single_file(self, code_file: CodeFile) -> List[CodeChunk]:
        
        content = code_file.content.strip()
        if not content:
            return []

        language = code_file.language

        if language in LANGUAGE_SPLIT_PATTERNS:
            raw_chunks = self._structure_aware_split(content, language)
        else:
            raw_chunks = self._recursive_splitter.split_text(content)

        refined_chunks = self._refine_oversized_chunks(raw_chunks)

        return self._build_code_chunks(refined_chunks, code_file)

    def _structure_aware_split(
        self, content: str, language: str
    ) -> List[str]:
        
        patterns = LANGUAGE_SPLIT_PATTERNS.get(language, [])

        boundary_positions = set([0])  
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                boundary_positions.add(match.start())

        
        sorted_positions = sorted(boundary_positions)
        sorted_positions.append(len(content))  

        segments: List[str] = []
        for i in range(len(sorted_positions) - 1):
            start = sorted_positions[i]
            end = sorted_positions[i + 1]
            segment = content[start:end].strip()
            if segment:
                segments.append(segment)

        
        if len(segments) <= 1:
            logger.debug(
                f"No structure boundaries found for {language}, "
                f"using recursive split."
            )
            return self._recursive_splitter.split_text(content)

        return segments

    def _refine_oversized_chunks(self, chunks: List[str]) -> List[str]:
        
        refined: List[str] = []
        for chunk in chunks:
            if len(chunk) > self.chunk_size:
                
                sub_chunks = self._recursive_splitter.split_text(chunk)
                refined.extend(sub_chunks)
            else:
                refined.append(chunk)
        return refined

    def _build_code_chunks(
        self, raw_texts: List[str], code_file: CodeFile
    ) -> List[CodeChunk]:
        
        chunks: List[CodeChunk] = []
        total = len(raw_texts)

        line_start_positions = self._build_line_index(code_file.content)

        for idx, text in enumerate(raw_texts):
            if not text.strip():
                continue

            char_pos = code_file.content.find(text[:50])  
            start_line = self._char_pos_to_line(char_pos, line_start_positions)

            chunk_id = self._make_chunk_id(
                code_file.repo_name, code_file.file_path, idx
            )

            chunks.append(
                CodeChunk(
                    chunk_id=chunk_id,
                    repo_name=code_file.repo_name,
                    file_path=code_file.file_path,
                    language=code_file.language,
                    content=text,
                    chunk_index=idx,
                    total_chunks=total,
                    start_line=start_line,
                    size_chars=len(text),
                )
            )

        return chunks


    @staticmethod
    def _build_line_index(content: str) -> List[int]:
        
        positions = [0]
        for i, char in enumerate(content):
            if char == "\n":
                positions.append(i + 1)
        return positions

    @staticmethod
    def _char_pos_to_line(char_pos: int, line_positions: List[int]) -> int:
        
        if char_pos < 0 or not line_positions:
            return 1
        lo, hi = 0, len(line_positions) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if line_positions[mid] <= char_pos:
                lo = mid + 1
            else:
                hi = mid - 1
        return max(1, lo)  

    @staticmethod
    def _make_chunk_id(repo_name: str, file_path: str, index: int) -> str:
        
        raw = f"{repo_name}:{file_path}:{index}"
        short_hash = hashlib.md5(raw.encode()).hexdigest()[:8]
        return f"{short_hash}:{index}"