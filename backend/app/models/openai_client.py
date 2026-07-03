"""OpenAI chat-completion client. Dev-mode only right now — not part of normal routing
(the router's low/mid/high tiers are Ollama/NIM/Claude by design). Exists because
OPENAI_API_KEY is already in .env for GPT Image, and the same key covers /v1/chat/completions,
so it's included as a testable model in the dev-mode picker.
"""
import os
import httpx

API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIClient:
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def complete(self, prompt: str, model: str = DEFAULT_MODEL, max_tokens: int = 1024, **kwargs) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(API_URL, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
