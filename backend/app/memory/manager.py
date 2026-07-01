"""High-level memory manager for Atlas.

Public API used by the rest of the codebase:
  record_lookup(prompt, result, output_type)    -- store a one-off lookup result
  record_tool_execution(tool_id, name, inputs, result)  -- store a tool run
  record_page_visit(url, title, summary)        -- store a browser page visit
  search(query, limit)                          -- semantic + keyword search
  context_for(prompt)                           -- returns (memories, preferences) relevant to a prompt
  set_preference(key, value, source)            -- explicit preference from user
"""
import asyncio
import logging

from app.models.router import router as model_router
from . import store
from .preference_extractor import maybe_infer

log = logging.getLogger(__name__)


async def _embed(text: str) -> list[float] | None:
    """Returns embedding or None if Ollama is unavailable."""
    try:
        return await model_router.embed(text)
    except Exception:
        return None


async def _store_with_embedding(type_: str, content: str, data: dict, tags: list[str]) -> str:
    mid = store.add_memory(type_, content, data, tags)
    embedding = await _embed(content)
    if embedding:
        store.add_embedding(mid, content, embedding)
    asyncio.create_task(maybe_infer(type_))
    return mid


# --- Record ---

async def record_lookup(prompt: str, result_summary: str, output_type: str) -> str:
    content = f"Lookup: {prompt} → {result_summary[:200]}"
    tags = ["lookup"] + _topic_tags(prompt)
    return await _store_with_embedding("lookup", content, {
        "prompt": prompt, "result_summary": result_summary, "output_type": output_type,
    }, tags)


async def record_tool_execution(tool_id: str, tool_name: str, inputs: dict, result_summary: str) -> str:
    content = f"Ran tool '{tool_name}' with {inputs} → {result_summary[:200]}"
    tags = ["tool", tool_id]
    return await _store_with_embedding("tool_execution", content, {
        "tool_id": tool_id, "tool_name": tool_name, "inputs": inputs, "result_summary": result_summary,
    }, tags)


async def record_page_visit(url: str, title: str, summary: str = "") -> str:
    content = f"Visited: {title} ({url})" + (f" — {summary[:150]}" if summary else "")
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    tags = ["page_visit", domain]
    return await _store_with_embedding("page_visit", content, {
        "url": url, "title": title, "summary": summary,
    }, tags)


# --- Search ---

async def search(query: str, limit: int = 5) -> list[dict]:
    """Semantic search with keyword fallback."""
    embedding = await _embed(query)
    if embedding:
        results = store.semantic_search(embedding, limit=limit)
        if results:
            return results
    return store.keyword_search(query, limit=limit)


async def context_for(prompt: str) -> dict:
    """Returns relevant memories and preferences for injecting into a prompt.

    Shape: {"memories": [...], "preferences": {...}, "context_str": "..."}
    context_str is a pre-formatted string ready to append to a prompt.
    """
    memories = await search(prompt, limit=4)
    preferences = store.get_preferences()

    parts = []
    if preferences:
        pref_lines = "\n".join(f"  - {k}: {v['value']}" for k, v in preferences.items())
        parts.append(f"Known user preferences:\n{pref_lines}")
    if memories:
        mem_lines = "\n".join(f"  - {m['content']}" for m in memories)
        parts.append(f"Relevant past activity:\n{mem_lines}")

    context_str = "\n\n".join(parts)
    return {"memories": memories, "preferences": preferences, "context_str": context_str}


# --- Explicit preference ---

def set_preference(key: str, value: str, source: str = "explicit"):
    store.set_preference(key, value, confidence=1.0, source=source)
    log.info("[memory] preference set explicitly: %s = %r", key, value)


# --- Helpers ---

_TOPIC_KEYWORDS = {
    "weather": ["weather", "temperature", "forecast", "rain", "sun", "humidity"],
    "music": ["artist", "album", "song", "band", "music", "track", "discography"],
    "finance": ["stock", "price", "currency", "exchange", "crypto", "bitcoin"],
    "news": ["news", "headline", "article", "report"],
    "sports": ["score", "match", "game", "team", "league", "player"],
}

def _topic_tags(text: str) -> list[str]:
    text_lower = text.lower()
    return [topic for topic, kws in _TOPIC_KEYWORDS.items() if any(kw in text_lower for kw in kws)]
