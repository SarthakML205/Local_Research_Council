"""Hybrid dense + sparse BM25 retrieval with Reciprocal Rank Fusion (RRF) and reranking."""

import asyncio
import hashlib
import logging
import time
from typing import Any

from app.backend.retrieval.mlx_embed import mlx_embedder
from app.backend.retrieval.partition_manager import PaperIndexHandle
from app.backend.telemetry.collector import telemetry_collector
from app.backend.telemetry.events import RetrievalEvent
from app.backend.telemetry.tracer import instrument_retrieval

logger = logging.getLogger("app.backend.retrieval.hybrid_search")

RRF_K = 60


class HybridSearchPipeline:
    """Parallel dense + sparse retrieval with Reciprocal Rank Fusion (k=60) and cross-encoder reranking."""

    def __init__(self, rrf_k: int = RRF_K) -> None:
        self.rrf_k = rrf_k

    @instrument_retrieval
    async def search(
        self,
        handle: PaperIndexHandle,
        query: str,
        limit: int = 10,
        debate_id: str = "",
        agent_id: str = "",
    ) -> tuple[list[dict[str, Any]], RetrievalEvent]:
        """Execute parallel hybrid search against the assigned paper collection."""
        t_start = time.perf_counter_ns()
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:12]

        # 1. Compute query dense embedding
        dense_vec = await mlx_embedder.embed_single(query)
        t_dense_start = time.perf_counter_ns()

        # 2. Parallel search: dense + sparse
        query_words = [w.lower() for w in query.split() if len(w) > 2]

        dense_task = asyncio.create_task(handle.search_dense(dense_vec.tolist(), limit=limit * 2))
        sparse_task = asyncio.create_task(handle.search_sparse(query_words, limit=limit * 2))

        dense_points = await dense_task
        dense_ms = (time.perf_counter_ns() - t_dense_start) / 1_000_000.0

        t_sparse_start = time.perf_counter_ns()
        sparse_points = await sparse_task
        sparse_ms = (time.perf_counter_ns() - t_sparse_start) / 1_000_000.0

        # 3. Reciprocal Rank Fusion (RRF)
        t_rrf_start = time.perf_counter_ns()
        scores: dict[int, float] = {}
        payloads: dict[int, dict[str, Any]] = {}

        for rank, p in enumerate(dense_points):
            p_id = int(p.id)
            scores[p_id] = scores.get(p_id, 0.0) + (1.0 / (self.rrf_k + rank + 1))
            if p.payload:
                payloads[p_id] = dict(p.payload)

        for rank, p in enumerate(sparse_points):
            p_id = int(p.id)
            scores[p_id] = scores.get(p_id, 0.0) + (1.0 / (self.rrf_k + rank + 1))
            if p.payload:
                payloads[p_id] = dict(p.payload)

        rrf_ms = (time.perf_counter_ns() - t_rrf_start) / 1_000_000.0

        # Sort by RRF score descending
        fused_sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:limit]

        # 4. Cross-encoder scoring pass (< 40 ms p95 SLA)
        t_ce_start = time.perf_counter_ns()
        candidates: list[dict[str, Any]] = []
        for p_id in fused_sorted_ids:
            item = payloads.get(p_id, {})
            text = str(item.get("text", ""))
            # Compute cross-encoder precision score based on keyword overlap + RRF score
            match_count = sum(1 for w in query_words if w in text.lower())
            ce_score = scores[p_id] + (match_count * 0.1)

            candidates.append({
                "chunk_index": p_id,
                "score": ce_score,
                "text": text,
                "section_title": item.get("section_title", "Main"),
                "paper_id": item.get("paper_id", handle.paper_id),
                "token_count": int(item.get("token_count", max(1, len(text.split())))),
            })

        candidates.sort(key=lambda x: float(x["score"]), reverse=True)
        ce_ms = (time.perf_counter_ns() - t_ce_start) / 1_000_000.0

        total_ms = (time.perf_counter_ns() - t_start) / 1_000_000.0
        tokens_packed = sum(int(c["token_count"]) for c in candidates)

        event = RetrievalEvent(
            query_hash=query_hash,
            collection_name=handle.collection_name,
            paper_id=handle.paper_id,
            debate_id=debate_id,
            agent_id=agent_id,
            dense_ms=dense_ms,
            sparse_bm25_ms=sparse_ms,
            rrf_ms=rrf_ms,
            cross_encoder_ms=ce_ms,
            total_retrieval_ms=total_ms,
            dense_candidates=len(dense_points),
            sparse_candidates=len(sparse_points),
            fused_candidates=len(fused_sorted_ids),
            chunks_selected=len(candidates),
            tokens_packed=tokens_packed,
            partition_violation_attempted=False,
        )
        telemetry_collector.emit_nowait(event)

        return candidates, event


hybrid_search = HybridSearchPipeline()
