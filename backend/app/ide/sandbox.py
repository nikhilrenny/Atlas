"""Subprocess-based runner for Python and JS snippets written in the IDE panel.

SECURITY NOTE (read before reusing this for anything else): this is a *process*
sandbox, not a *security* sandbox. It isolates via a throwaway temp dir + a hard
wall-clock timeout, but the child process still runs as the same OS user, with full
filesystem and network access. That's an acceptable trade-off for code Nik writes
himself in his own IDE panel. It is NOT acceptable for Phase 8 (tool builder), which
will execute LLM-generated code pulled from arbitrary web pages — that needs real
isolation (container, gVisor, or at minimum a locked-down service account) before
anything auto-generated is ever run. Don't copy this module's trust model forward.
"""
import asyncio
import shutil
import tempfile
import uuid
from pathlib import Path

RUNNERS = {
    "python": {"filename": "main.py", "cmd": lambda exe: [exe, "main.py"]},
    "javascript": {"filename": "main.js", "cmd": lambda exe: [exe, "main.js"]},
}
INTERPRETER = {"python": "python", "javascript": "node"}


async def run(language: str, code: str, timeout_s: float = 10.0) -> dict:
    """Writes `code` to a temp file and executes it with a hard timeout.

    Returns {stdout, stderr, exit_code, timed_out}. exit_code is None when the
    process was killed for exceeding timeout_s.
    """
    if language not in RUNNERS:
        raise ValueError(f"unsupported language: {language!r} (expected one of {list(RUNNERS)})")

    spec = RUNNERS[language]
    workdir = Path(tempfile.gettempdir()) / f"atlas_ide_{uuid.uuid4().hex}"
    workdir.mkdir(parents=True, exist_ok=True)
    script_path = workdir / spec["filename"]
    script_path.write_text(code, encoding="utf-8")

    exe = shutil.which(INTERPRETER[language])
    if exe is None:
        shutil.rmtree(workdir, ignore_errors=True)
        raise RuntimeError(f"interpreter not found on PATH: {INTERPRETER[language]}")

    cmd = spec["cmd"](exe)
    timed_out = False
    stdout, stderr, exit_code = "", "", None

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=workdir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        stdout, stderr = out.decode(errors="replace"), err.decode(errors="replace")
        exit_code = proc.returncode
    except asyncio.TimeoutError:
        timed_out = True
        proc.kill()
        await proc.wait()
        stderr = f"killed: exceeded {timeout_s}s timeout"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return {"stdout": stdout, "stderr": stderr, "exit_code": exit_code, "timed_out": timed_out}
