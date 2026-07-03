"""Executes an agent run's steps sequentially against Atlas's existing infrastructure --
no new execution surface, just orchestration on top of the tool registry, browser engine,
and tool-builder lookup pipeline that Phases 2/8 already built and hardened.

Stops on the first failed step by default (an agent blindly ploughing through a broken
plan is worse than stopping and reporting where it broke).
"""
import logging

from app.browser.engine import engine as browser_engine
from app.toolbuilder import run_tool, build_from_prompt
from . import store

log = logging.getLogger("atlas.agents")


async def _run_step(step: dict) -> dict:
    """Returns a small result dict; raises on failure so the caller can record it."""
    action = step["action"]
    target = step["target"]
    params = step["params"]

    if action == "tool":
        result = await run_tool(target, params)
        return {"data": result.get("data")}

    if action == "browse":
        page = await browser_engine.fetch(target)
        return {"title": page.get("title"), "text": page.get("text", "")[:2000]}

    if action == "lookup":
        result = await build_from_prompt(target)
        if result["status"] == "answered":
            return {"data": result.get("data"), "output_type": result.get("output_type")}
        if result["status"] == "infeasible":
            raise RuntimeError(result.get("reason", "lookup reported infeasible"))
        # "clarify"/"ready" mid-run isn't actionable without a human in the loop --
        # treat as a failure for this step rather than hanging the run.
        raise RuntimeError(f"lookup needs input Atlas can't supply mid-run (status={result['status']})")

    raise ValueError(f"unknown step action: {action!r}")


async def execute_run(run_id: str, steps: list[dict]) -> None:
    """Runs every step in order, persisting status as it goes. Never raises -- errors are
    recorded on the run/step rows so the frontend can poll and show exactly where it failed."""
    step_ids = [store.add_step(run_id, i, s["action"], s["target"], s["params"]) for i, s in enumerate(steps)]
    store.update_run_status(run_id, "running")

    for step, step_id in zip(steps, step_ids):
        store.update_step(step_id, "running", started=True)
        log.info("[agents] run %s step %s: %s %s", run_id, step["action"], step["target"], step["params"])
        try:
            result = await _run_step(step)
            store.update_step(step_id, "done", result=result, finished=True)
        except Exception as e:
            log.warning("[agents] run %s step failed: %s", run_id, e)
            store.update_step(step_id, "failed", error=str(e), finished=True)
            store.update_run_status(run_id, "failed", error=f"step {step['action']!r} failed: {e}")
            return

    store.update_run_status(run_id, "done")
