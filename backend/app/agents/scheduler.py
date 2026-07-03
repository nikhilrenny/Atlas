"""In-process cron-like scheduler for Phase 10. No new dependency (no croniter/APScheduler) --
recurrence is deliberately simple: fixed-interval or once-daily-at-HH:MM, matching the lean-
deps pattern used everywhere else in this codebase. Runs as one asyncio background task
started from main.py's lifespan, polling every 30s.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from . import store
from .planner import decompose
from .executor import execute_run

log = logging.getLogger("atlas.agents.scheduler")

POLL_SECONDS = 30
_task: asyncio.Task | None = None


def _next_run_after(recurrence: dict, now: datetime) -> datetime:
    if recurrence.get("type") == "interval":
        minutes = max(1, int(recurrence.get("minutes", 60)))
        return now + timedelta(minutes=minutes)
    if recurrence.get("type") == "daily":
        hh, mm = (recurrence.get("at") or "09:00").split(":")
        candidate = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    # Unknown recurrence type -- default to daily so a bad row doesn't spin every 30s.
    return now + timedelta(days=1)


async def _run_goal(goal: str) -> str:
    run_id = store.create_run(goal)
    try:
        steps = await decompose(goal)
    except Exception as e:
        store.update_run_status(run_id, "failed", error=f"planning failed: {e}")
        return run_id
    await execute_run(run_id, steps)
    return run_id


async def _poll_loop():
    while True:
        try:
            now = datetime.now(timezone.utc)
            for job in store.due_schedules(now.isoformat()):
                log.info("[agents] scheduled job due: %s", job["goal"])
                next_run = _next_run_after(job["recurrence"], now)
                store.mark_schedule_ran(job["id"], next_run.isoformat())
                asyncio.create_task(_run_goal(job["goal"]))
        except Exception as e:
            log.warning("[agents] scheduler poll failed: %s", e)
        await asyncio.sleep(POLL_SECONDS)


def start():
    global _task
    if _task is None:
        _task = asyncio.create_task(_poll_loop())
        log.info("[agents] scheduler started (poll every %ds)", POLL_SECONDS)


def stop():
    global _task
    if _task is not None:
        _task.cancel()
        _task = None
