"""RunwayML video client — cloud video generation.

CAVEAT (same spirit as claude_oauth_client.py's SDK note): Runway's public API is
image-to-video, not pure text-to-video — you submit a source image plus a text prompt
describing the motion. Endpoint paths and the async task shape (submit -> poll a task id
-> get an output url) are best-effort from Runway's dev docs as of this writing; verify
against https://docs.dev.runwayml.com before relying on this in production.

MODEL NOTE: Gen-3 Alpha Turbo is deprecated and sunsets 2026-07-30. Default here is
gen4_turbo (the recommended replacement for speed/cost); use gen4.5 for best quality.
"""
import asyncio
import os

import httpx

API_BASE = "https://api.dev.runwayml.com/v1"
API_VERSION = "2024-11-06"
DEFAULT_MODEL = "gen4_turbo"


class RunwayClient:
    def __init__(self):
        self.api_key = os.environ.get("RUNWAY_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        image_url: str,
        model: str = DEFAULT_MODEL,
        duration: int = 5,
        timeout_s: int = 300,
        **kwargs,
    ) -> bytes:
        """image_url must be a publicly reachable URL or data URI — Gen-3 is image-to-video,
        so a source frame is required, not optional."""
        if not self.api_key:
            raise RuntimeError("RUNWAY_API_KEY not set")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Runway-Version": API_VERSION,
            "Content-Type": "application/json",
        }
        payload = {"promptImage": image_url, "promptText": prompt, "model": model, "duration": duration}

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{API_BASE}/image_to_video", headers=headers, json=payload)
            r.raise_for_status()
            task_id = r.json()["id"]

            elapsed = 0
            poll_interval = 5
            while elapsed < timeout_s:
                status_r = await client.get(f"{API_BASE}/tasks/{task_id}", headers=headers)
                status_r.raise_for_status()
                task = status_r.json()
                if task["status"] == "SUCCEEDED":
                    video_url = task["output"][0]
                    video_r = await client.get(video_url, timeout=60)
                    video_r.raise_for_status()
                    return video_r.content
                if task["status"] == "FAILED":
                    raise RuntimeError(f"Runway task {task_id} failed: {task.get('failure')}")
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

        raise TimeoutError(f"Runway task {task_id} did not finish within {timeout_s}s")
