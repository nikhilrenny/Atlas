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
    tor: bool = False
    stealth: bool = False
    block_unsafe: bool = False  # if true, run a safety check first and 403 on "dangerous"


class BrowserFetchResponse(BaseModel):
    url: str
    title: str
    text: str
    html: str
    memory_id: str | None = None
    safety: "SafetyCheckResponse | None" = None  # populated only when block_unsafe=True


class BrowserScreenshotRequest(BaseModel):
    url: str
    full_page: bool = True
    tor: bool = False
    stealth: bool = False


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


# --- Phase 6: Privacy ---

class PrivacyStatusResponse(BaseModel):
    tor_port_open: bool
    tor_verified: bool  # confirmed actually exiting through Tor, not just port-open
    tor_exit_ip: str | None = None
    error: str | None = None


# --- Phase 7: Safe browsing ---

class SafetyCheckRequest(BaseModel):
    url: str
    deep_scan: bool = False  # let VirusTotal submit+poll unknown URLs (slower, up to ~20s)


class SafeBrowsingResult(BaseModel):
    safe: bool
    threats: list[str] = []


class VirusTotalResult(BaseModel):
    safe: bool
    malicious: int
    suspicious: int
    harmless: int
    undetected: int
    scanned: bool


class HeuristicsResult(BaseModel):
    score: int
    reasons: list[str]


class SafetyCheckResponse(BaseModel):
    url: str
    verdict: str  # "safe" | "suspicious" | "dangerous"
    heuristics: HeuristicsResult
    google_safe_browsing: dict | None = None
    virustotal: dict | None = None


BrowserFetchResponse.model_rebuild()  # resolves the forward-ref to SafetyCheckResponse above


# --- Phase 8: Tool builder ---

class ToolBuildRequest(BaseModel):
    url: str


class ToolInputSchema(BaseModel):
    name: str
    label: str
    type: str = "text"
    required: bool = True
    options: list[str] | None = None
    default: str | None = None


class ToolManifestResponse(BaseModel):
    id: str
    name: str
    description: str
    source_url: str
    pattern: str
    inputs: list[ToolInputSchema]
    output_type: str
    allowed_domains: list[str]
    pinned: bool = False
    created_at: str


class ToolListResponse(BaseModel):
    tools: list[ToolManifestResponse]


class ToolRunRequest(BaseModel):
    inputs: dict = {}


class ToolRunResponse(BaseModel):
    data: object = None
    output_type: str = "text"


class PromptBuildRequest(BaseModel):
    prompt: str
    answers: str | None = None
    round: int = 0


class PromptBuildResponse(BaseModel):
    status: str  # "clarify" | "infeasible" | "ready" | "answered"
    questions: list[str] = []
    reason: str | None = None
    tool: ToolManifestResponse | None = None
    data: object = None
    output_type: str = "text"


class ToolPinRequest(BaseModel):
    pinned: bool


# --- Phase 9: Memory ---

class MemoryRecord(BaseModel):
    id: str
    type: str
    content: str
    data: object
    tags: list[str] = []
    created_at: str
    updated_at: str


class MemoryListResponse(BaseModel):
    memories: list[MemoryRecord]
    total: int


class PreferenceEntry(BaseModel):
    value: str
    confidence: float
    source: str


class PreferencesResponse(BaseModel):
    preferences: dict[str, PreferenceEntry]


class SetPreferenceRequest(BaseModel):
    key: str
    value: str


class MemoryContextResponse(BaseModel):
    memories: list[MemoryRecord] = []
    preferences: dict[str, PreferenceEntry] = {}
