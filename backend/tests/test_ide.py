"""Manual smoke test for the IDE module — sandbox runner (Python + JS, including a
timeout case), git ops (against this repo itself), and AI completion.

Run from the backend directory with the venv active:
    python -m tests.test_ide
"""
import asyncio

from app.ide import sandbox, git_ops, completion

REPO_PATH = r"D:\Projects\atlas"


async def main():
    print("--- sandbox: python ---")
    try:
        result = await sandbox.run("python", "print('hello from python sandbox')")
        print(result)
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- sandbox: javascript ---")
    try:
        result = await sandbox.run("javascript", "console.log('hello from js sandbox')")
        print(result)
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- sandbox: timeout enforcement ---")
    try:
        result = await sandbox.run("python", "import time; time.sleep(5)", timeout_s=1.0)
        print(result)
        assert result["timed_out"] is True, "expected timed_out=True"
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- sandbox: error in user code surfaces in stderr ---")
    try:
        result = await sandbox.run("python", "raise ValueError('boom')")
        print(result)
        assert result["exit_code"] != 0
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- git: status ---")
    try:
        result = await git_ops.status(REPO_PATH)
        print(result)
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- git: log ---")
    try:
        entries = await git_ops.log(REPO_PATH, n=3)
        for e in entries:
            print(e)
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n--- ai completion ---")
    try:
        result = await completion.complete(
            code="def add(a, b):\n    return a + b\n",
            instruction="Add a docstring and type hints.",
            language="python",
        )
        print(result)
    except Exception as e:
        print(f"FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(main())
