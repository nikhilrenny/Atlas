"""Persists and serves generated tools. No restart required to register a new tool:
generate() writes manifest.json + tool.py to data/tools/<id>/ and adds it to the
in-memory dict immediately; run() reads code straight off disk each call so manual
edits (e.g. via the Phase 5 IDE panel once wired up) take effect without a reload.
"""
import json
from pathlib import Path

from .manifest import ToolManifest

TOOLS_DIR = Path(__file__).resolve().parents[3] / "data" / "tools"


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolManifest] = {}
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._loaded = True
        TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        for d in TOOLS_DIR.iterdir():
            manifest_path = d / "manifest.json"
            if d.is_dir() and manifest_path.exists():
                try:
                    data = json.loads(manifest_path.read_text(encoding="utf-8"))
                    self._tools[data["id"]] = ToolManifest(**data)
                except Exception:
                    continue  # skip corrupt entries rather than failing startup

    def list(self) -> list[ToolManifest]:
        self._ensure_loaded()
        return sorted(self._tools.values(), key=lambda m: m.created_at, reverse=True)

    def get(self, tool_id: str) -> ToolManifest | None:
        self._ensure_loaded()
        return self._tools.get(tool_id)

    def get_code(self, tool_id: str) -> str:
        path = TOOLS_DIR / tool_id / "tool.py"
        if not path.exists():
            raise KeyError(f"no code found for tool {tool_id}")
        return path.read_text(encoding="utf-8")

    def register(self, manifest: ToolManifest, code: str) -> None:
        self._ensure_loaded()
        tool_dir = TOOLS_DIR / manifest.id
        tool_dir.mkdir(parents=True, exist_ok=True)
        (tool_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        (tool_dir / "tool.py").write_text(code, encoding="utf-8")
        self._tools[manifest.id] = manifest

    def delete(self, tool_id: str) -> bool:
        self._ensure_loaded()
        import shutil
        tool_dir = TOOLS_DIR / tool_id
        if tool_dir.exists():
            shutil.rmtree(tool_dir)
        return self._tools.pop(tool_id, None) is not None

    def set_pinned(self, tool_id: str, pinned: bool) -> ToolManifest | None:
        self._ensure_loaded()
        manifest = self._tools.get(tool_id)
        if manifest is None:
            return None
        manifest.pinned = pinned
        (TOOLS_DIR / tool_id / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        return manifest


registry = ToolRegistry()
