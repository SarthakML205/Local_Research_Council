"""Tests for Dynamic Multi-Agent Academic Debate Flow and Tony Stark AI Personas.

Verifies:
1. Stark AI Persona assignment (J.A.R.V.I.S., F.R.I.D.A.Y., E.D.I.T.H., etc.) and star constellation emblems.
2. Formal academic debate prompts and citation grounding directives.
3. State-aware FSM execution: Opening Statements -> Dynamic Clashes -> Rebuttal Chains -> Final Synthesis.
4. Token budget ceiling invariant (<= 2,048 tokens).
"""

from __future__ import annotations

import pytest

from app.backend.agents.agent_factory import (
    STARK_ADVOCATE_PERSONAS,
    agent_factory,
)
from app.backend.agents.turn_manager import (
    TurnManager,
)
from app.backend.extraction.schemas import PaperExtractionSchema


@pytest.mark.asyncio
async def test_stark_persona_and_star_symbols() -> None:
    """Verify Stark AI persona assignment and constellation star emblems."""
    mod = agent_factory.create_moderator(debate_prompt="Compare architectures.")
    assert mod.stark_name == "J.A.R.V.I.S."
    assert mod.avatar_symbol == "❂"
    assert mod.color == "#fbbf24"
    assert "Grand Synthesizer" in mod.stark_title

    # Test advocates cycling through Stark personas
    advocates = [
        await agent_factory.create_advocate(
            paper_id=f"paper_{i}",
            slot_index=i,
            extraction=PaperExtractionSchema(
                tldr=f"Core contribution of paper {i}",
                problem_statement=f"Addressing bottleneck {i}",
                methodology=f"Novel recurrent kernel {i}",
                key_results=["Zero cache paging", "Linear memory"],
                why_it_matters="Scales sub-quadratically",
                audience="Systems Researchers",
                original_abstract="Abstract text",
                research_gaps_identified=[f"Theoretical bounds {i}"],
                ai_suggested_gaps=["Unified memory paging overhead"],
            ),
        )
        for i in range(4)
    ]

    expected_names = ["F.R.I.D.A.Y.", "E.D.I.T.H.", "K.A.R.E.N.", "J.O.C.A.S.T.A."]
    expected_symbols = ["✦", "★", "✧", "✪"]

    for i, adv in enumerate(advocates):
        assert adv.stark_name == expected_names[i]
        assert adv.avatar_symbol == expected_symbols[i]
        assert adv.color == STARK_ADVOCATE_PERSONAS[i]["color"]
        assert "defending the research paper" in adv.system_persona.lower()
        assert "formal academic" in adv.system_persona.lower()
        assert "never use raw unformatted bullet points" in adv.system_persona.lower()


@pytest.mark.asyncio
async def test_dynamic_debate_fsm_with_rebuttal_chain() -> None:
    """Verify state-aware debate execution: opening, clashes, rebuttal chains, and synthesis."""
    tm = TurnManager()
    session = await tm.create_session(
        debate_id="test_deb_stark_01",
        paper_ids=["2405.21060", "2312.00752"],
        prompt="Compare state space vs quadratic attention memory overhead on Apple Silicon.",
        rounds=1,
    )

    assert len(session.advocates) == 2
    assert session.advocates[0].stark_name == "F.R.I.D.A.Y."
    assert session.advocates[1].stark_name == "E.D.I.T.H."
    assert session.moderator.stark_name == "J.A.R.V.I.S."

    turns = []
    while True:
        turn = await tm.step(session.debate_id)
        if not turn:
            break
        turns.append(turn)

    # 1. Opening round: both advocates state opening theses
    assert len(turns) >= 3  # 2 openings + at least 1 clash + synthesis
    assert turns[0].turn_type == "opening"
    assert turns[0].speaker_name == "F.R.I.D.A.Y."
    assert turns[0].avatar_symbol == "✦"
    assert turns[0].total_tokens <= 2048

    assert turns[1].turn_type == "opening"
    assert turns[1].speaker_name == "E.D.I.T.H."
    assert turns[1].avatar_symbol == "★"
    assert turns[1].total_tokens <= 2048

    # 2. Dynamic clash / rebuttal turns
    clash_turns = [t for t in turns if t.turn_type in ("clash", "rebuttal")]
    assert len(clash_turns) >= 1
    for ct in clash_turns:
        assert ct.target_paper_id is not None
        assert ct.target_name is not None
        assert ct.total_tokens <= 2048

    # 3. Final turn is J.A.R.V.I.S. final synthesis
    last_turn = turns[-1]
    assert last_turn.turn_type in ("synthesis", "final_synthesis")
    assert last_turn.speaker_name == "J.A.R.V.I.S."
    assert last_turn.avatar_symbol == "❂"
    assert "Grand Synthesizer" in last_turn.speaker_title
    assert last_turn.total_tokens <= 2048
