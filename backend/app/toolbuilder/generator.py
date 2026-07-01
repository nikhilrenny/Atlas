"""Generates a tool manifest + Python implementation -- either grounded in a fetched page
(generate(), the URL path) or in an already-assessed plan (generate_from_plan(), the prompt
path -- see intake.py). Both share the same code-writing rules and JSON parsing/retry logic;
only the context section of the prompt differs.

`code` must define `async def run(inputs: dict) -> dict` and may only import the standard
library plus httpx and beautifulsoup4 -- the only third-party libs actually installed in the
executor's interpreter (see requirements.txt). Naming a library here that isn't installed
produces a working manifest with code that fails at runtime, so this list must stay in sync
with requirements.txt whenever the venv changes.

Network egress from generated code is enforced (not just requested) at the socket level by
the executor's domain allowlist -- see executor.py. The LLM is still told about it so it
doesn't waste a generation cycle writing code that will be blocked.
"""
import json
import re

from app.models.router import router as model_router
from .manifest import ToolManifest, INPUT_TYPES, OUTPUT_TYPES

_CODE_RULES = """Output ONLY a single JSON object, no markdown fences, no commentary, with this \
exact shape:

{{
  "manifest": {{
    "name": "short tool name",
    "description": "one sentence describing what it does",
    "inputs": [{{"name": "field_name", "label": "Human label", "type": "text|number|boolean|select|file",
                  "required": true, "options": null, "default": null}}],
    "output_type": "text|json|table|image"
  }},
  "code": "async def run(inputs: dict) -> dict:\\n    ...\\n    return {{\\\"data\\\": ...}}"
}}

Rules for "code":
- Must define exactly one top-level function: `async def run(inputs: dict) -> dict`
- Do NOT define any classes, do NOT wrap run() in a class. One bare function at module level only.
- `inputs` keys match manifest.inputs[].name exactly
- A "file" type input arrives as a plain base64 string (no "data:...;base64," prefix) in
  inputs[name] -- decode with `base64.b64decode(inputs[name])` before using PIL.
- Return value must be a dict with a "data" key (str, or JSON-serializable for output_type
  json/table). For output_type "table", data must be {{"columns": [...], "rows": [[...]]}}.
  For output_type "image", data must be a full data URI string, e.g.
  `f"data:image/png;base64,{{base64.b64encode(buf.getvalue()).decode()}}"` -- include the
  prefix on output (unlike input, which has no prefix).
- Choose output_type by the SHAPE of the result, not by reflex: "table" only for genuinely
  tabular/repeating records (a list of similar items with the same fields). "json" only when
  the result is config-like data someone would want to inspect as structure (API responses
  for debugging, nested settings) -- never for anything meant to be read as prose. If the
  result is naturally a narrative -- a bio, a summary, a description with an embedded list --
  use output_type "text" and build data as a single pre-formatted string yourself (paragraph
  breaks via "\n\n", list items as "- item" lines) rather than handing back a raw nested
  dict for the frontend to dump. A person should be able to read "text" output top to bottom
  without mentally parsing braces and quotes.
- Only stdlib, httpx, beautifulsoup4 (`from bs4 import BeautifulSoup`), and Pillow
  (`from PIL import Image`) may be imported. No other third-party libraries are installed --
  using one will fail at runtime. httpx is async; use `httpx.AsyncClient`. Image work happens
  fully in memory via `io.BytesIO` -- no file system writes, no subprocess, no eval/exec, no
  __import__.
- Network requests are ONLY permitted to these domains: {allowed_domains}. Calls to any
  other host will be blocked at runtime and raise PermissionError -- do not attempt to
  work around this.
- Pattern classification for this tool: {pattern}

{context}
"""

_URL_CONTEXT = """Page URL: {url}
Page title: {title}
Page text (truncated):
{text}"""

_PLAN_CONTEXT = """This tool was already planned in a feasibility step -- match the plan exactly,
don't redesign it, including any "default" values already set on inputs (carry them through
to the manifest unchanged -- they're pre-filled from what the user already told you):
{plan}

User's original request: {prompt}"""

_PREAMBLE = "You are generating an automation tool from a web page for Atlas, a personal AI browser. "
_PREAMBLE_PLAN = "You are generating an automation tool for Atlas, a personal AI browser, from an already-approved plan. "


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in model output")
    return json.loads(raw[start : end + 1])


async def _run_generation(full_prompt: str, source_url: str, pattern: str, allowed_domains: list[str]) -> tuple[ToolManifest, str]:
    last_err = None
    for attempt in range(2):  # one retry on malformed output
        try:
            raw = await model_router.complete(full_prompt, complexity="high")
            parsed = _extract_json(raw)
            manifest_data = parsed["manifest"]
            code = parsed["code"]
            if "async def run(" not in code:
                raise ValueError("generated code does not define async def run(inputs: dict)")
            try:
                compile(code, "<generated>", "exec")
            except SyntaxError as e:
                raise ValueError(f"generated code has a syntax error: {e}") from e
            manifest = ToolManifest(
                name=manifest_data.get("name", "Untitled tool"),
                description=manifest_data.get("description", ""),
                source_url=source_url,
                pattern=pattern,
                inputs=manifest_data.get("inputs", []),
                output_type=manifest_data.get("output_type", "text"),
                allowed_domains=allowed_domains,
            )
            return manifest, code
        except Exception as e:
            last_err = e
            full_prompt += f"\n\nYour previous output was invalid ({e}). Output ONLY the JSON object this time."
    raise RuntimeError(f"tool generation failed after retry: {last_err}")


async def generate(url: str, title: str, text: str, pattern: str, allowed_domains: list[str]) -> tuple[ToolManifest, str]:
    context = _URL_CONTEXT.format(url=url, title=title, text=text[:6000])
    rules = _CODE_RULES.format(
        allowed_domains=", ".join(allowed_domains) or "(none -- generated tool will have no network access)",
        pattern=pattern, context=context,
    )
    return await _run_generation(_PREAMBLE + rules, url, pattern, allowed_domains)


async def generate_from_plan(prompt: str, plan: dict) -> tuple[ToolManifest, str]:
    allowed_domains = plan.get("target_domains", [])
    pattern = plan.get("pattern", "generic")
    context = _PLAN_CONTEXT.format(plan=json.dumps(plan), prompt=prompt)
    rules = _CODE_RULES.format(
        allowed_domains=", ".join(allowed_domains) or "(none -- generated tool will have no network access)",
        pattern=pattern, context=context,
    )
    return await _run_generation(_PREAMBLE_PLAN + rules, "", pattern, allowed_domains)
