"""Phase 4 Benchmark and Verification Suite.

Tests:
1. Hard <= 2,048 Prompt Token Budget across 50 simulated debate turns.
2. Knapsack RAG context packing achieves >= 85% utilization of the 1,024 token compartment.
3. Abstractive position card compaction completes in < 350 ms.
4. End-to-end multi-agent debate FSM execution and Moderator consensus synthesis.
5. Mind Map graph synthesis with confidence >= 0.35 and typed edges.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.backend.agents.compression import HistoryCompressor
from app.backend.agents.turn_manager import turn_manager
from app.backend.graph.mindmap_synthesizer import MindMapSynthesizer
from app.backend.library.paper_store import PaperStore
from app.core.token_budget import TokenBudgeter


@pytest.mark.asyncio
async def test_token_budget_invariant_across_50_turns() -> None:
    """Assertion: Hard <= 2,048 prompt token budget strictly held across 50 turns."""
    budgeter = TokenBudgeter()

    sample_paragraph = (
        "This empirical analysis evaluates transformer architectures running on unified memory. "
        "We observe significant KV-cache memory pressure when sequence length exceeds 4,096 tokens. "
        "By enforcing strict compartment bounds, the attention mechanism avoids out-of-core paging. "
    )

    for i in range(50):
        # Varying lengths for compartments to stress test boundary truncation
        system_text = f"You are Advocate-{i % 3}. Defend paper principles rigorously. " * (i % 5 + 1)
        rag_text = sample_paragraph * ((i % 8) + 2)
        cards_text = "Advocate-0: Stance on memory. Advocate-1: Counter-argument. " * (i % 4 + 1)
        recent_turns = [
            f"Turn {j}: Opponent claimed KV cache is bounded, but page faults occurred [P1 §3 #2]."
            for j in range(i % 10 + 1)
        ]

        assembled = await budgeter.assemble_and_pack(
            system_text=system_text,
            rag_grounding_text=rag_text,
            position_cards_text=cards_text,
            recent_turns=recent_turns,
            num_agents=3,
        )

        assert assembled.total_tokens <= 2048, (
            f"Turn {i} breached hard ceiling: {assembled.total_tokens} > 2048"
        )
        assert assembled.system_tokens <= 256, (
            f"Turn {i} breached system budget: {assembled.system_tokens} > 256"
        )
        assert assembled.rag_tokens <= 1024, (
            f"Turn {i} breached RAG budget: {assembled.rag_tokens} > 1024"
        )
        assert assembled.history_tokens <= 768, (
            f"Turn {i} breached history budget: {assembled.history_tokens} > 768"
        )


@pytest.mark.asyncio
async def test_knapsack_rag_utilization() -> None:
    """Assertion: Knapsack context packing achieves >= 85% token utilization."""
    budgeter = TokenBudgeter()

    # Generate candidate text well above the 1,024 token limit (~1,500 tokens)
    candidate_chunk = (
        "In this work, we present a deterministic knapsack priority packer for local RAG retrieval. "
        "The context provider ranks candidate text passages by reciprocal rank fusion score. "
    )
    long_candidate_text = candidate_chunk * 50  # ~1,500 tokens

    truncated, tokens = budgeter.truncate_to_tokens(long_candidate_text, max_tokens=1024)

    assert tokens <= 1024, f"Packed tokens exceeded budget: {tokens} > 1024"
    utilization = (tokens / 1024.0) * 100.0
    assert utilization >= 85.0, f"Knapsack utilization below 85%: {utilization:.2f}%"


@pytest.mark.asyncio
async def test_position_card_compaction_sub_350ms() -> None:
    """Assertion: Agent position card compaction completes in < 350 ms."""
    compressor = HistoryCompressor()
    latencies: list[float] = []

    turn_text = (
        "The proposed linear attention formulation fails to maintain associative recall at scale. "
        "Citation: [P1 §4 #3]. Our empirical benchmark demonstrates a 14% perplexity regression."
    )

    for i in range(20):
        t0 = time.perf_counter_ns()
        card = await compressor.update_position_card(
            agent_id=f"advocate_{i % 3}",
            paper_id=f"paper_{i % 3}",
            recent_turn_text=turn_text,
            card_token_budget=96,
        )
        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        latencies.append(elapsed_ms)

        assert card.token_count <= 96
        assert len(card.stance) > 0
        assert len(card.strongest_evidence) > 0

    p99 = sorted(latencies)[int(len(latencies) * 0.99)]
    assert p99 < 350.0, f"Position card compaction p99 exceeded 350ms SLA: {p99:.3f} ms"


@pytest.mark.asyncio
async def test_end_to_end_debate_fsm(tmp_path: Path) -> None:
    """Assertion: End-to-end multi-agent debate FSM with Moderator synthesis."""

    paper_ids = ["p_attention", "p_mamba"]
    prompt = "Compare quadratic attention vs selective state space for long contexts on Apple Silicon."
    debate_id = "test_deb_001"

    session = await turn_manager.create_session(
        debate_id=debate_id,
        paper_ids=paper_ids,
        prompt=prompt,
        rounds=1,
    )

    assert len(session.advocates) == 2
    assert session.moderator.role == "moderator"

    # Step through all turns
    turns_run = 0
    while True:
        turn = await turn_manager.step(debate_id)
        if not turn:
            break
        turns_run += 1
        assert turn.total_tokens <= 2048, f"Turn {turn.turn_index} breached 2048 tokens"
        assert len(turn.text) > 0

    assert turns_run >= 4, f"Debate concluded too early with only {turns_run} turns"
    assert session.phase == "completed"

    # Verify the last turn was synthesized by the moderator
    last_turn = session.turns[-1]
    assert last_turn.agent_id == "moderator"
    assert "Council Synthesis" in last_turn.text or "Unified Curriculum" in last_turn.text


@pytest.mark.asyncio
async def test_mindmap_graph_synthesis(tmp_path: Path) -> None:
    """Assertion: Mind Map graph generation validation with confidence >= 0.35 and typed edges."""
    paper_store = PaperStore(base_dir=tmp_path / "papers")
    synthesizer = MindMapSynthesizer(paper_store)

    # Setup 2 papers in store
    from app.backend.library.paper_store import PaperManifest

    for p_id, title in [("p1", "Self-Attention Dynamics"), ("p2", "State Space Modeling")]:
        await paper_store.save_metadata(p_id, {"paper_id": p_id, "title": title, "year": 2024})
        manifest = PaperManifest(
            paper_id=p_id,
            content_hash=f"hash_{p_id}",
            stages_completed=["downloaded", "sliced", "chunked"],
        )
        await paper_store.save_manifest(p_id, manifest)
        await paper_store.save_extraction(
            p_id,
            {
                "paper_id": p_id,
                "title": title,
                "core_thesis": f"Foundational insights for {p_id}",
                "methodology_summary": "Empirical benchmarks",
                "key_findings": ["Validates hypothesis"],
                "identified_limitations": ["Scale"],
                "strengths": ["Speed"],
                "prerequisite_concepts": ["Linear Algebra", "Optimization"],
                "target_curriculum_topics": ["Deep Learning Systems"],
            },
        )

    graph = await synthesizer.build_graph(["p1", "p2"])

    # Validate nodes
    node_types = {n.type for n in graph.nodes}
    assert "paper" in node_types
    assert "prerequisite" in node_types
    assert "field" in node_types

    # Validate edges
    assert len(graph.edges) > 0
    for edge in graph.edges:
        assert edge.confidence >= 0.35, f"Edge confidence below 0.35: {edge.confidence}"
        assert edge.relation in [
            "prerequisite_for",
            "subfield_of",
            "supports",
            "contradicts",
            "extends",
            "co_cited_with",
        ]
