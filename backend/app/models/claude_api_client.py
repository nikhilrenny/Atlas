"""Claude API client — pay-per-token via ANTHROPIC_API_KEY. Used for mid/high complexity when OAuth path is unavailable."""
import os
from anthropic import AsyncAnthropic

DEFAULT_MID_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_HIGH_MODEL = "claude-sonnet-4-6"


class ClaudeAPIClient:
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        # Set by complete() immediately before return, read by the router right after the
        # awaited call completes (no intervening await in _dispatch, so no cross-request race
        # despite this being shared mutable state on a singleton client).
        self.last_model: str | None = None
        self.last_usage: dict | None = None

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def complete(self, prompt: str, model: str = DEFAULT_MID_MODEL, max_tokens: int = 1024, **kwargs) -> str:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        client = AsyncAnthropic(api_key=self.api_key)
        resp = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        self.last_model = model
        self.last_usage = (
            {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
            if resp.usage else None
        )
        return "".join(b.text for b in resp.content if b.type == "text")
