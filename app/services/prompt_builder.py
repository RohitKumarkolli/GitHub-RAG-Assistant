# app/services/prompt_builder.py

from typing import List
from app.schemas.search import SearchResult
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── System prompt ─────────────────────────────────────────────────────────────
# This is sent as the "system" role in Anthropic's API.
# It defines the assistant's persona, constraints, and output format.

SYSTEM_PROMPT = """You are an expert software engineer and code analyst assistant.

Your job is to answer questions about a specific GitHub repository's codebase.

## How you work:
- You are given CONTEXT: a set of relevant code chunks retrieved from the repository
- You answer questions based ONLY on the provided context
- You cite specific files and line numbers when relevant
- You explain code clearly, as if teaching a junior developer

## Rules:
- If the answer is not found in the context, say: "I could not find relevant information in the provided code context."
- Never hallucinate or invent code that isn't in the context
- Always mention which file(s) your answer comes from
- Format code snippets using markdown code blocks with the correct language tag
- Be concise but complete — don't pad your answer unnecessarily

## Output format:
1. Direct answer to the question
2. Relevant code snippets (if applicable)
3. File references (file path + line number)
"""


class PromptBuilder:
    """
    Constructs LLM prompts from retrieved search results.

    Responsibilities:
    - Format code chunks into readable context blocks
    - Respect the MAX_CONTEXT_CHARS limit to avoid token overflow
    - Produce consistent, well-structured prompts
    """

    def __init__(self, max_context_chars: int = settings.MAX_CONTEXT_CHARS):
        self.max_context_chars = max_context_chars

    # ── Public API ─────────────────────────────────────────────────────────────

    def build_prompt(
        self,
        question: str,
        search_results: List[SearchResult],
        repo_name: str,
    ) -> tuple[str, int]:
        """
        Build the full user prompt from question + retrieved chunks.

        Args:
            question:       The user's question
            search_results: Top-k chunks from FAISS search
            repo_name:      Name of the repository being queried

        Returns:
            Tuple of (prompt_text, number_of_chunks_used)
        """
        if not search_results:
            # No context found — tell LLM to say so honestly
            prompt = self._build_no_context_prompt(question, repo_name)
            return prompt, 0

        # Build context block, respecting character limits
        context_block, chunks_used = self._build_context_block(search_results)

        # Assemble the final prompt
        prompt = self._assemble_prompt(question, context_block, repo_name)

        logger.debug(
            f"Prompt built — {chunks_used} chunks used, "
            f"{len(prompt)} total chars"
        )
        return prompt, chunks_used

    def get_system_prompt(self) -> str:
        """Return the system prompt (used for Anthropic API's system field)."""
        return SYSTEM_PROMPT

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_context_block(
        self, results: List[SearchResult]
    ) -> tuple[str, int]:
        """
        Format retrieved chunks into a readable context block.

        Each chunk is shown with:
        - Its rank and relevance score
        - File path and starting line number
        - Language-tagged code block

        Stops adding chunks once MAX_CONTEXT_CHARS is reached.

        Returns:
            (formatted context string, number of chunks included)
        """
        context_parts: List[str] = []
        total_chars = 0
        chunks_used = 0

        for i, result in enumerate(results, start=1):
            chunk_text = self._format_single_chunk(i, result)
            chunk_chars = len(chunk_text)

            # Stop if adding this chunk would exceed our limit
            if total_chars + chunk_chars > self.max_context_chars:
                logger.debug(
                    f"Context limit reached at chunk {i} "
                    f"({total_chars} chars). Stopping."
                )
                break

            context_parts.append(chunk_text)
            total_chars += chunk_chars
            chunks_used += 1

        return "\n\n".join(context_parts), chunks_used

    @staticmethod
    def _format_single_chunk(rank: int, result: SearchResult) -> str:
        """
        Format a single search result into a readable block.

        Example output:
            ### [1] app/services/auth.py (line 42) | python | score: 0.87
```python
            def verify_token(token: str) -> dict:
                ...
```
        """
        return (
            f"### [{rank}] {result.file_path} "
            f"(line {result.start_line}) | "
            f"{result.language} | "
            f"relevance: {result.relevance} (score: {result.similarity_score})\n"
            f"```{result.language}\n"
            f"{result.content}\n"
            f"```"
        )

    @staticmethod
    def _assemble_prompt(
        question: str,
        context_block: str,
        repo_name: str,
    ) -> str:
        """
        Assemble the final user message from its parts.

        Structure:
            REPOSITORY INFO
            ───────────────
            CONTEXT (retrieved chunks)
            ───────────────
            QUESTION
        """
        return f"""## Repository: `{repo_name}`

## Retrieved Code Context:
The following code chunks were retrieved from the repository as the most relevant to your question.

{context_block}

---

## Question:
{question}

## Your Answer:
Based on the code context above, please answer the question. \
Reference specific files and line numbers where relevant."""

    @staticmethod
    def _build_no_context_prompt(question: str, repo_name: str) -> str:
        """Prompt to use when FAISS returns no results above threshold."""
        return f"""## Repository: `{repo_name}`

## Retrieved Code Context:
No relevant code chunks were found for this question.

## Question:
{question}

## Your Answer:
Since no relevant context was retrieved, explain that you cannot \
find related code in the repository and suggest the user rephrase their question."""