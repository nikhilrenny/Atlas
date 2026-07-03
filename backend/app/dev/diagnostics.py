"""System diagnostics for the Settings panel -- best-effort, never raises. Wraps the
model router's existing available_models() with a GPU read via nvidia-smi, since
Atlas has no other way to check VRAM headroom before a local model load.
"""
import asyncio


async def gpu_info() -> dict | None:
    """Parses `nvidia-smi --query-gpu=...` into {name, memory_used_mb, memory_total_mb}.
    Returns None if nvidia-smi isn't on PATH or the call fails -- non-NVIDIA machines
    or a driver hiccup shouldn't break the diagnostics panel."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "nvidia-smi",
            "--query-gpu=name,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        line = stdout.decode().strip().splitlines()[0]
        name, used, total, util = [p.strip() for p in line.split(",")]
        return {
            "name": name,
            "memory_used_mb": int(used),
            "memory_total_mb": int(total),
            "utilization_pct": int(util),
        }
    except Exception:
        return None
