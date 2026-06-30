"""Loads .env before any media client reads os.environ — mirrors app/models/__init__.py."""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
