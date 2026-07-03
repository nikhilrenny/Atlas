"""NVIDIA NIM client — free cloud tier via build.nvidia.com, OpenAI-compatible API. Used for low-complexity routing."""
import os
import httpx

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"


class NIMClient:
    def __init__(self):
        self.api_key = os.environ.get("NVIDIA_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def complete(self, prompt: str, model: str = DEFAULT_MODEL, max_tokens: int = 1024, timeout: float = 8.0, **kwargs) -> str:
        if not self.api_key:
            raise RuntimeError("NVIDIA_API_KEY not set")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(f"{NIM_BASE_URL}/chat/completions", headers=headers, json=payload)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except httpx.TimeoutException:
            # httpx timeout exceptions carry no message text (str(e) == ""), which surfaces
            # as a blank/unhelpful error upstream -- give it one explicitly.
            raise RuntimeError(f"NIM request timed out after {timeout}s (model={model})")
