"""In-memory activity feed for Atlas's dev-only "Scripts Mode" panel.

Captures the app's existing logging output (the same [toolbuilder]/[router]/etc. lines
that already print to the terminal) into a bounded in-memory ring buffer, so the frontend
can poll for "what's happening behind the scenes right now" without needing a websocket
or any change to the extensive logging that already exists throughout the codebase.

Dev-only: this is not a general observability system, just a thin tap on the logger.
"""
import logging
import time
from collections import deque
from threading import Lock

MAX_ENTRIES = 500

_buffer: deque[dict] = deque(maxlen=MAX_ENTRIES)
_lock = Lock()
_next_id = 0


class ActivityLogHandler(logging.Handler):
    """Appends every log record from the app's loggers into the shared ring buffer."""

    def emit(self, record: logging.LogRecord) -> None:
        global _next_id
        try:
            message = self.format(record)
        except Exception:
            message = record.getMessage()
        with _lock:
            _next_id += 1
            _buffer.append({
                "id": _next_id,
                "ts": time.time(),
                "level": record.levelname,
                "logger": record.name,
                "message": message,
            })


def install(logger_name: str = "", level: int = logging.INFO) -> None:
    """Attaches the ring-buffer handler to the given logger (root, by default, so every
    logger in the process feeds it regardless of naming convention). Call once at startup."""
    handler = ActivityLogHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger(logger_name).addHandler(handler)


def recent(after_id: int = 0, limit: int = 200) -> list[dict]:
    """Returns entries with id > after_id, oldest first, capped at `limit`."""
    with _lock:
        entries = [e for e in _buffer if e["id"] > after_id]
    return entries[-limit:]
