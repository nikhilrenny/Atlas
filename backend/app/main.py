"""Atlas backend entrypoint.

Run with:
    cd D:\\Projects\\atlas\\backend
    venv\\Scripts\\activate
    uvicorn app.main:app --reload --port 8765
"""
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # safety net; app.models also loads .env on import, see app/models/__init__.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.browser.engine import engine as browser_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
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
