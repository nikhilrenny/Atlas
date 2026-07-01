"""Executes generated tool code with real network-egress enforcement.

SECURITY MODEL (the honest version, see ide/sandbox.py's note for why this module
exists): this is still a process sandbox, not a container/VM. The generated code
runs as the same OS user with full filesystem access in theory. Two real, enforced
controls are layered on top to make that acceptable for LLM-generated code pulled
from arbitrary pages:

  1. Network allowlist enforced at the socket layer (monkeypatching
     socket.getaddrinfo in the child process, BEFORE the generated module is
     imported). This is not a prompt instruction the model can ignore -- every
     HTTP library in Python (requests, httpx, urllib) resolves hosts through
     socket.getaddrinfo, so a host outside manifest.allowed_domains raises
     PermissionError no matter what the generated code does.
  2. A stripped environment (no ANTHROPIC_API_KEY, no other Atlas secrets) and a
     throwaway temp working directory, deleted after the run.

What this does NOT protect against: malicious filesystem access within the temp
dir's parent paths, CPU/memory exhaustion beyond the wall-clock timeout, or a
sufficiently creative DNS-rebinding-style bypass of the allowlist. If Phase 8
moves from personal-use to anything multi-user, swap this for a real container
(gVisor/Docker) before that happens.
"""
import asyncio
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

_HARNESS = '''
import asyncio, json, os, socket, sys

_allowed = set(filter(None, os.environ.get("ATLAS_ALLOWED_DOMAINS", "").split(",")))

def _domain_ok(host):
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="ignore")
    host = (host or "").lower()
    return any(host == d or host.endswith("." + d) for d in _allowed)

_orig_getaddrinfo = socket.getaddrinfo
def _guarded_getaddrinfo(host, *a, **kw):
    if not _domain_ok(host):
        raise PermissionError(f"atlas sandbox: network access to {host!r} is not allowed "
                               f"(allowed: {sorted(_allowed)})")
    return _orig_getaddrinfo(host, *a, **kw)
socket.getaddrinfo = _guarded_getaddrinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tool

with open("inputs.json", encoding="utf-8") as f:
    inputs = json.load(f)

result = asyncio.run(tool.run(inputs))
print("__ATLAS_RESULT__" + json.dumps(result))
'''

TIMEOUT_S = 20.0


async def execute(code: str, inputs: dict, allowed_domains: list[str], timeout_s: float = TIMEOUT_S) -> dict:
    workdir = Path(tempfile.gettempdir()) / f"atlas_tool_{uuid.uuid4().hex}"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "tool.py").write_text(code, encoding="utf-8")
    (workdir / "harness.py").write_text(_HARNESS, encoding="utf-8")
    (workdir / "inputs.json").write_text(json.dumps(inputs), encoding="utf-8")

    exe = shutil.which("python")
    if exe is None:
        shutil.rmtree(workdir, ignore_errors=True)
        raise RuntimeError("python interpreter not found on PATH")

    # Stripped env: PATH + minimal Windows requirements, no Atlas secrets, plus the allowlist.
    env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "ATLAS_ALLOWED_DOMAINS": ",".join(allowed_domains),
    }

    stdout, stderr, exit_code, timed_out = "", "", None, False
    proc = await asyncio.create_subprocess_exec(
        exe, "harness.py", cwd=workdir, env=env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
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

    if timed_out:
        raise RuntimeError(f"tool execution timed out after {timeout_s}s")
    if exit_code != 0:
        raise RuntimeError(f"tool execution failed (exit {exit_code}): {stderr.strip()[-2000:]}")

    marker = "__ATLAS_RESULT__"
    line = next((l for l in stdout.splitlines() if l.startswith(marker)), None)
    if line is None:
        raise RuntimeError(f"tool produced no result marker. stdout: {stdout[-1000:]} stderr: {stderr[-1000:]}")
    return json.loads(line[len(marker):])
