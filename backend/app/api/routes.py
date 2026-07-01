"""API routes exposing the model router, browser engine, and memory store to the frontend."""
import base64

from fastapi import APIRouter, HTTPException

from app.models.router import router as model_router
from app.browser.engine import engine as browser_engine
from app.search.memory import memory as memory_store
from app.media.router import media_router
from app.ide import sandbox as ide_sandbox
from app.ide import git_ops as ide_git
from app.ide import completion as ide_completion
from app.privacy import tor_proxy
from app.safety import checker as safety_checker
from app import toolbuilder
from app.toolbuilder.registry import registry as tool_registry
from app.api.schemas import (
    CompleteRequest,
    CompleteResponse,
    EmbedRequest,
    EmbedResponse,
    ModelsStatusResponse,
    BrowserFetchRequest,
    BrowserFetchResponse,
    BrowserScreenshotRequest,
    BrowserScreenshotResponse,
    MemoryAddRequest,
    MemoryAddResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySearchResult,
    MediaImageRequest,
    MediaVideoRequest,
    MediaAudioRequest,
    MediaResponse,
    IDERunRequest,
    IDERunResponse,
    IDEGitStatusRequest,
    IDEGitStatusResponse,
    IDEGitDiffRequest,
    IDEGitDiffResponse,
    IDEGitCommitRequest,
    IDEGitCommitResponse,
    IDEGitLogRequest,
    IDEGitLogResponse,
    IDECompleteRequest,
    IDECompleteResponse,
    PrivacyStatusResponse,
    SafetyCheckRequest,
    SafetyCheckResponse,
)
from app.ide.git_ops import GitError
from app.api.schemas import (
    ToolBuildRequest,
    ToolManifestResponse,
    ToolListResponse,
    ToolRunRequest,
    ToolRunResponse,
    PromptBuildRequest,
    PromptBuildResponse,
    ToolPinRequest,
    MemoryRecord,
    MemoryListResponse,
    PreferenceEntry,
    PreferencesResponse,
    SetPreferenceRequest,
)

router = APIRouter()


@router.post("/chat", response_model=CompleteResponse)
async def chat(req: CompleteRequest):
    try:
        result = await model_router.complete_verbose(req.prompt, complexity=req.complexity)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return CompleteResponse(**result)


@router.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest):
    try:
        vector = await model_router.embed(req.text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return EmbedResponse(embedding=vector)


@router.get("/models/status", response_model=ModelsStatusResponse)
async def models_status():
    return ModelsStatusResponse(
        ollama=await model_router.ollama.is_available(),
        nim=model_router.nim.is_available(),
        claude_api=model_router.claude_api.is_available(),
    )


@router.post("/browser/fetch", response_model=BrowserFetchResponse)
async def browser_fetch(req: BrowserFetchRequest):
    safety_result = None
    if req.block_unsafe:
        verdict = await safety_checker.check_url(req.url)
        safety_result = SafetyCheckResponse(**verdict)
        if safety_result.verdict == "dangerous":
            raise HTTPException(
                status_code=403,
                detail=f"Blocked unsafe URL: {req.url} (reasons: {safety_result.heuristics.reasons})",
            )

    try:
        result = await browser_engine.fetch(req.url, tor=req.tor, stealth=req.stealth)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    memory_id = None
    if req.store:
        memory_id = await memory_store.add(
            result["text"],
            metadata={"url": result["url"], "title": result["title"]},
            collection=req.collection,
        )
    return BrowserFetchResponse(**result, memory_id=memory_id, safety=safety_result)


@router.post("/browser/screenshot", response_model=BrowserScreenshotResponse)
async def browser_screenshot(req: BrowserScreenshotRequest):
    try:
        png_bytes = await browser_engine.screenshot(
            req.url, full_page=req.full_page, tor=req.tor, stealth=req.stealth
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return BrowserScreenshotResponse(url=req.url, image_base64=base64.b64encode(png_bytes).decode())


@router.post("/memory/add", response_model=MemoryAddResponse)
async def memory_add(req: MemoryAddRequest):
    try:
        doc_id = await memory_store.add(req.text, metadata=req.metadata, collection=req.collection)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return MemoryAddResponse(id=doc_id)


@router.post("/memory/search", response_model=MemorySearchResponse)
async def memory_search(req: MemorySearchRequest):
    try:
        results = await memory_store.search(
            req.query, n_results=req.n_results, collection=req.collection, where=req.where
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return MemorySearchResponse(results=[MemorySearchResult(**r) for r in results])


@router.post("/media/image", response_model=MediaResponse)
async def media_image(req: MediaImageRequest):
    try:
        result = await media_router.image(
            req.prompt, provider=req.provider, width=req.width, height=req.height
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return MediaResponse(
        provider=result["provider"],
        mime=result["mime"],
        path=result["path"],
        base64=base64.b64encode(result["bytes"]).decode(),
    )


@router.post("/media/video", response_model=MediaResponse)
async def media_video(req: MediaVideoRequest):
    try:
        result = await media_router.video(
            req.prompt, image_url=req.image_url, provider=req.provider, duration=req.duration
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return MediaResponse(
        provider=result["provider"],
        mime=result["mime"],
        path=result["path"],
        base64=base64.b64encode(result["bytes"]).decode(),
    )


@router.post("/media/audio", response_model=MediaResponse)
async def media_audio(req: MediaAudioRequest):
    try:
        result = await media_router.audio(req.text, voice=req.voice, provider=req.provider)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return MediaResponse(
        provider=result["provider"],
        mime=result["mime"],
        path=result["path"],
        base64=base64.b64encode(result["bytes"]).decode(),
    )


# --- Phase 5: Code IDE ---

@router.post("/ide/run", response_model=IDERunResponse)
async def ide_run(req: IDERunRequest):
    try:
        result = await ide_sandbox.run(req.language, req.code, timeout_s=req.timeout_s)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return IDERunResponse(**result)


@router.post("/ide/git/status", response_model=IDEGitStatusResponse)
async def ide_git_status(req: IDEGitStatusRequest):
    try:
        result = await ide_git.status(req.repo_path)
    except GitError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return IDEGitStatusResponse(**result)


@router.post("/ide/git/diff", response_model=IDEGitDiffResponse)
async def ide_git_diff(req: IDEGitDiffRequest):
    try:
        result = await ide_git.diff(req.repo_path, path=req.path, staged=req.staged)
    except GitError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return IDEGitDiffResponse(diff=result)


@router.post("/ide/git/commit", response_model=IDEGitCommitResponse)
async def ide_git_commit(req: IDEGitCommitRequest):
    try:
        commit_hash = await ide_git.commit(req.repo_path, req.message, paths=req.paths)
    except GitError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return IDEGitCommitResponse(commit_hash=commit_hash)


@router.post("/ide/git/log", response_model=IDEGitLogResponse)
async def ide_git_log(req: IDEGitLogRequest):
    try:
        entries = await ide_git.log(req.repo_path, n=req.n)
    except GitError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return IDEGitLogResponse(entries=entries)


@router.post("/ide/complete", response_model=IDECompleteResponse)
async def ide_complete(req: IDECompleteRequest):
    try:
        code = await ide_completion.complete(req.code, req.instruction, language=req.language)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return IDECompleteResponse(code=code)


# --- Phase 6: Privacy ---

@router.get("/privacy/status", response_model=PrivacyStatusResponse)
async def privacy_status():
    port_open = tor_proxy.is_port_open()
    if not port_open:
        return PrivacyStatusResponse(tor_port_open=False, tor_verified=False)
    try:
        result = await tor_proxy.check_exit_ip()
        return PrivacyStatusResponse(
            tor_port_open=True, tor_verified=bool(result.get("IsTor")), tor_exit_ip=result.get("IP")
        )
    except Exception as e:
        return PrivacyStatusResponse(tor_port_open=True, tor_verified=False, error=str(e))


# --- Phase 7: Safe browsing ---

@router.post("/safety/check", response_model=SafetyCheckResponse)
async def safety_check(req: SafetyCheckRequest):
    result = await safety_checker.check_url(req.url, deep_scan=req.deep_scan)
    return SafetyCheckResponse(**result)


# --- Phase 8: Tool builder ---

@router.post("/toolbuilder/generate", response_model=ToolManifestResponse)
async def toolbuilder_generate(req: ToolBuildRequest):
    try:
        manifest = await toolbuilder.build_from_url(req.url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return ToolManifestResponse(**manifest.model_dump())


@router.get("/toolbuilder/tools", response_model=ToolListResponse)
async def toolbuilder_list():
    return ToolListResponse(tools=[ToolManifestResponse(**m.model_dump()) for m in tool_registry.list()])


@router.get("/toolbuilder/tools/{tool_id}", response_model=ToolManifestResponse)
async def toolbuilder_get(tool_id: str):
    manifest = tool_registry.get(tool_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="tool not found")
    return ToolManifestResponse(**manifest.model_dump())


@router.post("/toolbuilder/tools/{tool_id}/run", response_model=ToolRunResponse)
async def toolbuilder_run(tool_id: str, req: ToolRunRequest):
    manifest = tool_registry.get(tool_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="tool not found")
    try:
        result = await toolbuilder.run_tool(tool_id, req.inputs)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return ToolRunResponse(data=result.get("data"), output_type=manifest.output_type)


@router.delete("/toolbuilder/tools/{tool_id}")
async def toolbuilder_delete(tool_id: str):
    if not tool_registry.delete(tool_id):
        raise HTTPException(status_code=404, detail="tool not found")
    return {"deleted": tool_id}


@router.post("/toolbuilder/tools/{tool_id}/pin", response_model=ToolManifestResponse)
async def toolbuilder_pin(tool_id: str, req: ToolPinRequest):
    manifest = tool_registry.set_pinned(tool_id, req.pinned)
    if manifest is None:
        raise HTTPException(status_code=404, detail="tool not found")
    return ToolManifestResponse(**manifest.model_dump())


@router.post("/toolbuilder/build_from_prompt", response_model=PromptBuildResponse)
async def toolbuilder_build_from_prompt(req: PromptBuildRequest):
    try:
        result = await toolbuilder.build_from_prompt(req.prompt, answers=req.answers, round=req.round)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    if result["status"] == "ready":
        return PromptBuildResponse(status="ready", tool=ToolManifestResponse(**result["manifest"].model_dump()))
    if result["status"] == "answered":
        return PromptBuildResponse(status="answered", data=result["data"], output_type=result["output_type"])
    return PromptBuildResponse(**result)


# --- Phase 9: Memory ---

from app import memory as atlas_memory


@router.get("/memory", response_model=MemoryListResponse)
async def memory_list(type: str | None = None, limit: int = 50, offset: int = 0):
    records = atlas_memory.list_memories(type_=type, limit=limit, offset=offset)
    return MemoryListResponse(memories=records, total=len(records))


@router.get("/memory/search", response_model=MemoryListResponse)
async def memory_search_get(q: str, limit: int = 5):
    records = await atlas_memory.search(q, limit=limit)
    return MemoryListResponse(memories=records, total=len(records))


@router.delete("/memory/{memory_id}")
async def memory_delete(memory_id: str):
    if not atlas_memory.delete_memory(memory_id):
        raise HTTPException(status_code=404, detail="memory not found")
    return {"deleted": memory_id}


@router.get("/memory/preferences", response_model=PreferencesResponse)
async def memory_preferences():
    prefs = atlas_memory.get_preferences()
    return PreferencesResponse(preferences={
        k: PreferenceEntry(**v) for k, v in prefs.items()
    })


@router.post("/memory/preferences")
async def memory_set_preference(req: SetPreferenceRequest):
    atlas_memory.set_preference(req.key, req.value, source="explicit")
    return {"set": req.key, "value": req.value}
