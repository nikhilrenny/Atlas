"""Git integration via subprocess calls to the system `git` binary — no GitPython
dependency, matching the project's lean-deps pattern (browser engine uses Playwright
directly, media uses raw HTTP clients, etc).

All functions take an explicit repo_path so the IDE panel can point at any repo on
disk, not just D:\\Projects\\atlas itself.
"""
import asyncio
import shutil
from pathlib import Path


class GitError(Exception):
    pass


def _check_repo(repo_path: str) -> Path:
    path = Path(repo_path)
    if not path.is_dir():
        raise GitError(f"not a directory: {repo_path}")
    if not (path / ".git").exists():
        raise GitError(f"not a git repo (no .git dir): {repo_path}")
    return path


async def _git(repo_path: str, *args: str) -> str:
    exe = shutil.which("git")
    if exe is None:
        raise GitError("git not found on PATH")
    _check_repo(repo_path)
    proc = await asyncio.create_subprocess_exec(
        exe, "-C", repo_path, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise GitError(err.decode(errors="replace").strip() or f"git {' '.join(args)} failed")
    return out.decode(errors="replace")


async def status(repo_path: str) -> dict:
    """Returns {branch, staged: [...], unstaged: [...], untracked: [...]}."""
    branch = (await _git(repo_path, "branch", "--show-current")).strip()
    raw = await _git(repo_path, "status", "--porcelain=v1")
    staged, unstaged, untracked = [], [], []
    for line in raw.splitlines():
        if not line:
            continue
        code, path = line[:2], line[3:]
        if code == "??":
            untracked.append(path)
        else:
            if code[0] != " ":
                staged.append(path)
            if code[1] != " ":
                unstaged.append(path)
    return {"branch": branch, "staged": staged, "unstaged": unstaged, "untracked": untracked}


async def diff(repo_path: str, path: str | None = None, staged: bool = False) -> str:
    args = ["diff", "--staged"] if staged else ["diff"]
    if path:
        args += ["--", path]
    return await _git(repo_path, *args)


async def add(repo_path: str, paths: list[str]) -> None:
    await _git(repo_path, "add", *paths)


async def commit(repo_path: str, message: str, paths: list[str] | None = None) -> str:
    """Stages `paths` (if given) then commits. Returns the new commit hash."""
    if paths:
        await add(repo_path, paths)
    await _git(repo_path, "commit", "-m", message)
    return (await _git(repo_path, "rev-parse", "HEAD")).strip()


async def log(repo_path: str, n: int = 10) -> list[dict]:
    raw = await _git(repo_path, "log", f"-{n}", "--pretty=format:%H\x1f%an\x1f%ad\x1f%s", "--date=iso")
    entries = []
    for line in raw.splitlines():
        if not line:
            continue
        commit_hash, author, date, subject = line.split("\x1f", 3)
        entries.append({"hash": commit_hash, "author": author, "date": date, "subject": subject})
    return entries
