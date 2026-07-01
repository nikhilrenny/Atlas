"""Manifest schema for LLM-generated tools.

A tool manifest is the contract between a generated Python module (must define
`async def run(inputs: dict) -> dict`) and the frontend, which auto-renders an
input form + output panel from this schema alone -- no per-tool frontend code.
"""
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from pydantic import BaseModel, Field

PATTERNS = (
    "search_form",       # page has a search/query box -> tool takes a query string
    "data_extractor",    # page has structured data (table/list) -> tool scrapes + returns it
    "calculator",         # page computes something from inputs -> tool replicates the computation
    "api_wrapper",         # page is backed by a discoverable API -> tool calls it directly
    "form_submitter",       # page has a form with side effects -> tool fills + submits it
    "file_processor",        # tool transforms an uploaded file (e.g. image format conversion)
    "generic",               # fallback: summarizer/fetcher for the page
)

INPUT_TYPES = ("text", "number", "boolean", "select", "file")
OUTPUT_TYPES = ("text", "json", "table", "image")


class ToolInput(BaseModel):
    name: str
    label: str
    type: str = "text"
    required: bool = True
    options: list[str] | None = None  # only for type == "select"
    default: str | None = None


class ToolManifest(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    description: str
    source_url: str
    pattern: str = "generic"
    inputs: list[ToolInput] = []
    output_type: str = "text"
    allowed_domains: list[str] = []
    pinned: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def model_post_init(self, __context) -> None:
        if self.pattern not in PATTERNS:
            self.pattern = "generic"
        if self.output_type not in OUTPUT_TYPES:
            self.output_type = "text"
        if not self.allowed_domains:
            host = urlparse(self.source_url).netloc
            if host:
                self.allowed_domains = [host]
