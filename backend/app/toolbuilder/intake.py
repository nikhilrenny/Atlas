"""Feasibility check + clarification flow for prompt-based ("build me X") tool requests,
as opposed to URL-based ones (see classifier.py + generator.generate). There's no page to
ground against here -- the LLM has to reason about whether the request is buildable at all
within the sandbox's real constraints (stdlib + httpx + bs4 only, no file upload/download,
network only to domains it names itself -- see executor.py and generator.py) before any
code gets written, and ask the user for missing specifics rather than silently guessing.
"""
import json
import re

from app.models.router import router as model_router
from .manifest import PATTERNS, OUTPUT_TYPES

MAX_CLARIFY_ROUNDS = 2

_PROMPT = """RESPOND WITH ONLY A JSON OBJECT. No explanation, no preamble, no markdown fences.

A user of Atlas, a personal AI browser, wants a tool built from a plain-language \
request (no source page to ground against). Decide whether it's buildable, and if so, plan it.

HARD CONSTRAINTS (mark infeasible if the request cannot be satisfied within these):
- File input/output is supported, but ONLY for images, via base64 -- a "file" type input
  field delivers the file as a base64 string (no data: prefix) in inputs[name], and an
  "image" output_type means the tool returns a full data URI string
  ("data:image/png;base64,...") as data. Only Pillow (PIL) is available for image work --
  no other file formats (PDF, video, audio, documents) and no file processing beyond what
  Pillow can do (format conversion, resize, crop, basic filters). A request needing those
  is infeasible.
- Only stdlib, httpx, beautifulsoup4, and Pillow (PIL) are installed -- no other libraries.
- Any external data source must be a specific domain the tool will call directly. Prefer
  free, no-API-key sources (e.g. Open-Meteo at api.open-meteo.com + geocoding-api.open-meteo.com
  for weather/location -- no key required). If a request genuinely requires a paid or
  key-gated API, that's fine: add an "api_key" text input to the plan so the user supplies
  their own key at run-time -- Atlas never stores it. Don't invent a fake free endpoint for
  something that actually requires auth.
- No local hardware/OS access (webcam, filesystem, clipboard, notifications).

Respond with ONLY a single JSON object, no markdown fences, no commentary, in exactly one
of these three shapes:

Missing information you can't reasonably default (e.g. "weather widget" with no location
given and no sensible global default):
{{"status": "clarify", "questions": ["short question 1", "short question 2"]}}

Request can't be satisfied within the constraints above:
{{"status": "infeasible", "reason": "one sentence, plain language, no jargon"}}

Buildable as-is or after reasonable defaults:
{{"status": "ready", "intent": "lookup|tool", "plan": {{
  "name": "short tool name",
  "description": "one sentence",
  "pattern": "{patterns}",
  "target_domains": ["domain1.com"],
  "inputs": [{{"name": "field_name", "label": "Human label", "type": "text|number|boolean|select|file",
                "required": true, "options": null, "default": null}}],
  "output_type": "{output_types}"
}}}}

Deciding "intent": this determines whether the build gets saved as a reusable tool in the
user's sidebar, or just runs once and shows the answer. Use "tool" only when the request
explicitly asks for something to build/save/reuse -- "build me a...", "make a widget for...",
"create a converter", "I want a tool that...". Use "lookup" for anything phrased as a direct
question or one-time request for information -- "what's the weather in Paris", "tell me
about The Weeknd", "get me everything on X", "how many calories in...". When intent is
"lookup", every input should end up with a "default" set (per the rule below) since there's
no user-facing form -- the tool runs immediately with those defaults and returns the result.
If genuinely unsure, prefer "lookup" -- it's the lower-commitment choice.

If the user's request already names a specific value for an input (e.g. "music artist the
weekend" naming The Weeknd, or "weather in Paris" naming Paris), set that input's "default"
to it so the field arrives pre-filled and ready to run -- don't make the user re-type
something they already told you. Leave "default" null only for genuinely open fields.

Choosing output_type: "table" only for genuinely repeating records (a list of similar
items, same fields each). "json" only for config-like structure someone would inspect, not
for anything meant to be read as prose. If the result is naturally narrative -- a bio, a
summary, a description -- use "text"; the tool's code will format it as a single readable
string, not return raw nested data for the frontend to dump.

{force_decide}

User's request: {prompt}
"""


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in model output")
    body = raw[start : end + 1]
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        repaired = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", body)
        return json.loads(repaired)


async def assess(prompt: str, force_decide: bool = False) -> dict:
    """Returns one of:
      {"status": "clarify", "questions": [...]}
      {"status": "infeasible", "reason": "..."}
      {"status": "ready", "intent": "lookup"|"tool", "plan": {...}}
    """
    force_note = (
        "You've already asked for clarification once and the user replied -- you MUST "
        "respond with \"ready\" or \"infeasible\" now, not \"clarify\" again. If anything "
        "is still ambiguous, pick the most sensible default rather than asking again."
        if force_decide else ""
    )
    full_prompt = _PROMPT.format(
        patterns="|".join(PATTERNS), output_types="|".join(OUTPUT_TYPES),
        force_decide=force_note, prompt=prompt,
    )

    last_err = None
    for attempt in range(2):
        try:
            raw = await model_router.complete(full_prompt, complexity="low")
            parsed = _extract_json(raw)
            status = parsed.get("status")
            if status not in ("clarify", "infeasible", "ready"):
                raise ValueError(f"unexpected status: {status!r}")
            if status == "clarify" and force_decide:
                # model ignored the instruction -- don't loop forever, treat as infeasible
                return {"status": "infeasible", "reason": "Couldn't pin down enough detail to build this automatically."}
            return parsed
        except Exception as e:
            last_err = e
            full_prompt += f"\n\nYour previous output was invalid ({e}). Output ONLY the JSON object this time."
    raise RuntimeError(f"feasibility assessment failed after retry: {last_err}")
