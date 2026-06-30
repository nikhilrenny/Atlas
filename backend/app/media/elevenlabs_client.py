"""ElevenLabs client — cloud text-to-speech."""
import os

import httpx

API_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # "Rachel" — ElevenLabs' default premade voice


class ElevenLabsClient:
    def __init__(self):
        self.api_key = os.environ.get("ELEVENLABS_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self, text: str, voice: str = DEFAULT_VOICE_ID, model: str = "eleven_multilingual_v2", **kwargs
    ) -> bytes:
        if not self.api_key:
            raise RuntimeError("ELEVENLABS_API_KEY not set")
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {"text": text, "model_id": model}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{API_BASE}/text-to-speech/{voice}", headers=headers, json=payload)
            r.raise_for_status()
            return r.content
