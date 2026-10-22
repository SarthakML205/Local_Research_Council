"""LRC Multi-Agent Debate & Mind Map API Routes.

Exposes endpoints to launch debates, step through debate turns, stream
agent turns, inspect position cards, and synthesize knowledge mind maps.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Final

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.stream import broadcaster
from app.backend.agents.turn_manager import turn_manager
from app.backend.graph.mindmap_synthesizer import MindMapSynthesizer
from app.backend.library.council_launcher import CouncilLauncher
from app.backend.library.library_store import LibraryStore
from app.backend.library.paper_store import PaperStore

logger: Final = logging.getLogger(__name__)

router: Final[APIRouter] = APIRouter(prefix="/debate", tags=["Debate"])

paper_store: Final[PaperStore] = PaperStore()
library_store: Final[LibraryStore] = LibraryStore()
council_launcher: Final[CouncilLauncher] = CouncilLauncher(paper_store, library_store)
mindmap_synthesizer: Final[MindMapSynthesizer] = MindMapSynthesizer(paper_store)

# Staged paper list by debate_id
debate_papers: dict[str, list[str]] = {}


class DebateLaunchRequest(BaseModel):
    paper_ids: list[str] | None = Field(
        default=None,
        description="Paper IDs to convene. If None, uses active Council Tray.",
    )
    user_query: str = Field(
        default="Synthesize findings, identify tensions, and build a unified curriculum.",
        description="Core research question or agenda for the council debate.",
    )
    max_rounds: int = Field(default=2, ge=1, le=10)


@router.post("/launch")
async def launch_debate(req: DebateLaunchRequest) -> dict[str, Any]:
    """Validate paper bounds (2-6), initialize virtual advocates, and stage debate FSM."""
    target_papers = req.paper_ids
    if not target_papers:
        tray = await library_store.get_council_tray()
        target_papers = list(tray.get("paper_ids", []))

    try:
        council_manifest = await council_launcher.stage_debate(
            paper_ids=target_papers,
            user_agenda=req.user_query,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    debate_id = f"deb_{uuid.uuid4().hex[:8]}"

    session = await turn_manager.create_session(
        debate_id=debate_id,
        paper_ids=target_papers,
        prompt=req.user_query,
        rounds=req.max_rounds,
    )
    debate_papers[debate_id] = target_papers

    # Broadcast debate launch event
    await broadcaster.publish(
        "debate_launched",
        {
            "debate_id": debate_id,
            "paper_ids": target_papers,
            "advocate_count": len(session.advocates),
            "user_query": req.user_query,
            "status": "ready",
        },
    )

    return {
        "status": "staged",
        "debate_id": debate_id,
        "paper_ids": target_papers,
        "advocate_count": len(session.advocates),
        "advocates": [a.model_dump() for a in session.advocates],
        "moderator": session.moderator.model_dump(),
        "council_manifest": council_manifest,
    }


@router.post("/{debate_id}/step")
async def step_debate(debate_id: str) -> dict[str, Any]:
    """Advance the debate by exactly one speaker turn."""
    session = turn_manager.get_session(debate_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debate '{debate_id}' not found",
        )

    turn = await turn_manager.step(debate_id)
    if not turn:
        return {
            "status": "completed",
            "debate_id": debate_id,
            "current_phase": session.phase,
            "turn": None,
        }

    turn_data = turn.model_dump()

    # Broadcast turn event to SSE subscribers
    await broadcaster.publish("debate_turn", {"debate_id": debate_id, "turn": turn_data})

    return {
        "status": "in_progress" if session.phase != "completed" else "completed",
        "debate_id": debate_id,
        "current_phase": session.phase,
        "turn": turn_data,
        "budget_telemetry": {
            "prompt_tokens": turn.prompt_tokens,
            "within_sla": turn.prompt_tokens <= 2048,
        },
    }


@router.post("/{debate_id}/run")
async def run_debate(debate_id: str) -> dict[str, Any]:
    """Execute debate turns asynchronously until completion."""
    session = turn_manager.get_session(debate_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debate '{debate_id}' not found",
        )

    turns_executed: list[dict[str, Any]] = []
    while True:
        turn = await turn_manager.step(debate_id)
        if not turn:
            break

        turn_dict = turn.model_dump()
        turns_executed.append(turn_dict)
        await broadcaster.publish("debate_turn", {"debate_id": debate_id, "turn": turn_dict})
        await asyncio.sleep(0.01)

    await broadcaster.publish(
        "debate_completed",
        {
            "debate_id": debate_id,
            "total_turns": len(turns_executed),
            "final_synthesis": turns_executed[-1]["text"] if turns_executed else "",
        },
    )

    return {
        "status": "completed",
        "debate_id": debate_id,
        "total_turns": len(turns_executed),
        "turns": turns_executed,
    }


@router.get("/{debate_id}/status")
async def get_debate_status(debate_id: str) -> dict[str, Any]:
    """Retrieve current debate state, turns, position cards, and token budget statistics."""
    session = turn_manager.get_session(debate_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debate '{debate_id}' not found",
        )

    position_cards: dict[str, str] = {
        agent_id: card.stance
        for agent_id, card in session.position_cards.items()
    }

    return {
        "debate_id": debate_id,
        "phase": session.phase,
        "round_index": session.current_round_index,
        "turns_count": len(session.turns),
        "position_cards": position_cards,
        "papers": debate_papers.get(debate_id, []),
    }


@router.get("/mindmap/active")
async def get_active_mindmap() -> dict[str, Any]:
    """Get synthesized mind map for currently active tray papers or library."""
    tray = await library_store.get_council_tray()
    papers = list(tray.get("paper_ids", []))
    if not papers:
        all_p = await library_store.get_papers()
        papers = [p["paper_id"] for p in all_p[:4]]
    if not papers:
        papers = ["p_attention", "p_mamba"]
    mindmap = await mindmap_synthesizer.build_graph(papers)
    return mindmap.model_dump()


@router.get("/{debate_id}/mindmap")
async def get_debate_mindmap(debate_id: str) -> dict[str, Any]:
    """Generate and return multi-layered mind map graph for debate papers or paper ID."""
    papers = debate_papers.get(debate_id)
    if not papers:
        # Check if debate_id is a single paper ID or comma-separated paper IDs
        manifest = await paper_store.get_manifest(debate_id)
        if manifest:
            tray = await library_store.get_council_tray()
            tray_ids = list(tray.get("paper_ids", []))
            papers = list(dict.fromkeys([debate_id] + tray_ids))
        elif debate_id in ("tray", "current", "active", "default"):
            tray = await library_store.get_council_tray()
            papers = list(tray.get("paper_ids", []))
        else:
            # Fallback to tray or library papers
            tray = await library_store.get_council_tray()
            papers = list(tray.get("paper_ids", []))
            if not papers:
                all_p = await library_store.get_papers()
                papers = [p["paper_id"] for p in all_p[:4]]

    if not papers:
        papers = ["p_attention", "p_mamba"]

    mindmap = await mindmap_synthesizer.build_graph(papers)
    return mindmap.model_dump()
