"""Persists generated media bytes to disk — data/media/, gitignored, mirrors the
data/chroma_db pattern used by app/search/memory.py."""
import uuid
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "media"

EXT_BY_MIME = {
    "image/png": "png",
    "video/mp4": "mp4",
    "audio/mpeg": "mp3",
}


def save(content: bytes, mime: str) -> str:
    """Writes `content` to a new file under data/media/ and returns its absolute path."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ext = EXT_BY_MIME.get(mime, "bin")
    path = DATA_DIR / f"{uuid.uuid4()}.{ext}"
    path.write_bytes(content)
    return str(path)
