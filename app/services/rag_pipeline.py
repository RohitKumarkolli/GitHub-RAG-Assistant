# app/services/rag_pipeline.py

import time
from typing import Optional

from app.core.config import settings
from app.schemas.rag import AskRequest, AskResponse, SourceReference
from app.schemas.search import SearchResult
from app.services.embedder import CodeEmbedder
from app.services.vector_store import FAISSVectorStore
from app.services.prompt_builder import PromptBuilder
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RAGPipeline:
    """
    Orchestrates the full RAG pipeline:
    Embed → Retrieve → Prompt → Generate → Respond

    Supports three LLM backends:
      - Groq       (recommended — free, fast, powerful Llama3/Mixtral)
      - Anthropic  (best quality — requires paid credits)
      - HuggingFace (local fallback — no API key needed)
    """

    def __init__(
        self,
        embedder: CodeEmbedder,
        vector_store: FAISSVectorStore,
    ):
        self.embedder       = embedder
        self.vector_store   = vector_store
        self.prompt_builder = PromptBuilder()
        self.llm_provider   = settings.LLM_PROVIDER
        self._llm_client    = self._init_llm()

        logger.info(
            f"RAGPipeline initialised — provider='{self.llm_provider}'"
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def ask(self, request: AskRequest) -> AskResponse:
        """Main entry point — answer a question about a repository."""
        t0 = time.time()
        logger.info(
            f"RAG query — repo='{request.repo_name}', "
            f"question='{request.question[:80]}...'"
        )

        # Step 1: Embed the question
        query_vector = self.embedder.embed_query(request.question)

        # Step 2: Retrieve relevant chunks
        search_response = self.vector_store.similarity_search(
            query_vector=query_vector,
            repo_name=request.repo_name,
            top_k=request.top_k,
        )
        retrieved_chunks = search_response.results
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks from vector store.")

        # Step 3: Build prompt
        prompt, chunks_used = self.prompt_builder.build_prompt(
            question=request.question,
            search_results=retrieved_chunks,
            repo_name=request.repo_name,
        )

        # Step 4: Generate answer
        answer, model_used = self._generate_answer(prompt)

        # Step 5: Build structured response
        sources = self._build_sources(retrieved_chunks, request.include_sources)
        elapsed = time.time() - t0

        logger.info(
            f"✅ RAG complete in {elapsed:.2f}s — "
            f"provider={self.llm_provider}, chunks_used={chunks_used}"
        )

        return AskResponse(
            question=request.question,
            answer=answer,
            repo_name=request.repo_name,
            sources=sources,
            total_sources_used=len(sources),
            model_used=model_used,
            retrieval_scores=[r.similarity_score for r in retrieved_chunks],
            message=(
                f"Answer generated using {chunks_used} context chunks "
                f"via {self.llm_provider}."
            ),
        )

    # ── LLM Initialisation ─────────────────────────────────────────────────────

    def _init_llm(self):
        """Initialise the correct LLM backend from config."""
        if self.llm_provider == "groq":
            return self._init_groq()
        elif self.llm_provider == "anthropic":
            return self._init_anthropic()
        elif self.llm_provider == "huggingface":
            return self._init_huggingface()
        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER='{self.llm_provider}'. "
                "Valid options: 'groq', 'anthropic', 'huggingface'"
            )

    def _init_groq(self):
        """
        Initialise the Groq client.
        Free tier at https://console.groq.com — no credit card needed.
        """
        try:
            from groq import Groq
        except ImportError:
            raise ImportError(
                "groq package not installed. Run: pip install groq"
            )

        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set in .env.\n"
                "Get your free key at: https://console.groq.com"
            )

        client = Groq(api_key=settings.GROQ_API_KEY)
        logger.info(
            f"✅ Groq client ready — model='{settings.GROQ_MODEL}'"
        )
        return client

    def _init_anthropic(self):
        """Initialise the Anthropic client."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("Run: pip install 'anthropic>=0.40.0'")

        if not settings.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not set in .env. "
                "Tip: Switch to Groq (free) by setting LLM_PROVIDER=groq"
            )

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        logger.info(
            f"Anthropic client ready — model='{settings.ANTHROPIC_MODEL}'"
        )
        return client

    def _init_huggingface(self):
        """Load a local HuggingFace model — no API key needed."""
        try:
            from transformers import pipeline as hf_pipeline
        except ImportError:
            raise ImportError("Run: pip install transformers")

        logger.info(
            f"Loading HuggingFace model '{settings.HF_LLM_MODEL}'... "
            "(may take 1-2 minutes on first run)"
        )
        pipe = hf_pipeline(
            "text2text-generation",
            model=settings.HF_LLM_MODEL,
            device=settings.HF_DEVICE,
            max_new_tokens=settings.HF_MAX_NEW_TOKENS,
        )
        logger.info(f"✅ HuggingFace model loaded: '{settings.HF_LLM_MODEL}'")
        return pipe

    # ── Answer Generation ──────────────────────────────────────────────────────

    def _generate_answer(self, prompt: str) -> tuple[str, str]:
        """Route to the correct LLM backend."""
        if self.llm_provider == "groq":
            return self._call_groq(prompt)
        elif self.llm_provider == "anthropic":
            return self._call_anthropic(prompt)
        else:
            return self._call_huggingface(prompt)

    def _call_groq(self, prompt: str) -> tuple[str, str]:
        """
        Call Groq's API.

        Groq uses an OpenAI-compatible interface.
        Uses system + user message format — same as Anthropic.
        """
        try:
            logger.debug(
                f"Calling Groq — model={settings.GROQ_MODEL}, "
                f"prompt_len={len(prompt)} chars"
            )

            response = self._llm_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": self.prompt_builder.get_system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                max_tokens=settings.GROQ_MAX_TOKENS,
                temperature=settings.GROQ_TEMPERATURE,
            )

            answer   = response.choices[0].message.content.strip()
            model_id = f"groq/{settings.GROQ_MODEL}"

            # Log token usage for monitoring
            if hasattr(response, "usage") and response.usage:
                logger.info(
                    f"Groq token usage — "
                    f"input={response.usage.prompt_tokens}, "
                    f"output={response.usage.completion_tokens}"
                )

            return answer, model_id

        except Exception as e:
            error_str = str(e)
            logger.error(f"Groq API call failed — raw error: {error_str}")

            if "invalid_api_key" in error_str.lower() or "401" in error_str:
                raise RuntimeError(
                    "Groq API error: Invalid API key. "
                    "Check GROQ_API_KEY in your .env file."
                )
            elif "rate_limit" in error_str.lower() or "429" in error_str:
                raise RuntimeError(
                    "Groq API error: Rate limit hit. "
                    "Wait a moment and try again (free tier limits apply)."
                )
            elif "model_not_found" in error_str.lower() or "404" in error_str:
                raise RuntimeError(
                    f"Groq API error: Model '{settings.GROQ_MODEL}' not found. "
                    "Valid models: llama3-8b-8192, llama3-70b-8192, "
                    "mixtral-8x7b-32768"
                )
            else:
                raise RuntimeError(f"Groq API error: {error_str}") from e

    def _call_anthropic(self, prompt: str) -> tuple[str, str]:
        """Call Anthropic Claude API."""
        try:
            response = self._llm_client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=settings.ANTHROPIC_MAX_TOKENS,
                system=self.prompt_builder.get_system_prompt(),
                messages=[{"role": "user", "content": prompt}],
            )
            answer   = response.content[0].text
            model_id = f"anthropic/{settings.ANTHROPIC_MODEL}"
            return answer, model_id

        except Exception as e:
            error_str = str(e)
            logger.error(f"Anthropic API call failed — raw error: {error_str}")
            if "credit balance is too low" in error_str:
                raise RuntimeError(
                    "Anthropic API error: Credit balance too low. "
                    "Switch to Groq (free): set LLM_PROVIDER=groq in .env"
                )
            raise RuntimeError(f"Anthropic API error: {error_str}") from e

    def _call_huggingface(self, prompt: str) -> tuple[str, str]:
        """Call local HuggingFace model."""
        try:
            condensed = self._condense_for_hf(prompt)
            outputs   = self._llm_client(condensed)
            answer    = outputs[0]["generated_text"].strip()
            model_id  = f"huggingface/{settings.HF_LLM_MODEL}"

            if not answer or len(answer) < 5:
                answer = (
                    "The local model could not generate a detailed answer. "
                    "Switch to Groq for much better results: "
                    "set LLM_PROVIDER=groq in .env"
                )
            return answer, model_id

        except Exception as e:
            logger.error(f"HuggingFace generation failed: {e}")
            raise RuntimeError(f"LLM generation failed: {e}") from e

    @staticmethod
    def _condense_for_hf(prompt: str) -> str:
        """Trim prompt to fit flan-t5's small context window."""
        max_chars = 1800
        question_marker = "## Question:"
        if question_marker in prompt:
            q_start = prompt.find(question_marker)
            condensed = (
                f"Answer this question about the code:\n\n"
                f"{prompt[:min(800, q_start)]}\n\n"
                f"{prompt[q_start:]}"
            ).replace("## Your Answer:", "").strip()
        else:
            condensed = prompt
        return condensed[:max_chars] if len(condensed) > max_chars else condensed

    # ── Response Building ──────────────────────────────────────────────────────

    @staticmethod
    def _build_sources(
        results: list[SearchResult],
        include_sources: bool,
    ) -> list[SourceReference]:
        if not include_sources:
            return []
        sources = []
        for result in results:
            snippet = result.content[:200].strip()
            if len(result.content) > 200:
                snippet += "..."
            sources.append(
                SourceReference(
                    file_path=result.file_path,
                    language=result.language,
                    start_line=result.start_line,
                    similarity_score=result.similarity_score,
                    relevance=result.relevance,
                    snippet=snippet,
                )
            )
        return sources