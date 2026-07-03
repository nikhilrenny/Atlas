"""Atlas backend entrypoint.

Run with:
    cd D:\\Projects\\atlas\\backend
    venv\\Scripts\\activate
    uvicorn app.main:app --port 8765

Do NOT use --reload. uvicorn's --reload supervisor spawns a fresh worker subprocess
that re-derives its own asyncio event loop policy independently of this module's
Proactor override below (and independently of uvicorn's own Windows defaults in the
non-reload path). The result is a SelectorEventLoop in the reload worker, which
Playwright's subprocess-based Chromium launch cannot run under on Windows --
asyncio.create_subprocess_exec raises NotImplementedError. This is a known, recurring
Windows-specific Playwright/ASGI-reload incompatibility (seen across several unrelated
projects, not Atlas-specific) -- restart manually after backend edits instead.
"""
from contextlib import asynccontextmanager
import asyncio
import sys

# Playwright launches Chromium via asyncio.create_subprocess_exec, which on Windows
# only the Proactor event loop supports -- the Selector loop raises NotImplementedError
# at subprocess creation. Uvicorn (especially with --reload) can leave the Selector
# policy active, so force Proactor here before any event loop is created.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
# basicConfig is a no-op if uvicorn already added root handlers before this runs.
# Force our app logger to INFO so it propagates to uvicorn's root handler regardless.
logging.getLogger("app").setLevel(logging.INFO)

from app.dev import activity_log
activity_log.install()  # dev-only "Scripts Mode" panel taps the root logger

from dotenv import load_dotenv

load_dotenv()  # safety net; app.models also loads .env on import, see app/models/__init__.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.browser.engine import engine as browser_engine
from app import agents as atlas_agents
from app.agents import scheduler as agent_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_scheduler.start()
    yield
    agent_scheduler.stop()
    await browser_engine.stop()  # closes the shared Playwright/Chromium process cleanly


app = FastAPI(title="Atlas", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
