"""Pydantic request/response schemas for the Atlas API."""
from pydantic import BaseModel


class CompleteRequest(BaseModel):
    prompt: str
    complexity: str | None = None  # "low" | "mid" | "high"; auto-classified by length if omitted
    prefer_free: bool | None = None  # None -> falls back to the Settings panel's prefer_free


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


# --- Dev mode: direct model testing, bypasses routing ---

class DevProviderModels(BaseModel):
    available: bool
    models: list[str]


class DevModelsResponse(BaseModel):
    ollama: DevProviderModels
    nim: DevProviderModels
    claude_api: DevProviderModels
    claude_oauth: DevProviderModels
    openai: DevProviderModels


class DevCompleteRequest(BaseModel):
    prompt: str
    provider: str  # "ollama" | "nim" | "claude_api" | "claude_oauth"
    model: str | None = None


class DevCompleteResponse(BaseModel):
    text: str
    provider: str
    model: str | None


class DevActivityEntry(BaseModel):
    id: int
    ts: float
    level: str
    logger: str
    message: str


class DevActivityResponse(BaseModel):
    entries: list[DevActivityEntry]


class DevUsageProvider(BaseModel):
    calls: int
    cost_usd: float
    avg_latency_ms: float


class DevUsageResponse(BaseModel):
    total_calls: int
    total_cost_usd: float
    by_provider: dict[str, DevUsageProvider]


# --- Settings panel ---

class SettingsResponse(BaseModel):
    prefer_free: bool
    default_tor: bool
    default_stealth: bool
    default_block_unsafe: bool


class SettingsUpdateRequest(BaseModel):
    prefer_free: bool | None = None
    default_tor: bool | None = None
    default_stealth: bool | None = None
    default_block_unsafe: bool | None = None


class GPUInfo(BaseModel):
    name: str
    memory_used_mb: int
    memory_total_mb: int
    utilization_pct: int


class DiagnosticsResponse(BaseModel):
    ollama: DevProviderModels
    nim: DevProviderModels
    claude_api: DevProviderModels
    claude_oauth: DevProviderModels
    openai: DevProviderModels
    gpu: GPUInfo | None = None


class BrowserFetchRequest(BaseModel):
    url: str
    store: bool = False  # if true, the fetched text is embedded and saved to memory
    collection: str = "browser_history"
    tor: bool | None = None       # None -> falls back to the Settings panel's default_tor
    stealth: bool | None = None   # None -> falls back to the Settings panel's default_stealth
    block_unsafe: bool | None = None  # None -> falls back to default_block_unsafe


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
    tor: bool | None = None
    stealth: bool | None = None


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
    force_provider: str | None = None
    force_model: str | None = None


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
    force_provider: str | None = None  # dev mode: force this provider for both assess+generate steps
    force_model: str | None = None


class ClarifyQuestion(BaseModel):
    question: str
    options: list[str] | None = None


class PromptBuildResponse(BaseModel):
    status: str  # "clarify" | "infeasible" | "ready" | "answered" | "agent_started"
    questions: list[ClarifyQuestion] = []
    reason: str | None = None
    tool: ToolManifestResponse | None = None
    data: object = None
    output_type: str = "text"
    agent_run_id: str | None = None  # set when status == "agent_started"


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


# --- Phase 10: Agents ---

class AgentRunRequest(BaseModel):
    goal: str
    force_provider: str | None = None
    force_model: str | None = None


class AgentStepResponse(BaseModel):
    id: str
    idx: int
    action: str
    target: str
    params: dict
    status: str
    result: object = None
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class AgentRunResponse(BaseModel):
    id: str
    goal: str
    status: str
    error: str | None = None
    created_at: str
    updated_at: str
    steps: list[AgentStepResponse] = []


class AgentRunListResponse(BaseModel):
    runs: list[AgentRunResponse]


class AgentScheduleRequest(BaseModel):
    goal: str
    recurrence: dict  # {"type": "interval", "minutes": N} | {"type": "daily", "at": "HH:MM"}


class AgentScheduleResponse(BaseModel):
    id: str
    goal: str
    recurrence: dict
    enabled: bool = True
    next_run_at: str
    last_run_at: str | None = None


class AgentScheduleListResponse(BaseModel):
    schedules: list[AgentScheduleResponse]
