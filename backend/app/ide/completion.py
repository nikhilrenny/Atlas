"""AI code completion for the IDE panel — routes through the existing model router
rather than calling Claude Code OAuth directly, so it gets the same free-OAuth-first,
paid-API-fallback behavior as the rest of Atlas (and shows up in the Phase 1 usage log).
"""
from app.models.router import router as model_router

PROMPT_TEMPLATE = """You are completing/editing code inside an IDE panel. Language: {language}.

Instruction: {instruction}

Current code:
```{language}
{code}
```

Respond with ONLY the resulting code (the full file, not a diff), no explanation, \
no markdown fences."""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


async def complete(code: str, instruction: str, language: str = "python") -> str:
    prompt = PROMPT_TEMPLATE.format(language=language, instruction=instruction, code=code)
    # Code edits are usually long enough to land in "high" complexity by length already,
    # but pin it explicitly so a short snippet + short instruction doesn't get routed to
    # the low-tier model and produce a worse edit.
    raw = await model_router.complete(prompt, complexity="high", prefer_free=True)
    return _strip_fences(raw)
