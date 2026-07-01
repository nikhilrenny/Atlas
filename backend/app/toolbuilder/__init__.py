"""Phase 8 orchestrator: two entry paths into the same back half of the pipeline.

  URL path:    fetch page -> classify -> generate -> register -> run
  Prompt path: assess feasibility (maybe clarify) -> generate_from_plan -> branch on intent:
                 "tool"   -> register, return for repeated use (sidebar entry, input form)
                 "lookup" -> execute immediately with the plan's defaults, return the
                             answer directly, nothing saved to the registry or disk

Both paths converge on the same registry/executor for "tool" intent -- a tool built from a
prompt is identical in every way to one built from a URL once it exists. "lookup" intent
skips the registry entirely; see intake.py for how that's decided.
"""
from urllib.parse import urlparse
import asyncio
import logging

log = logging.getLogger(__name__)

from app.browser.engine import engine as browser_engine
from app import memory as mem

from .classifier import classify
from .generator import generate, generate_from_plan
from .executor import execute
from .intake import assess, MAX_CLARIFY_ROUNDS
from .manifest import ToolManifest
from .registry import registry


async def build_from_url(url: str) -> ToolManifest:
    log.info("[toolbuilder] fetch: %s", url)
    page = await browser_engine.fetch(url)
    log.info("[toolbuilder] fetched — title: %r", page.get("title"))
    log.info("[toolbuilder] classifying page...")
    pattern = await classify(url, page["title"], page["text"])
    log.info("[toolbuilder] pattern: %s", pattern)
    host = urlparse(url).netloc
    log.info("[toolbuilder] generating code (high tier)...")
    manifest, code = await generate(url, page["title"], page["text"], pattern, [host] if host else [])
    log.info("[toolbuilder] generated: %r  inputs: %s  output_type: %s", manifest.name, [i.name for i in manifest.inputs], manifest.output_type)
    registry.register(manifest, code)
    log.info("[toolbuilder] registered as %s", manifest.id)
    return manifest


async def build_from_prompt(prompt: str, answers: str | None = None, round: int = 0) -> dict:
    """Returns one of:
      {"status": "clarify", "questions": [...]}
      {"status": "infeasible", "reason": "..."}
      {"status": "ready", "manifest": ToolManifest}                       -- intent "tool"
      {"status": "answered", "data": ..., "output_type": "..."}            -- intent "lookup"
    """
    combined = prompt if not answers else f"{prompt}\n\nUser's clarifying answers: {answers}"
    force_decide = round >= MAX_CLARIFY_ROUNDS
    log.info("[toolbuilder] assessing prompt (low tier): %r  round=%d", prompt, round)

    # Fetch relevant memory context and inject into assessment
    mem_context = await mem.context_for(prompt)
    context_prompt = combined
    if mem_context["context_str"]:
        context_prompt = combined + f"\n\n[Memory context for this request:]\n{mem_context['context_str']}"
        log.info("[toolbuilder] injecting memory context (%d memories, %d preferences)",
                 len(mem_context["memories"]), len(mem_context["preferences"]))

    assessment = await assess(context_prompt, force_decide=force_decide)
    log.info("[toolbuilder] assessment: status=%s  intent=%s", assessment.get("status"), assessment.get("intent"))

    if assessment["status"] == "infeasible":
        log.info("[toolbuilder] infeasible: %s", assessment["reason"])
        return {"status": "infeasible", "reason": assessment["reason"]}
    if assessment["status"] == "clarify":
        log.info("[toolbuilder] needs clarification: %s", assessment["questions"])
        return {"status": "clarify", "questions": assessment["questions"]}

    plan = assessment["plan"]
    intent = assessment.get("intent", "tool")
    log.info("[toolbuilder] generating code (high tier)  intent=%s  pattern=%s  domains=%s", intent, plan.get("pattern"), plan.get("target_domains"))
    manifest, code = await generate_from_plan(combined, plan)
    log.info("[toolbuilder] generated: %r  inputs: %s  output_type: %s", manifest.name, [i.name for i in manifest.inputs], manifest.output_type)

    if intent == "lookup":
        inputs = {f.name: f.default for f in manifest.inputs if f.default is not None}
        log.info("[toolbuilder] lookup — executing immediately with defaults: %s", inputs)
        result = await execute(code, inputs, manifest.allowed_domains)
        log.info("[toolbuilder] lookup complete")
        # Record the lookup result in memory
        result_summary = str(result.get("data", ""))[:300]
        await mem.record_lookup(prompt, result_summary, manifest.output_type)
        return {"status": "answered", "data": result.get("data"), "output_type": manifest.output_type,
                "memory_context": mem_context}

    registry.register(manifest, code)
    log.info("[toolbuilder] registered as %s", manifest.id)
    return {"status": "ready", "manifest": manifest, "memory_context": mem_context}


async def run_tool(tool_id: str, inputs: dict) -> dict:
    manifest = registry.get(tool_id)
    if manifest is None:
        raise KeyError(f"no such tool: {tool_id}")
    code = registry.get_code(tool_id)
    result = await execute(code, inputs, manifest.allowed_domains)
    # Record execution in memory (fire-and-forget)
    result_summary = str(result.get("data", ""))[:300]
    asyncio.create_task(mem.record_tool_execution(tool_id, manifest.name, inputs, result_summary))
    return result
