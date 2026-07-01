"""Infers user preferences from memory patterns using the model router.

Called after every INFER_AFTER_N new memories of the same type accumulate.
Looks at recent memories of that type and extracts stable preferences
(location, temperature unit, language, topic interests) at low complexity
so it routes to llama3.1:8b or NIM -- cheap, fast, not worth burning Pro credits.

Preferences are stored with a confidence score (0-1). Re-inference updates
the score upward (more evidence = higher confidence) or corrects it if the
pattern changed.
"""
import json
import logging

from app.models.router import router as model_router
from . import store

log = logging.getLogger(__name__)

INFER_AFTER_N = 5  # run inference after every N new memories of the same type

_PROMPT = """Analyze these recent Atlas memory records and extract any stable user preferences.

Records:
{records}

Existing preferences already known:
{existing}

Return ONLY a JSON object mapping preference keys to values. Only include preferences
you're confident about from the evidence. If nothing new can be inferred, return {{}}.

Keys to look for (use exactly these key names):
- "location"            -- user's primary location/city (from repeated local lookups)
- "temperature_unit"    -- "celsius" or "fahrenheit" (from weather lookups)
- "language"            -- preferred language if not English
- "topics"              -- comma-separated list of frequent interest areas

Example: {{"location": "Delhi", "temperature_unit": "celsius", "topics": "music,weather"}}

Return ONLY the JSON object, no explanation."""


async def maybe_infer(type_: str):
    """Run preference inference if enough new memories of this type have accumulated."""
    count = store.count_memories(type_)
    if count % INFER_AFTER_N != 0:
        return
    log.info("[memory] running preference inference after %d %s memories", count, type_)
    await infer_preferences(type_)


async def infer_preferences(type_: str | None = None):
    """Explicitly run preference inference across recent memories."""
    memories = store.list_memories(type_=type_, limit=20)
    if not memories:
        return
    existing = store.get_preferences()
    records_text = "\n".join(f"- [{m['type']}] {m['content']}" for m in memories)
    existing_text = json.dumps({k: v["value"] for k, v in existing.items()}) if existing else "{}"
    prompt = _PROMPT.format(records=records_text, existing=existing_text)
    try:
        raw = await model_router.complete(prompt, complexity="low")
        raw = raw.strip()
        import re
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            return
        inferred = json.loads(raw[start:end + 1])
        for key, value in inferred.items():
            if value:
                # Increase confidence slightly if it matches existing, set fresh if new
                existing_val = existing.get(key, {}).get("value")
                confidence = min(1.0, existing.get(key, {}).get("confidence", 0.5) + 0.1) if existing_val == value else 0.7
                store.set_preference(key, str(value), confidence=confidence, source="inferred")
                log.info("[memory] preference inferred: %s = %r (confidence=%.2f)", key, value, confidence)
    except Exception as e:
        log.warning("[memory] preference inference failed: %s", e)
