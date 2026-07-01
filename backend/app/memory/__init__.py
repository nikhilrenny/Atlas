"""Atlas memory package. Initialises the DB on import."""
from .store import init_db
from .manager import (
    record_lookup,
    record_tool_execution,
    record_page_visit,
    search,
    context_for,
    set_preference,
)
from .store import (
    list_memories,
    get_memory,
    delete_memory,
    get_preferences,
    get_preference,
)

init_db()
