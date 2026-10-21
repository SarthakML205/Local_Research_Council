"""Embedded Qdrant vector store: 1-collection-per-paper isolation and payload storage."""

import logging
from pathlib import Path
from typing import Any

from qdrant_client import AsyncQdrantClient, models

from app.backend.library.paper_store import paper_store
from app.backend.retrieval.mlx_embed import mlx_embedder
from app.backend.telemetry.events import FailureCode, Severity
from app.backend.telemetry.failure_log import failure_logger
from app.config import settings

logger = logging.getLogger("app.backend.retrieval.qdrant_store")


class QdrantStore:
    """Manages structural 1-collection-per-paper partitions in embedded/local Qdrant."""

    def __init__(
        self,
        storage_path: Path = settings.QDRANT_PATH,
        mode: str = settings.QDRANT_MODE,
        server_url: str = settings.QDRANT_URL,
    ) -> None:
        self.storage_path = storage_path
        self.mode = mode
        self.server_url = server_url
        self._client: AsyncQdrantClient | None = None

    async def get_client(self) -> AsyncQdrantClient:
        """Lazily initialize the AsyncQdrantClient."""
        if self._client is None:
            if self.mode == "server":
                self._client = AsyncQdrantClient(url=self.server_url, prefer_grpc=True)
            else:
                self.storage_path.mkdir(parents=True, exist_ok=True)
                self._client = AsyncQdrantClient(path=str(self.storage_path))
        return self._client

    def get_collection_name(self, paper_id: str) -> str:
        """Derive 1-to-1 collection name from sanitized paper ID."""
        clean = paper_store.sanitize_paper_id(paper_id)
        return f"paper__{clean}"

    async def ensure_paper_collection(self, paper_id: str) -> str:
        """Ensure a single-paper collection exists with dense and sparse vectors."""
        client = await self.get_client()
        coll_name = self.get_collection_name(paper_id)

        try:
            exists = await client.collection_exists(collection_name=coll_name)
            if not exists:
                await client.create_collection(
                    collection_name=coll_name,
                    vectors_config={
                        "dense": models.VectorParams(
                            size=1024,
                            distance=models.Distance.COSINE,
                        )
                    },
                    sparse_vectors_config={
                        "sparse": models.SparseVectorParams(
                            index=models.SparseIndexParams(on_disk=False)
                        )
                    },
                )
            return coll_name
        except Exception as exc:
            await failure_logger.log_failure(
                code=FailureCode.QDRANT_ERROR,
                message=f"Failed ensuring Qdrant collection {coll_name}: {exc}",
                paper_id=paper_id,
                severity=Severity.ERROR,
                component="qdrant_store",
            )
            raise

    async def index_paper_chunks(
        self,
        paper_id: str,
        chunks: list[dict[str, Any]],
    ) -> int:
        """Embed and upsert chunks into the paper's isolated collection."""
        if not chunks:
            return 0
        client = await self.get_client()
        coll_name = await self.ensure_paper_collection(paper_id)

        texts = [c["text"] for c in chunks]
        dense_vectors, _ = await mlx_embedder.embed_batch(texts)

        points: list[models.PointStruct] = []
        for i, chunk in enumerate(chunks):
            chunk_idx = int(chunk["chunk_index"])
            # Generate deterministic sparse weights for exact keyword matching (BM25 surrogate)
            words = set(chunk["text"].lower().split())
            sparse_indices = [abs(hash(w)) % 100000 for w in words]
            sparse_values = [1.0] * len(sparse_indices)

            points.append(
                models.PointStruct(
                    id=chunk_idx,
                    vector={
                        "dense": dense_vectors[i].tolist(),
                        "sparse": models.SparseVector(
                            indices=sparse_indices,
                            values=sparse_values,
                        ),
                    },
                    payload={
                        "paper_id": paper_id,
                        "section_title": chunk.get("section_title", "Main"),
                        "chunk_index": chunk_idx,
                        "token_count": int(chunk.get("token_count", 0)),
                        "text": chunk["text"],
                    },
                )
            )

        try:
            await client.upsert(collection_name=coll_name, points=points)
            await paper_store.mark_stage_completed(paper_id, "indexed")
            return len(points)
        except Exception as exc:
            await failure_logger.log_failure(
                code=FailureCode.QDRANT_ERROR,
                message=f"Failed upserting points to {coll_name}: {exc}",
                paper_id=paper_id,
                severity=Severity.ERROR,
                component="qdrant_store",
            )
            raise

    async def drop_paper_collection(self, paper_id: str) -> bool:
        """Drop collection when a paper is deleted."""
        client = await self.get_client()
        coll_name = self.get_collection_name(paper_id)
        try:
            if await client.collection_exists(coll_name):
                await client.delete_collection(coll_name)
                return True
        except Exception as exc:
            logger.error(f"Failed deleting collection {coll_name}: {exc}")
        return False

    async def count_points(self, paper_id: str) -> int:
        """Return point count in paper collection."""
        client = await self.get_client()
        coll_name = self.get_collection_name(paper_id)
        try:
            if not await client.collection_exists(coll_name):
                return 0
            info = await client.get_collection(coll_name)
            return int(info.points_count or 0)
        except Exception:
            return 0


qdrant_store = QdrantStore()
