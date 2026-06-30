"""GPT Image client — OpenAI's current image generation API. Cloud fallback when local
FLUX/ComfyUI isn't available.

NOTE: this replaces what used to be DALL-E 3 here. OpenAI removed dall-e-2/dall-e-3 from
the API on 2026-05-12; the replacement family is gpt-image-1 / gpt-image-1.5 / gpt-image-2,
same /v1/images/generations endpoint, different model name. Key differences from the old
DALL-E shape: no response_format param (GPT Image models always return base64), and
quality is low/medium/high instead of standard/hd.
"""
import base64
import os

import httpx

API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = "gpt-image-1"  # stable GA tier; swap to gpt-image-1.5/2 for higher quality at higher cost


class GptImageClient:
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self, prompt: str, size: str = "1024x1024", quality: str = "medium", model: str = DEFAULT_MODEL, **kwargs
    ) -> bytes:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": model, "prompt": prompt, "size": size, "quality": quality, "n": 1}
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(API_URL, headers=headers, json=payload)
            r.raise_for_status()
            b64 = r.json()["data"][0]["b64_json"]
            return base64.b64decode(b64)
