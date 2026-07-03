"""Runtime settings store for Atlas -- small JSON-file-backed key/value store for
the Settings panel. Deliberately not a full config system: just the handful of
behavioral defaults that were previously only reachable via env vars or hardcoded
Pydantic defaults, now user-editable at runtime without restarting the backend.
"""
import json
from pathlib import Path
from threading import Lock

SETTINGS_PATH = Path(__file__).resolve().parents[3] / "data" / "settings.json"

DEFAULTS = {
    "prefer_free": True,        # mid/high complexity tries Claude Pro OAuth before paid API
    "default_tor": False,       # browser fetch/screenshot Tor default when not specified per-call
    "default_stealth": False,   # fingerprint stealth default when not specified per-call
    "default_block_unsafe": False,  # safe-browsing 403-on-dangerous default when not specified per-call
}

_lock = Lock()


def _load() -> dict:
    if not SETTINGS_PATH.exists():
        return dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        return {**DEFAULTS, **saved}
    except Exception:
        return dict(DEFAULTS)


def get_all() -> dict:
    with _lock:
        return _load()


def update(patch: dict) -> dict:
    with _lock:
        current = _load()
        current.update({k: v for k, v in patch.items() if k in DEFAULTS})
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        return current
