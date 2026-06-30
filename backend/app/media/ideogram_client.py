"""Ideogram client — cloud image generation, alternative to DALL-E 3 (often stronger at
in-image text rendering). Endpoint shape is best-effort from Ideogram's public API docs —
Ideogram's API has changed shape before; verify against https://developer.ideogram.ai
before relying on this in production, same caveat as claude_oauth_client.py's SDK note.
"""
import os

import httpx

API_URL = "https://api.ideogram.ai/generate"


class IdeogramClient:
    def __init__(self):
        self.api_key = os.environ.get("IDEOGRAM_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, aspect_ratio: str = "ASPECT_1_1", model: str = "V_2", **kwargs) -> bytes:
        if not self.api_key:
            raise RuntimeError("IDEOGRAM_API_KEY not set")
        headers = {"Api-Key": self.api_key, "Content-Type": "application/json"}
        payload = {"image_request": {"prompt": prompt, "aspect_ratio": aspect_ratio, "model": model}}
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(API_URL, headers=headers, json=payload)
            r.raise_for_status()
            image_url = r.json()["data"][0]["url"]
            img_r = await client.get(image_url)
            img_r.raise_for_status()
            return img_r.content
