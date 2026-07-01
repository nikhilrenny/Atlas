"""Classifies a fetched web page into one of the toolbuilder PATTERNS using the model router."""
from app.models.router import router as model_router
from .manifest import PATTERNS

_PROMPT = """Classify this web page into exactly one category for the purpose of building \
an automation tool from it. Categories: {patterns}.

- search_form: page lets the user search/query something and view results
- data_extractor: page shows structured data (table, list, feed) worth scraping
- calculator: page computes a result from user-provided inputs
- api_wrapper: page output is clearly backed by a simple, callable API
- form_submitter: page's main purpose is submitting a form with side effects
- generic: none of the above fit well

Respond with ONLY the single category word, nothing else.

URL: {url}
Page title: {title}
Page text (truncated):
{text}
"""


async def classify(url: str, title: str, text: str) -> str:
    prompt = _PROMPT.format(patterns=", ".join(PATTERNS), url=url, title=title, text=text[:3000])
    try:
        result = await model_router.complete(prompt, complexity="low")
    except Exception:
        return "generic"
    label = result.strip().lower().split()[0].strip(".,:;\"'") if result.strip() else ""
    return label if label in PATTERNS else "generic"
