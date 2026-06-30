"""Loads .env before any client in this package reads os.environ, regardless of which
module gets imported first (router.py, individual clients, or test scripts)."""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
