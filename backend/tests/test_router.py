"""Manual smoke test for the model router — exercises every routing tier independently
so a failure in one provider doesn't mask the others.

Run from the backend directory with the venv active:
    cd D:\\Projects\\atlas\\backend
    venv\\Scripts\\activate
    python -m tests.test_router
"""
import asyncio

from app.models.router import router


async def main():
    print("--- low complexity (NIM, falls back to Ollama) ---")
    try:
        print(await router.complete("What's 2+2?", complexity="low"))
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- mid complexity (Claude Haiku via API) ---")
    try:
        print(await router.complete("Explain TCP in one sentence.", complexity="mid"))
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- high complexity (Claude Pro OAuth, falls back to API Sonnet) ---")
    try:
        result = await router.complete_verbose("Explain TCP in one sentence.", complexity="high")
        print(f"[{result['provider']}] {result['text']}")
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- embeddings (Ollama, nomic-embed-text) ---")
    try:
        vec = await router.embed("hello world")
        print(f"embedding length: {len(vec)}")
    except Exception as e:
        print(f"FAILED (is Ollama running with nomic-embed-text pulled?): {e}")


if __name__ == "__main__":
    asyncio.run(main())
