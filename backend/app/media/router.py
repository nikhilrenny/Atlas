"""Media router — unifies FLUX (local, ComfyUI), DALL-E 3, Ideogram, RunwayML Gen-3, and
ElevenLabs behind one media() call, the Phase 4 counterpart to app/models/router.py.

Routing:
  image  -> local FLUX/ComfyUI first (free, private, runs on the 5070); falls back to
            GPT Image (OpenAI) if ComfyUI isn't reachable, unless a specific cloud
            provider is requested. Ideogram is opt-in only (not a fallback target) since
            it has different strengths (text-in-image) rather than being a drop-in
            substitute.
  video  -> RunwayML Gen-3 (image-to-video; no local option configured)
  audio  -> ElevenLabs TTS (no local option configured)

Every generated asset is saved to data/media/ and the call returns its path alongside the
raw bytes, so callers (the API layer, the browser/tool-builder UI, agents) can choose
whether to stream bytes back or just reference the file.
"""
import logging

from .comfyui_client import ComfyUIClient
from .gpt_image_client import GptImageClient
from .ideogram_client import IdeogramClient
from .runway_client import RunwayClient
from .elevenlabs_client import ElevenLabsClient
from .storage import save

logger = logging.getLogger("atlas.media.router")


class MediaRouter:
    def __init__(self):
        self.comfyui = ComfyUIClient()
        self.gpt_image = GptImageClient()
        self.ideogram = IdeogramClient()
        self.runway = RunwayClient()
        self.elevenlabs = ElevenLabsClient()

    async def image(self, prompt: str, provider: str = "auto", **kwargs) -> dict:
        if provider in ("auto", "flux_local"):
            if await self.comfyui.is_available():
                try:
                    content = await self.comfyui.generate(prompt, **kwargs)
                    return self._result(content, "image/png", "flux_local")
                except Exception as e:
                    logger.warning(f"ComfyUI/FLUX failed: {e}")
                    if provider == "flux_local":
                        raise
            elif provider == "flux_local":
                raise RuntimeError("ComfyUI not reachable at http://127.0.0.1:8188 — start it first")

        if provider == "ideogram":
            content = await self.ideogram.generate(prompt, **kwargs)
            return self._result(content, "image/png", "ideogram")

        content = await self.gpt_image.generate(prompt, **kwargs)
        return self._result(content, "image/png", "gpt_image")

    async def video(self, prompt: str, image_url: str, provider: str = "runway", **kwargs) -> dict:
        content = await self.runway.generate(prompt, image_url=image_url, **kwargs)
        return self._result(content, "video/mp4", "runway")

    async def audio(self, text: str, voice: str | None = None, provider: str = "elevenlabs", **kwargs) -> dict:
        content = await self.elevenlabs.generate(text, voice=voice, **kwargs) if voice else \
            await self.elevenlabs.generate(text, **kwargs)
        return self._result(content, "audio/mpeg", "elevenlabs")

    async def media(self, type: str, **kwargs) -> dict:
        """Single entrypoint: media(type="image"|"video"|"audio", ...)."""
        if type == "image":
            return await self.image(**kwargs)
        if type == "video":
            return await self.video(**kwargs)
        if type == "audio":
            return await self.audio(**kwargs)
        raise ValueError(f"Unknown media type: {type!r} (expected image, video, or audio)")

    @staticmethod
    def _result(content: bytes, mime: str, provider: str) -> dict:
        path = save(content, mime)
        return {"bytes": content, "mime": mime, "provider": provider, "path": path}


media_router = MediaRouter()
