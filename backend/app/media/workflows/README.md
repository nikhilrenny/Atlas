Drop your exported ComfyUI workflow here as `flux_schnell.json` (ComfyUI UI -> dev mode ->
"Save (API Format)"), and tell the client which node IDs to inject values into via
`flux_schnell.meta.json`.

Example meta file, matching a typical FLUX Schnell txt2img graph:

{
  "prompt_node": {"id": "6", "field": "text"},
  "seed_node":   {"id": "25", "field": "noise_seed"},
  "size_node":   {"id": "27", "width_field": "width", "height_field": "height"}
}

Node IDs are whatever ComfyUI assigned when you built the graph — open the exported JSON
and find the CLIPTextEncode node (positive prompt), the KSampler/RandomNoise node (seed),
and the EmptyLatentImage/EmptySD3LatentImage node (width/height).

Neither file is committed with real content yet — comfyui_client.py raises a clear error
until both exist.
