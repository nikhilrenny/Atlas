"""Model router — unifies Ollama, NVIDIA NIM, Claude API, and Claude Pro OAuth behind one call.

Routing:
  embeddings        -> Ollama (nomic-embed-text)
  low complexity     -> NVIDIA NIM (falls back to Ollama if no key / request fails)
  mid complexity     -> Claude API, Haiku
  high complexity    -> Claude Pro OAuth (free), falls back to Claude API Sonnet if OAuth fails
"""
import logging
import os
import time
from enum import Enum

from .ollama_client import OllamaClient
from .nim_client import NIMClient
from .claude_api_client import ClaudeAPIClient, DEFAULT_HIGH_MODEL
from .claude_oauth_client import ClaudeOAuthClient
from .usage_log import usage_log

logger = logging.getLogger("atlas.router")


class Complexity(str, Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"


class ModelRouter:
    def __init__(self):
        self.ollama = OllamaClient()
        self.nim = NIMClient()
        self.claude_api = ClaudeAPIClient()
        self.claude_oauth = ClaudeOAuthClient()

    def classify(self, prompt: str, complexity: str | None = None) -> Complexity:
        if complexity:
            return Complexity(complexity)
        length = len(prompt)
        if length < 200:
            return Complexity.LOW
        if length < 1000:
            return Complexity.MID
        return Complexity.HIGH

    async def embed(self, text):
        return await self.ollama.embed(text)

    async def _dispatch(self, prompt: str, level: Complexity, prefer_free: bool, **kwargs) -> tuple[str, str]:
        # Hard override: route everything to Ollama, skip NIM/Claude entirely.
        # Low complexity (assess/classify) -> llama3.1:8b (fast)
        # High/mid complexity (code generation) -> qwen3.5:9b (better at Python)
        if os.environ.get("ATLAS_FORCE_OLLAMA", "").lower() in ("1", "true", "yes"):
            model = "llama3.1:8b" if level == Complexity.LOW else "qwen3.5:9b"
            start = time.perf_counter()
            try:
                text = await self.ollama.complete(prompt, model=model, **kwargs)
                return text, "ollama"
            finally:
                usage_log.record(
                    provider="ollama", complexity=level.value,
                    latency_ms=(time.perf_counter() - start) * 1000,
                    prompt_chars=len(prompt), response_chars=0,
                )

        if os.environ.get("ATLAS_FORCE_CLAUDE_PRO", "").lower() in ("1", "true", "yes"):
            start = time.perf_counter()
            try:
                text = await self.claude_oauth.complete(prompt, **kwargs)
                return text, "claude_oauth"
            finally:
                usage_log.record(
                    provider="claude_oauth", complexity=level.value,
                    latency_ms=(time.perf_counter() - start) * 1000,
                    prompt_chars=len(prompt), response_chars=0,
                )
        """Runs the routing logic for an already-classified prompt. Returns (text, provider_name).

        Times the whole call (including any fallback hop) and persists one record to
        usage_log regardless of outcome — failed calls are logged with error set and no cost.
        """
        start = time.perf_counter()
        text = None
        provider = None
        error = None
        try:
            if level == Complexity.LOW:
                if self.nim.is_available():
                    try:
                        text, provider = await self.nim.complete(prompt, **kwargs), "nim"
                    except Exception as e:
                        logger.warning(f"NIM failed, falling back to Ollama: {e}")
                if text is None:
                    text, provider = await self.ollama.complete(prompt, **kwargs), "ollama"

            elif level == Complexity.MID:
                if prefer_free:
                    try:
                        text, provider = await self.claude_oauth.complete(prompt, **kwargs), "claude_oauth"
                    except Exception as e:
                        logger.warning(f"Claude OAuth failed, falling back to Claude API Haiku: {e}")
                if text is None:
                    text, provider = await self.claude_api.complete(prompt, **kwargs), "claude_api_haiku"

            else:  # HIGH
                if prefer_free:
                    try:
                        text, provider = await self.claude_oauth.complete(prompt, **kwargs), "claude_oauth"
                    except Exception as e:
                        logger.warning(f"Claude OAuth failed, falling back to Claude API: {e}")
                if text is None:
                    text, provider = (
                        await self.claude_api.complete(prompt, model=DEFAULT_HIGH_MODEL, **kwargs),
                        "claude_api_sonnet",
                    )
            return text, provider
        except Exception as e:
            error = str(e)
            raise
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            model = self.claude_api.last_model if provider in ("claude_api_haiku", "claude_api_sonnet") else None
            usage = self.claude_api.last_usage if model else None
            usage_log.record(
                provider=provider or "none",
                complexity=level.value,
                latency_ms=latency_ms,
                prompt_chars=len(prompt),
                response_chars=len(text) if text else 0,
                model=model,
                input_tokens=usage["input_tokens"] if usage else None,
                output_tokens=usage["output_tokens"] if usage else None,
                error=error,
            )

    async def complete(self, prompt: str, complexity: str | None = None, prefer_free: bool = True, **kwargs) -> str:
        level = self.classify(prompt, complexity)
        text, _ = await self._dispatch(prompt, level, prefer_free, **kwargs)
        return text

    async def complete_verbose(self, prompt: str, complexity: str | None = None, prefer_free: bool = True, **kwargs) -> dict:
        """Same routing as complete(), but also returns which provider served the request
        and the classified complexity tier — used by the API layer."""
        level = self.classify(prompt, complexity)
        text, provider = await self._dispatch(prompt, level, prefer_free, **kwargs)
        return {"text": text, "provider": provider, "complexity": level.value}


router = ModelRouter()
