"""Verification & Benchmarks for arXiv Boolean Query Syntax, Category Filtering, and Widen-and-Rerank Pipeline."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.backend.ingest.arxiv_client import (
    ArxivClient,
    build_arxiv_boolean_query,
    compute_date_decay_multiplier,
    extract_arxiv_id,
    is_arxiv_id,
    local_cross_encoder_rerank,
    search_and_filter_papers,
)


@pytest.mark.asyncio
async def test_arxiv_field_specific_query_syntax_and_boolean_operators() -> None:
    """Assertion 1: Maps raw user prompt to structured boolean query targeting abs/ti fields with CS categories."""
    raw_query = "agents memory optimization"
    structured = await build_arxiv_boolean_query(
        raw_query,
        target_fields=("abs",),
        categories=["cs.AI", "cs.CL", "cs.LG"],
        try_llm=False,
    )

    # Assert exact field targeting syntax
    assert "abs:agent" in structured or 'abs:"multi-agent"' in structured
    assert "abs:memory" in structured or 'abs:"KV cache"' in structured
    assert "abs:optimization" in structured or "abs:compression" in structured

    # Assert boolean operators AND & OR
    assert " AND " in structured
    assert " OR " in structured

    # Assert category filtering constrained to specified categories
    assert "cat:cs.AI" in structured
    assert "cat:cs.CL" in structured
    assert "cat:cs.LG" in structured
    assert "physics" not in structured


@pytest.mark.asyncio
async def test_category_filtering_default_and_custom() -> None:
    """Assertion 2: Constrains query space to designated Computer Science categories."""
    # Default categories: cs.AI, cs.CL, cs.LG, cs.MA
    q_default = await build_arxiv_boolean_query("quantization pruning", try_llm=False)
    assert "cat:cs.AI" in q_default
    assert "cat:cs.CL" in q_default
    assert "cat:cs.LG" in q_default
    assert "cat:cs.MA" in q_default

    # Custom category filter
    q_custom = await build_arxiv_boolean_query(
        "retrieval augmented", categories=["cs.IR", "cs.CL"], try_llm=False
    )
    assert "cat:cs.IR" in q_custom
    assert "cat:cs.CL" in q_custom
    assert "cat:cs.AI" not in q_custom


@pytest.mark.asyncio
async def test_arxiv_id_extraction_and_direct_routing() -> None:
    """Assertion: Direct arXiv IDs bypass keyword expansion and route cleanly."""
    valid_ids = ["2301.00123", "2401.00001v2", "arxiv:2301.00123", "math.PR/0601001"]
    for vid in valid_ids:
        assert is_arxiv_id(vid) is True
        extracted = extract_arxiv_id(vid)
        assert extracted is not None

    assert is_arxiv_id("agents memory optimization") is False
    assert extract_arxiv_id("agents memory optimization") is None

    # Query generation for direct ID
    q_id = await build_arxiv_boolean_query("2401.00001v1")
    assert q_id == "id:2401.00001v1"


def test_date_decay_multiplier_boosts_recent_penalizes_outdated() -> None:
    """Assertion: Boosts papers <= 24 months old and penalizes outdated research."""
    now = datetime.now(UTC)

    # 1. Recent paper (6 months old) -> receives 1.15x state-of-the-art boost
    recent_date = (now - timedelta(days=180)).isoformat()
    boost_recent = compute_date_decay_multiplier(recent_date)
    assert boost_recent == 1.15

    # 2. 18-month old paper -> receives 1.05x boost
    med_date = (now - timedelta(days=500)).isoformat()
    boost_med = compute_date_decay_multiplier(med_date)
    assert boost_med == 1.05

    # 3. 3-year old paper -> 0.95
    older_date = (now - timedelta(days=1000)).isoformat()
    mult_older = compute_date_decay_multiplier(older_date)
    assert mult_older == 0.95

    # 4. 2017 paper (approx 9 years old) -> penalized down to floor
    archival_date = "2017-06-12T00:00:00Z"
    mult_archival = compute_date_decay_multiplier(archival_date)
    assert mult_archival < 0.90
    assert mult_archival >= 0.65


@pytest.mark.asyncio
async def test_local_cross_encoder_rerank_scoring_and_filtering() -> None:
    """Assertion 3: Widen-and-Rerank local semantic pass scores, date-decays, and sorts candidates."""
    query = "KV cache compression in multi-agent LLM systems"
    now = datetime.now(UTC)

    candidates: list[dict[str, Any]] = [
        {
            "paper_id": "2401.0001",
            "title": "KV Cache Compression and Activation Memory Optimization for LLMs",
            "summary": "We introduce dynamic KV cache compression and token pruning for long context LLM multi-agent reasoning.",
            "published": (now - timedelta(days=90)).isoformat(),  # 2024+ recent
            "authors": ["Author A"],
            "categories": ["cs.AI", "cs.LG"],
        },
        {
            "paper_id": "1706.0002",
            "title": "Attention Is All You Need",
            "summary": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
            "published": "2017-06-12T00:00:00Z",  # 2017 archival
            "authors": ["Vaswani et al."],
            "categories": ["cs.CL"],
        },
        {
            "paper_id": "2402.0003",
            "title": "Robotic Locomotion via Reinforcement Learning",
            "summary": "Quadruped locomotion trained using model-free RL over rugged physical terrains.",
            "published": (now - timedelta(days=60)).isoformat(),
            "authors": ["Author C"],
            "categories": ["cs.RO"],
        },
    ]

    scored = await local_cross_encoder_rerank(
        user_query=query,
        candidates=candidates,
        apply_date_decay=True,
        min_score_threshold=0.10,
    )

    assert len(scored) >= 2
    # The KV Cache Compression paper must rank #1 due to exact concept overlap + recent date boost
    assert scored[0]["paper_id"] == "2401.0001"
    assert scored[0]["score"] > scored[1]["score"]
    assert "raw_score" in scored[0]
    assert "recency_multiplier" in scored[0]
    assert scored[0]["recency_multiplier"] == 1.15


@pytest.mark.asyncio
async def test_widen_and_rerank_pipeline_flow() -> None:
    """Assertion: search_and_filter_papers fetches wide candidate pool and returns top N filtered papers."""
    now = datetime.now(UTC)
    mock_candidates: list[dict[str, Any]] = [
        {
            "paper_id": f"2401.{i:04d}",
            "arxiv_id": f"2401.{i:04d}",
            "title": f"Agent Memory Optimization Method #{i}",
            "summary": f"A scalable approach to multi-agent memory cache pruning and KV state persistence variant {i}.",
            "published": (now - timedelta(days=30 * i)).isoformat(),
            "authors": [f"Researcher {i}"],
            "categories": ["cs.AI", "cs.MA"],
            "pdf_url": f"https://export.arxiv.org/pdf/2401.{i:04d}.pdf",
        }
        for i in range(1, 31)
    ]

    client = ArxivClient()

    with patch.object(client, "fetch_candidates", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_candidates
        with patch("app.backend.ingest.arxiv_client.arxiv_client", client):
            results = await search_and_filter_papers(
                user_query="multi-agent memory optimization",
                max_results=5,
            )

            # Assert candidates fetched with widen net (>= 30)
            mock_fetch.assert_awaited_once()
            called_pool = mock_fetch.call_args[1]["max_candidates"]
            assert called_pool >= 30

            # Assert top N filtered papers returned
            assert len(results) == 5
            for r in results:
                assert "score" in r
                assert "raw_score" in r
                assert r["score"] > 0.0


@pytest.mark.asyncio
async def test_network_guard_enforcement() -> None:
    """Assertion: Network guard halts unauthorized external egress outside 127.0.0.1 and export.arxiv.org."""
    client = ArxivClient()

    # export.arxiv.org is permitted
    client._verify_host("https://export.arxiv.org/api/query?search_query=cat:cs.AI")
    client._verify_host("https://arxiv.org/pdf/2401.00001.pdf")
    client._verify_host("http://127.0.0.1:11434/api/generate")
    client._verify_host("http://localhost:6333/dashboard")

    # Unauthorized cloud endpoints trigger PermissionError
    with pytest.raises(PermissionError, match="NETWORK_GUARD_TRIGGER"):
        client._verify_host("https://api.openai.com/v1/chat/completions")

    with pytest.raises(PermissionError, match="NETWORK_GUARD_TRIGGER"):
        client._verify_host("https://cloud.qdrant.io/v1/collections")
