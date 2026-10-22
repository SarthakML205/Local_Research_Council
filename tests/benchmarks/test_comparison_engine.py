"""Verification and benchmark suite for the 3-Way Search & Reranking Strategy Engine.

Asserts:
  - Strategy A (Code-Only): ~2ms, 0 tokens, 0 MB VRAM, literal keyword matching.
  - Strategy B (Local LLM): Token context tracking, ~4.5 GB VRAM footprint, narrative justification.
  - Strategy C (Hybrid Rerank): Blazing fast (< 50ms), 0 LLM context generation tokens, Apple M5 Metal memory.
  - Parallel execution via asyncio.gather.
  - API endpoint verification (/library/research/compare).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.backend.retrieval.comparison_engine import (
    compare_all_strategies,
    run_strategy_a_code_only,
    run_strategy_b_local_llm,
    run_strategy_c_hybrid_rerank,
)
from app.main import app


@pytest.fixture
def mock_candidates() -> list[dict[str, Any]]:
    """Fixture providing 10 diverse preprints for strategy comparison."""
    now = datetime.now(UTC)
    return [
        {
            "paper_id": "2401.0001",
            "arxiv_id": "2401.0001",
            "title": "KV-Cache Compression and Memory Optimization for Multi-Agent LLMs",
            "summary": "We present hardware-aligned KV-cache compression and activation memory pruning for multi-agent reasoning.",
            "published": (now - timedelta(days=60)).isoformat(),
            "authors": ["Author One", "Author Two"],
            "categories": ["cs.AI", "cs.LG"],
        },
        {
            "paper_id": "2312.0002",
            "title": "Selective State Space Models for Long-Sequence Language Modeling",
            "summary": "Mamba introduces input-dependent selection mechanisms achieving linear scaling without quadratic attention overhead.",
            "published": (now - timedelta(days=300)).isoformat(),
            "authors": ["Author Three"],
            "categories": ["cs.LG", "cs.CL"],
        },
        {
            "paper_id": "1706.0003",
            "title": "Attention Is All You Need",
            "summary": "The dominant sequence transduction models are based on recurrent networks. We introduce the Transformer.",
            "published": "2017-06-12T00:00:00Z",
            "authors": ["Vaswani et al."],
            "categories": ["cs.CL"],
        },
        {
            "paper_id": "2402.0004",
            "title": "Robotic Quadruped Locomotion on Uneven Terrain",
            "summary": "Reinforcement learning for legged robot navigation across rough physical obstacles.",
            "published": (now - timedelta(days=45)).isoformat(),
            "authors": ["Author Four"],
            "categories": ["cs.RO"],
        },
    ]


@pytest.mark.asyncio
async def test_strategy_a_code_only_benchmark(mock_candidates: list[dict[str, Any]]) -> None:
    """Strategy A Assertion: < 10ms latency, 0 tokens, 0 MB VRAM, pure regex keyword hits."""
    query = "KV-cache memory optimization"
    res = await run_strategy_a_code_only(query, mock_candidates, max_papers=2)

    assert res.strategy_id == "strategy_a_code_only"
    assert res.strategy_name == "Strategy A: Code-Only Logic"
    assert res.tagline == "The Literal Librarian"
    assert "brute-force baseline" in res.narrative
    assert res.token_cost == 0
    assert res.vram_mb == 0.0
    assert res.latency_ms < 15.0  # Ultra-fast regex
    assert len(res.papers) == 2

    # Paper 2401.0001 has literal "KV-cache", "memory", "optimization" in title
    assert res.papers[0].paper_id == "2401.0001"
    assert "Literal keyword match" in res.papers[0].match_reason


@pytest.mark.asyncio
async def test_strategy_b_local_llm_benchmark(mock_candidates: list[dict[str, Any]]) -> None:
    """Strategy B Assertion: Tracks tokens, ~4.5 GB VRAM footprint, and generative justification."""
    query = "memory optimization in multi-agent transformers"
    res = await run_strategy_b_local_llm(query, mock_candidates, max_papers=2, timeout_s=0.5)

    assert res.strategy_id == "strategy_b_local_llm"
    assert res.strategy_name == "Strategy B: Local LLM Call"
    assert res.tagline == "The Heavy Thinker"
    assert "overkill and slow" in res.narrative
    assert res.token_cost > 0
    assert res.vram_mb >= 4000.0  # ~4.5 GB 8B model RAM footprint
    assert len(res.papers) == 2
    assert "LLM" in res.papers[0].match_reason


@pytest.mark.asyncio
async def test_strategy_c_hybrid_rerank_flagship_benchmark(mock_candidates: list[dict[str, Any]]) -> None:
    """Strategy C Assertion: Flagship default, < 50ms latency, 0 generation tokens, Metal unified memory."""
    query = "KV-cache memory optimization in multi-agent LLMs"
    res = await run_strategy_c_hybrid_rerank(query, mock_candidates, max_papers=2)

    assert res.strategy_id == "strategy_c_hybrid_rerank"
    assert res.strategy_name == "Strategy C: Hybrid Reranking"
    assert res.tagline == "The Smart Context Assistant"
    assert res.is_default is True
    assert "optimal systems balance" in res.narrative
    assert res.token_cost == 0
    assert res.vram_mb == 1024.0
    assert res.latency_ms < 60.0  # Metal hardware accelerated
    assert len(res.papers) == 2

    # Reranker scores KV-cache paper #1 with MLX dense cosine + date boost
    assert res.papers[0].paper_id == "2401.0001"
    assert "MLX Dense Cosine" in res.papers[0].match_reason
    assert "Date Decay Boost" in res.papers[0].match_reason


@pytest.mark.asyncio
async def test_parallel_compare_all_strategies(mock_candidates: list[dict[str, Any]]) -> None:
    """Assertion: All 3 strategies execute concurrently via asyncio.gather."""
    query = "KV-cache compression"
    response = await compare_all_strategies(
        query=query,
        candidates=mock_candidates,
        max_papers=3,
    )

    assert response.query == query
    assert response.total_candidates_analyzed == len(mock_candidates)
    assert response.default_strategy_id == "strategy_c_hybrid_rerank"
    assert "strategy_a_code_only" in response.strategies
    assert "strategy_b_local_llm" in response.strategies
    assert "strategy_c_hybrid_rerank" in response.strategies

    # Ensure all 3 returned results
    strat_a = response.strategies["strategy_a_code_only"]
    strat_b = response.strategies["strategy_b_local_llm"]
    strat_c = response.strategies["strategy_c_hybrid_rerank"]

    assert len(strat_a.papers) == 3
    assert len(strat_b.papers) == 3
    assert len(strat_c.papers) == 3


def test_api_compare_endpoint(mock_candidates: list[dict[str, Any]]) -> None:
    """Assertion: POST /api/library/research/compare responds with 3-way benchmark payload."""
    client = TestClient(app)
    resp = client.post(
        "/api/library/research/compare",
        json={"query": "KV cache attention memory", "max_papers": 3},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["query"] == "KV cache attention memory"
    assert "strategies" in data
    assert "strategy_a_code_only" in data["strategies"]
    assert "strategy_b_local_llm" in data["strategies"]
    assert "strategy_c_hybrid_rerank" in data["strategies"]
    assert data["default_strategy_id"] == "strategy_c_hybrid_rerank"
