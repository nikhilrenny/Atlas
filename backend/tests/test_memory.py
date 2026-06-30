"""Manual smoke test for the memory store — add, semantic search, and metadata filtering.

Run from the backend directory with the venv active:
    python -m tests.test_memory
"""
import asyncio

from app.search.memory import memory


async def main():
    print("--- add ---")
    try:
        id1 = await memory.add("The RTX 5070 has 8GB of VRAM.", metadata={"topic": "hardware"})
        id2 = await memory.add(
            "Playwright is used for the Atlas browser engine.", metadata={"topic": "architecture"}
        )
        print(f"stored ids: {id1}, {id2}")
    except Exception as e:
        print(f"FAILED: {e}")
        return

    print("\n--- semantic search (no filter) ---")
    try:
        results = await memory.search("how much GPU memory does my laptop have?", n_results=2)
        for r in results:
            print(f"[{r['distance']:.4f}] {r['text']}  ({r['metadata']})")
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- semantic search (metadata filter) ---")
    try:
        results = await memory.search("project setup", n_results=5, where={"topic": "architecture"})
        for r in results:
            print(f"[{r['distance']:.4f}] {r['text']}")
    except Exception as e:
        print(f"FAILED: {e}")

    print(f"\ncollections: {memory.list_collections()}")
    print(f"'memory' collection count: {memory.count()}")


if __name__ == "__main__":
    asyncio.run(main())
