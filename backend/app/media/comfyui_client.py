"""ComfyUI client — local FLUX image generation on the RTX 5070, free and private.

ComfyUI's API is graph-based: you POST a full node workflow (the same JSON ComfyUI's UI
exports via "Save (API Format)"), it queues it, and you poll /history for the result.
Because the exact node graph (checkpoint name, sampler, LoRAs, etc.) is specific to each
ComfyUI install, this client does NOT hardcode a graph. Instead it loads a workflow JSON
template from disk plus a small "meta" file that says which node IDs to inject prompt/
seed/width/height into — drop your own exported workflow in rather than relying on a
guessed graph.

Setup (one-time, outside Atlas):
  1. Install ComfyUI, load a FLUX.1 Schnell checkpoint.
  2. Build a basic txt2img workflow in the ComfyUI UI, enable "Save (API Format)" in the
     dev menu, export it to app/media/workflows/flux_schnell.json.
  3. Edit app/media/workflows/flux_schnell.meta.json to point at the right node IDs
     (see the placeholder file for the expected shape).
ComfyUI must be running (default http://127.0.0.1:8188) before image() calls will work.
"""
import asyncio
import json
import logging
import uuid
from pathlib import Path

import httpx

logger = logging.getLogger("atlas.media.comfyui")

WORKFLOW_DIR = Path(__file__).resolve().parent / "workflows"
DEFAULT_HOST = "http://127.0.0.1:8188"


class ComfyUIClient:
    def __init__(self, host: str = DEFAULT_HOST, workflow_name: str = "flux_schnell"):
        self.host = host
        self.workflow_path = WORKFLOW_DIR / f"{workflow_name}.json"
        self.meta_path = WORKFLOW_DIR / f"{workflow_name}.meta.json"

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{self.host}/system_stats")
                return r.status_code == 200
        except Exception:
            return False

    def _load_workflow(self, prompt: str, seed: int | None, width: int, height: int) -> dict:
        if not self.workflow_path.exists() or not self.meta_path.exists():
            raise RuntimeError(
                f"No ComfyUI workflow configured at {self.workflow_path}. "
                "Export one from the ComfyUI UI (Save (API Format)) and add a matching "
                ".meta.json — see comfyui_client.py docstring."
            )
        workflow = json.loads(self.workflow_path.read_text(encoding="utf-8"))
        meta = json.loads(self.meta_path.read_text(encoding="utf-8"))

        prompt_node = meta["prompt_node"]
        workflow[prompt_node["id"]]["inputs"][prompt_node["field"]] = prompt

        if seed is not None and "seed_node" in meta:
            seed_node = meta["seed_node"]
            workflow[seed_node["id"]]["inputs"][seed_node["field"]] = seed

        if "size_node" in meta:
            size_node = meta["size_node"]
            workflow[size_node["id"]]["inputs"][size_node.get("width_field", "width")] = width
            workflow[size_node["id"]]["inputs"][size_node.get("height_field", "height")] = height

        return workflow

    async def generate(
        self, prompt: str, seed: int | None = None, width: int = 1024, height: int = 1024, timeout_s: int = 120
    ) -> bytes:
        workflow = self._load_workflow(prompt, seed, width, height)
        client_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{self.host}/prompt", json={"prompt": workflow, "client_id": client_id})
            r.raise_for_status()
            prompt_id = r.json()["prompt_id"]

            # Poll /history rather than the websocket progress feed — simpler, good enough
            # for single-shot generation; switch to websocket if Atlas later needs live
            # progress in the UI.
            elapsed = 0
            poll_interval = 1.5
            while elapsed < timeout_s:
                hist_r = await client.get(f"{self.host}/history/{prompt_id}")
                hist_r.raise_for_status()
                history = hist_r.json()
                if prompt_id in history:
                    outputs = history[prompt_id]["outputs"]
                    image_info = self._first_image(outputs)
                    if image_info:
                        img_r = await client.get(
                            f"{self.host}/view",
                            params={
                                "filename": image_info["filename"],
                                "subfolder": image_info.get("subfolder", ""),
                                "type": image_info.get("type", "output"),
                            },
                        )
                        img_r.raise_for_status()
                        return img_r.content
                    raise RuntimeError(f"ComfyUI job {prompt_id} finished with no image output")
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

        raise TimeoutError(f"ComfyUI job {prompt_id} did not finish within {timeout_s}s")

    @staticmethod
    def _first_image(outputs: dict) -> dict | None:
        for node_output in outputs.values():
            images = node_output.get("images")
            if images:
                return images[0]
        return None
