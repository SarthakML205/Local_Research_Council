"""Retrieval engine: MLX embeddings, embedded Qdrant, context partitioning, and RRF search."""

from app.backend.retrieval.context_provider import (
    ContextBundle,
    ContextProvider,
    GroundingChunk,
    context_provider,
)
from app.backend.retrieval.hybrid_search import HybridSearchPipeline, hybrid_search
from app.backend.retrieval.mlx_embed import MLXEmbedder, mlx_embedder
from app.backend.retrieval.partition_manager import (
    PaperIndexHandle,
    PartitionManager,
    partition_manager,
)
from app.backend.retrieval.qdrant_store import QdrantStore, qdrant_store

__all__ = [
    "MLXEmbedder",
    "mlx_embedder",
    "QdrantStore",
    "qdrant_store",
    "PaperIndexHandle",
    "PartitionManager",
    "partition_manager",
    "HybridSearchPipeline",
    "hybrid_search",
    "GroundingChunk",
    "ContextBundle",
    "ContextProvider",
    "context_provider",
]
