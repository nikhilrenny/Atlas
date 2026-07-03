"""Phase 10 orchestrator: goal -> decompose -> execute -> queryable run/step records.

Public API used by routes.py:
  start_run(goal)             -- kicks off a new agent run (fire-and-forget), returns run_id
  get_run(run_id)             -- run + its steps
  list_runs()                 -- recent runs
  create_schedule(...)        -- register a recurring goal
  list_schedules()            -- all schedules
  delete_schedule(id)         -- remove one
"""
import asyncio
import logging
from datetime import datetime, timezone

from . import store
from .planner import decompose
from .executor import execute_run
from .scheduler import start as start_scheduler, stop as stop_scheduler, _next_run_after

log = logging.getLogger("atlas.agents")

store.init_db()


async def _run(goal: str, run_id: str, force_provider: str | None, force_model: str | None):
    try:
        steps = await decompose(goal, force_provider=force_provider, force_model=force_model)
    except Exception as e:
        store.update_run_status(run_id, "failed", error=f"planning failed: {e}")
        return
    await execute_run(run_id, steps)


def start_run(goal: str, force_provider: str | None = None, force_model: str | None = None) -> str:
    run_id = store.create_run(goal)
    asyncio.create_task(_run(goal, run_id, force_provider, force_model))
    return run_id


def get_run(run_id: str) -> dict | None:
    return store.get_run(run_id)


def list_runs(limit: int = 50) -> list[dict]:
    return store.list_runs(limit=limit)


def create_schedule(goal: str, recurrence: dict) -> dict:
    now = datetime.now(timezone.utc)
    next_run = _next_run_after(recurrence, now)
    job_id = store.create_schedule(goal, recurrence, next_run.isoformat())
    return {"id": job_id, "goal": goal, "recurrence": recurrence, "next_run_at": next_run.isoformat()}


def list_schedules() -> list[dict]:
    return store.list_schedules()


def delete_schedule(job_id: str) -> bool:
    return store.delete_schedule(job_id)


def set_schedule_enabled(job_id: str, enabled: bool) -> bool:
    return store.set_schedule_enabled(job_id, enabled)
