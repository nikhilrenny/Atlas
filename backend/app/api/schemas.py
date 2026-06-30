"""Pydantic request/response schemas for the Atlas API."""
from pydantic import BaseModel


class CompleteRequest(BaseModel):
    prompt: str
    complexity: str | None = None  # "low" | "mid" | "high"; auto-classified by length if omitted


class CompleteResponse(BaseModel):
    text: str
    provider: str
    complexity: str


class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    embedding: list[float]


class ModelsStatusResponse(BaseModel):
    ollama: bool
    nim: bool
    claude_api: bool


class BrowserFetchRequest(BaseModel):
    url: str
    store: bool = False  # if true, the fetched text is embedded and saved to memory
    collection: str = "browser_history"


class BrowserFetchResponse(BaseModel):
    url: str
    title: str
    text: str
    html: str
    memory_id: str | None = None


class BrowserScreenshotRequest(BaseModel):
    url: str
    full_page: bool = True


class BrowserScreenshotResponse(BaseModel):
    url: str
    image_base64: str


class MemoryAddRequest(BaseModel):
    text: str
    metadata: dict | None = None
    collection: str = "memory"


class MemoryAddResponse(BaseModel):
    id: str


class MemorySearchRequest(BaseModel):
    query: str
    n_results: int = 5
    collection: str = "memory"
    where: dict | None = None


class MemorySearchResult(BaseModel):
    id: str
    text: str
    metadata: dict
    distance: float


class MemorySearchResponse(BaseModel):
    results: list[MemorySearchResult]


class MediaImageRequest(BaseModel):
    prompt: str
    provider: str = "auto"  # "auto" | "flux_local" | "dalle3" | "ideogram"
    width: int = 1024
    height: int = 1024


class MediaVideoRequest(BaseModel):
    prompt: str
    image_url: str  # Gen-3 is image-to-video; a source frame is required
    provider: str = "runway"
    duration: int = 5


class MediaAudioRequest(BaseModel):
    text: str
    voice: str | None = None
    provider: str = "elevenlabs"


class MediaResponse(BaseModel):
    provider: str
    mime: str
    path: str
    base64: str


# --- Phase 5: Code IDE ---

class IDERunRequest(BaseModel):
    language: str  # "python" | "javascript"
    code: str
    timeout_s: float = 10.0


class IDERunResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool


class IDEGitStatusRequest(BaseModel):
    repo_path: str


class IDEGitStatusResponse(BaseModel):
    branch: str
    staged: list[str]
    unstaged: list[str]
    untracked: list[str]


class IDEGitDiffRequest(BaseModel):
    repo_path: str
    path: str | None = None
    staged: bool = False


class IDEGitDiffResponse(BaseModel):
    diff: str


class IDEGitCommitRequest(BaseModel):
    repo_path: str
    message: str
    paths: list[str] | None = None


class IDEGitCommitResponse(BaseModel):
    commit_hash: str


class IDEGitLogRequest(BaseModel):
    repo_path: str
    n: int = 10


class IDEGitLogEntry(BaseModel):
    hash: str
    author: str
    date: str
    subject: str


class IDEGitLogResponse(BaseModel):
    entries: list[IDEGitLogEntry]


class IDECompleteRequest(BaseModel):
    code: str
    instruction: str
    language: str = "python"


class IDECompleteResponse(BaseModel):
    code: str
