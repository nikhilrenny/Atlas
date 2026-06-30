"""Ollama client — local models, free, private. Used for embeddings and low-stakes local completion."""
import httpx

OLLAMA_HOST = "http://localhost:11434"


class OllamaClient:
    def __init__(self, host: str = OLLAMA_HOST):
        self.host = host

    async def complete(self, prompt: str, model: str = "llama3.1:8b", **kwargs) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.host}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            return r.json()["response"]

    async def embed(self, text, model: str = "nomic-embed-text"):
        single = isinstance(text, str)
        texts = [text] if single else text
        out = []
        async with httpx.AsyncClient(timeout=60) as client:
            for t in texts:
                r = await client.post(
                    f"{self.host}/api/embeddings", json={"model": model, "prompt": t}
                )
                r.raise_for_status()
                out.append(r.json()["embedding"])
        return out[0] if single else out

    async def list_models(self):
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{self.host}/api/tags")
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{self.host}/api/tags")
                return r.status_code == 200
        except Exception:
            return False
