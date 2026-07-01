"""Claude Pro OAuth client — free access via Claude Code SDK on Pro subscription.

Pops ANTHROPIC_API_KEY from the environment before connecting so the SDK falls back to the
OAuth-authenticated Claude Code session instead of billing the API key. Restores it afterward.

NOTE: claude_agent_sdk's exact surface (ClaudeSDKClient.query / receive_response) was written
from memory of the SDK shape, not verified against the installed package version. Run
test_router.py's oauth smoke test and adjust if the installed SDK's API differs.
"""
import os
import asyncio
from contextlib import contextmanager


@contextmanager
def _pop_api_key():
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


class ClaudeOAuthClient:
    async def complete(self, prompt: str, timeout: float = 45.0, **kwargs) -> str:
        from claude_agent_sdk import ClaudeSDKClient

        async def _run():
            with _pop_api_key():
                async with ClaudeSDKClient() as client:
                    await client.query(prompt)
                    text = ""
                    async for msg in client.receive_response():
                        for block in getattr(msg, "content", []):
                            if hasattr(block, "text"):
                                text += block.text
                    return text

        try:
            return await asyncio.wait_for(_run(), timeout=timeout)
        except asyncio.TimeoutError:
            raise RuntimeError(f"Claude OAuth timed out after {timeout}s")
