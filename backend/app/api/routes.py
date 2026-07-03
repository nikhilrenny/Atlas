"""API routes exposing the model router, browser engine, and memory store to the frontend."""
import base64
import logging
import traceback

from fastapi import APIRouter, HTTPException

log = logging.getLogger("atlas.api")

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
    DevModelsResponse,
    DevCompleteRequest,
    DevCompleteResponse,
    DevActivityResponse,
    DevUsageResponse,
    SettingsResponse,
    SettingsUpdateRequest,
    DiagnosticsResponse,
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
    from app.dev import settings_store
    prefer_free = req.prefer_free if req.prefer_free is not None else settings_store.get_all()["prefer_free"]
    try:
        result = await model_router.complete_verbose(req.prompt, complexity=req.complexity, prefer_free=prefer_free)
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


@router.get("/dev/models", response_model=DevModelsResponse)
async def dev_models():
    return DevModelsResponse(**await model_router.available_models())


@router.post("/dev/complete", response_model=DevCompleteResponse)
async def dev_complete(req: DevCompleteRequest):
    try:
        result = await model_router.complete_direct(req.prompt, req.provider, model=req.model)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return DevCompleteResponse(**result)


@router.get("/dev/activity", response_model=DevActivityResponse)
async def dev_activity(after_id: int = 0, limit: int = 200):
    from app.dev import activity_log
    return DevActivityResponse(entries=activity_log.recent(after_id=after_id, limit=limit))


@router.get("/dev/usage", response_model=DevUsageResponse)
async def dev_usage():
    from app.models.usage_log import usage_log
    return DevUsageResponse(**usage_log.summary())


@router.post("/dev/usage/reset")
async def dev_usage_reset():
    from app.models.usage_log import usage_log
    usage_log.reset()
    return {"reset": True}


# --- Settings panel ---

@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    from app.dev import settings_store
    return SettingsResponse(**settings_store.get_all())


@router.post("/settings", response_model=SettingsResponse)
async def update_settings(req: SettingsUpdateRequest):
    from app.dev import settings_store
    updated = settings_store.update(req.model_dump(exclude_none=True))
    return SettingsResponse(**updated)


@router.get("/settings/diagnostics", response_model=DiagnosticsResponse)
async def settings_diagnostics():
    from app.dev import diagnostics
    models = await model_router.available_models()
    gpu = await diagnostics.gpu_info()
    return DiagnosticsResponse(**models, gpu=gpu)


@router.post("/browser/fetch", response_model=BrowserFetchResponse)
async def browser_fetch(req: BrowserFetchRequest):
    from app.dev import settings_store
    settings = settings_store.get_all()
    tor = req.tor if req.tor is not None else settings["default_tor"]
    stealth = req.stealth if req.stealth is not None else settings["default_stealth"]
    block_unsafe = req.block_unsafe if req.block_unsafe is not None else settings["default_block_unsafe"]

    safety_result = None
    if block_unsafe:
        verdict = await safety_checker.check_url(req.url)
        safety_result = SafetyCheckResponse(**verdict)
        if safety_result.verdict == "dangerous":
            raise HTTPException(
                status_code=403,
                detail=f"Blocked unsafe URL: {req.url} (reasons: {safety_result.heuristics.reasons})",
            )

    try:
        result = await browser_engine.fetch(req.url, tor=tor, stealth=stealth)
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
    from app.dev import settings_store
    settings = settings_store.get_all()
    tor = req.tor if req.tor is not None else settings["default_tor"]
    stealth = req.stealth if req.stealth is not None else settings["default_stealth"]
    try:
        png_bytes = await browser_engine.screenshot(
            req.url, full_page=req.full_page, tor=tor, stealth=stealth
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
        manifest = await toolbuilder.build_from_url(req.url, force_provider=req.force_provider, force_model=req.force_model)
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
        result = await toolbuilder.build_from_prompt(req.prompt, answers=req.answers, round=req.round, force_provider=req.force_provider, force_model=req.force_model)
    except Exception as e:
        log.error("[toolbuilder] build_from_prompt failed: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=502, detail=str(e) or f"{type(e).__name__} (see server log)")
    if result["status"] == "agent":
        from app import agents as atlas_agents
        run_id = atlas_agents.start_run(result["goal"], force_provider=req.force_provider, force_model=req.force_model)
        return PromptBuildResponse(status="agent_started", agent_run_id=run_id)
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


@router.delete("/memory/clear")
async def memory_clear(type: str | None = None):
    n = atlas_memory.clear_all(type_=type)
    return {"cleared": n}


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


# --- Phase 10: Agents ---

from app import agents as atlas_agents
from app.api.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    AgentRunListResponse,
    AgentScheduleRequest,
    AgentScheduleResponse,
    AgentScheduleListResponse,
)


@router.post("/agents/run", response_model=AgentRunResponse)
async def agents_run(req: AgentRunRequest):
    run_id = atlas_agents.start_run(req.goal, force_provider=req.force_provider, force_model=req.force_model)
    run = atlas_agents.get_run(run_id)
    return AgentRunResponse(**run)


@router.get("/agents/runs", response_model=AgentRunListResponse)
async def agents_list_runs(limit: int = 50):
    return AgentRunListResponse(runs=[AgentRunResponse(**r, steps=[]) for r in atlas_agents.list_runs(limit=limit)])


@router.get("/agents/runs/{run_id}", response_model=AgentRunResponse)
async def agents_get_run(run_id: str):
    run = atlas_agents.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return AgentRunResponse(**run)


@router.post("/agents/schedule", response_model=AgentScheduleResponse)
async def agents_create_schedule(req: AgentScheduleRequest):
    job = atlas_agents.create_schedule(req.goal, req.recurrence)
    return AgentScheduleResponse(**job)


@router.get("/agents/schedule", response_model=AgentScheduleListResponse)
async def agents_list_schedules():
    return AgentScheduleListResponse(schedules=[AgentScheduleResponse(**s) for s in atlas_agents.list_schedules()])


@router.delete("/agents/schedule/{job_id}")
async def agents_delete_schedule(job_id: str):
    if not atlas_agents.delete_schedule(job_id):
        raise HTTPException(status_code=404, detail="schedule not found")
    return {"deleted": job_id}


@router.post("/agents/schedule/{job_id}/toggle")
async def agents_toggle_schedule(job_id: str, enabled: bool):
    if not atlas_agents.set_schedule_enabled(job_id, enabled):
        raise HTTPException(status_code=404, detail="schedule not found")
    return {"id": job_id, "enabled": enabled}
