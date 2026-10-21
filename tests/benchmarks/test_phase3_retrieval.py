"""Phase 3 Verification Gate & Benchmarks: MLX Hybrid Indexing, Partitioning & Council Context Provider."""

import time
from pathlib import Path
from typing import Any

import pytest

from app.backend.library.paper_store import PaperStore
from app.backend.retrieval.context_provider import ContextProvider
from app.backend.retrieval.mlx_embed import MLXEmbedder
from app.backend.retrieval.partition_manager import PartitionManager


@pytest.mark.asyncio
async def test_mlx_embedding_throughput_120_chunks_per_sec() -> None:
    """Assertion: MLX embedding throughput >= 120 chunks/second."""
    embedder = MLXEmbedder()
    chunks = [f"Academic research chunk {i}: transformer attention scaling in unified memory." for i in range(150)]

    t0 = time.perf_counter()
    vectors, event = await embedder.embed_batch(chunks)
    elapsed_s = time.perf_counter() - t0

    throughput = len(chunks) / elapsed_s
    assert len(vectors) == 150
    assert vectors.shape[1] == 1024
    assert throughput >= 120.0, f"Throughput was {throughput:.1f} chunks/s (< 120 chunks/s SLA)"


@pytest.mark.asyncio
async def test_partition_isolation_and_cross_talk_block() -> None:
    """Assertion: Strict zero cross-talk between paper partitions; attempted violation raises PARTITION_VIOLATION."""
    pm = PartitionManager()
    pm.create_handle(agent_id="advocate:paper_1", paper_id="paper_1")
    pm.create_handle(agent_id="advocate:paper_2", paper_id="paper_2")

    # Authorized access passes
    await pm.verify_partition_access("advocate:paper_1", "paper_1")

    # Unauthorized access to opponent partition raises PermissionError / PARTITION_VIOLATION
    with pytest.raises(PermissionError) as exc_info:
        await pm.verify_partition_access("advocate:paper_1", "paper_2")
    assert "PARTITION_VIOLATION" in str(exc_info.value)

    # Moderator is denied Qdrant access by design
    with pytest.raises(PermissionError) as mod_exc:
        pm.create_handle("moderator", "paper_1")
    assert "PARTITION_VIOLATION" in str(mod_exc.value)


@pytest.mark.asyncio
async def test_context_provider_knapsack_and_citation_auditing() -> None:
    """Assertion: Grounding chunks knapsack-packed into 1,024 tokens; unsupplied citations logged as CITATION_UNGROUNDED."""
    # Create mock search pipeline that returns candidate chunks
    class MockSearch:
        async def search(self, *args: Any, **kwargs: Any) -> tuple[list[dict[str, Any]], Any]:
            candidates = [
                {
                    "chunk_index": i,
                    "score": 0.95 - (i * 0.05),
                    "text": f"Grounding evidence content {i} demonstrating scaling efficiency.",
                    "section_title": "Methodology",
                    "paper_id": "test_paper",
                    "token_count": 100,
                }
                for i in range(15)  # 15 * 100 tokens = 1500 tokens (exceeds 1,024)
            ]
            return candidates, None

    provider = ContextProvider(rag_budget=1024, search_pipeline=MockSearch())

    bundle = await provider.provide(
        debate_id="debate_123",
        agent_id="advocate:test_paper",
        paper_id="test_paper",
        query_text="scaling efficiency",
        paper_num=1,
        token_budget=1024,
    )

    # Assert knapsack packing SLA: packed tokens <= 1024
    assert bundle.packed_tokens <= 1024
    assert bundle.packed_tokens == 1000  # 10 chunks of 100 tokens
    assert len(bundle.chunks) == 10
    assert bundle.dropped_candidates_count == 5

    # Test citation verification:
    # Valid citation to chunk 2
    valid_text = "According to our architecture [P1 §Methodology #2], throughput is doubled."
    ungrounded_valid = await provider.validate_citations(valid_text, bundle)
    assert len(ungrounded_valid) == 0

    # Unsupplied citation to chunk 99
    hallucinated_text = "As stated in our results [P1 §Results #99], latency is zero."
    ungrounded_invalid = await provider.validate_citations(hallucinated_text, bundle)
    assert len(ungrounded_invalid) == 1
    assert "#99" in ungrounded_invalid[0]


@pytest.mark.asyncio
async def test_corrupt_paper_pdf_hash_detection(tmp_path: Path) -> None:
    """Assertion: Corrupting paper.pdf is detected by hash check and logged as PAPER_STORAGE_ERROR."""
    paper_st = PaperStore(base_dir=tmp_path / "papers")
    pdf_bytes = b"%PDF-1.4 test document content"
    await paper_st.init_paper_folder("paper_hash_test", pdf_bytes, {"paper_id": "paper_hash_test"})

    # Corrupt the PDF binary
    folder = paper_st.get_paper_folder("paper_hash_test")
    pdf_path = folder / "paper.pdf"
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 TAMPERED_DATA_BYTES")

    is_valid = await paper_st.verify_integrity("paper_hash_test")
    assert not is_valid, "Integrity check should fail on hash mismatch"
