"""Vector memory store — ChromaDB persistence layer for Atlas.

Embeddings always come from the model router (Ollama, nomic-embed-text) and are passed
to Chroma explicitly rather than through Chroma's built-in embedding functions, since
those are synchronous and router.embed() is async. This keeps Chroma as pure
storage/retrieval and the router as the single source of truth for embeddings — so if
the embedding model ever changes, there's exactly one place to change it.

Separate named collections (e.g. "browser_history", "chat_history", "tool_outputs") keep
different kinds of memory from polluting each other's search results; "memory" is the
default for anything generic.
"""
import uuid
from pathlib import Path

import chromadb

from app.models.router import router as model_router

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "chroma_db"


class MemoryStore:
    def __init__(self, path: Path = DATA_DIR):
        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(path))

    def _collection(self, name: str):
        return self._client.get_or_create_collection(name)

    async def add(
        self,
        text: str,
        metadata: dict | None = None,
        collection: str = "memory",
        id: str | None = None,
    ) -> str:
        """Embeds `text` and stores it. Returns the id it was stored under."""
        doc_id = id or str(uuid.uuid4())
        embedding = await model_router.embed(text)
        self._collection(collection).add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata or {}],
        )
        return doc_id

    async def add_many(
        self,
        texts: list[str],
        metadatas: list[dict] | None = None,
        collection: str = "memory",
    ) -> list[str]:
        """Batch version of add() — one embedding call for the whole batch."""
        ids = [str(uuid.uuid4()) for _ in texts]
        embeddings = await model_router.embed(texts)
        self._collection(collection).add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas or [{} for _ in texts],
        )
        return ids

    async def search(
        self,
        query: str,
        n_results: int = 5,
        collection: str = "memory",
        where: dict | None = None,
    ) -> list[dict]:
        """Semantic search: embeds the query, returns the n_results closest stored items."""
        query_embedding = await model_router.embed(query)
        result = self._collection(collection).query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )
        if not result["ids"][0]:
            return []
        return [
            {
                "id": result["ids"][0][i],
                "text": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                "distance": result["distances"][0][i],
            }
            for i in range(len(result["ids"][0]))
        ]

    def delete(self, ids: list[str], collection: str = "memory") -> None:
        self._collection(collection).delete(ids=ids)

    def list_collections(self) -> list[str]:
        return [c.name for c in self._client.list_collections()]

    def count(self, collection: str = "memory") -> int:
        return self._collection(collection).count()


memory = MemoryStore()
