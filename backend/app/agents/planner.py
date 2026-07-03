"""Goal decomposition for Phase 10 agent runs -- one LLM call breaks a natural-language
goal into an ordered list of steps against Atlas's existing capabilities.

Uses the same lesson Phase 8 landed on the hard way: no JSON-in-JSON. Steps come back as
plain-text ===STEP=== blocks with simple key: value lines, parsed without touching a JSON
parser for the params. Only `params` itself is JSON (one line, easy to isolate).
"""
import json
import re

from app.models.router import router as model_router
from app.toolbuilder.registry import registry as tool_registry

PLANNING_MAX_TOKENS = 1536

_RULES = """You are decomposing a goal into an ordered sequence of steps for Atlas, a personal \
AI agent. Output EXACTLY this structure and nothing else -- no commentary before or after:

===STEP===
action: tool | browse | lookup
target: <tool id, or a URL, or a one-off question -- depending on action>
params: {{"key": "value"}}
===STEP===
(repeat for each step, in order)
===END===

Action types:
- "tool": run one of the user's existing saved tools. target = the tool's id (exactly as
  listed below). params = the tool's inputs as a flat JSON object matching its input names.
- "browse": fetch a URL and use its text as context for later steps. target = the URL.
  params = {{}}.
- "lookup": answer a one-off question using Atlas's tool-builder lookup pipeline (it can
  browse the web itself if needed). target = the question, phrased as you'd type it into
  Atlas's search bar. params = {{}}.

Rules:
- Prefer "tool" whenever an existing tool already does what's needed -- don't re-invent it
  as a "lookup".
- Keep the plan to the minimum steps that actually accomplish the goal. Don't pad it.
- If the goal is impossible with what's available (no tool, and not something a web lookup
  could answer), output a single step: action: lookup, target: the original goal verbatim,
  params: {{}} -- let the lookup pipeline itself report infeasibility rather than guessing here.
- "params" must be valid JSON on one line -- no multi-line objects, no trailing commentary.

Available saved tools:
{tools_list}

Goal: {goal}
"""


def _extract_steps(raw: str) -> list[dict]:
    raw = raw.strip()
    raw = re.sub(r"^```\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    if "===STEP===" not in raw:
        raise ValueError("missing ===STEP=== markers in model output")
    steps = []
    for block in raw.split("===STEP==="):
        block = block.replace("===END===", "").strip()
        if not block:
            continue
        action_m = re.search(r"^action:\s*(\w+)", block, re.MULTILINE)
        target_m = re.search(r"^target:\s*(.+)$", block, re.MULTILINE)
        params_m = re.search(r"^params:\s*(\{.*\})\s*$", block, re.MULTILINE | re.DOTALL)
        if not action_m or not target_m:
            continue
        action = action_m.group(1).strip().lower()
        target = target_m.group(1).strip()
        params = {}
        if params_m:
            try:
                params = json.loads(params_m.group(1))
            except Exception:
                params = {}
        if action not in ("tool", "browse", "lookup"):
            continue
        steps.append({"action": action, "target": target, "params": params})
    if not steps:
        raise ValueError("no valid steps parsed from model output")
    return steps


async def decompose(goal: str, force_provider: str | None = None, force_model: str | None = None) -> list[dict]:
    """Returns [{"action": ..., "target": ..., "params": {...}}, ...]. Raises RuntimeError
    after one retry if the model won't produce a parseable plan."""
    tools = tool_registry.list()
    tools_list = "\n".join(f"- id={t.id}  name={t.name!r}  inputs={[i.name for i in t.inputs]}" for t in tools) or "(none saved yet)"
    prompt = _RULES.format(tools_list=tools_list, goal=goal)

    last_err = None
    for attempt in range(2):
        try:
            raw = await model_router.complete(prompt, complexity="high", force_provider=force_provider, force_model=force_model, max_tokens=PLANNING_MAX_TOKENS)
            return _extract_steps(raw)
        except Exception as e:
            last_err = e
            prompt += f"\n\nYour previous output was invalid ({e}). Follow the ===STEP=== format exactly."
    raise RuntimeError(f"goal decomposition failed after retry: {last_err}")
