"""Dynamic agent spawning: generates virtual advocate personas and moderator."""

import logging

from pydantic import BaseModel, ConfigDict

from app.backend.extraction.schemas import PaperExtractionSchema
from app.backend.library.paper_store import paper_store
from app.backend.retrieval.partition_manager import partition_manager
from app.backend.telemetry.collector import telemetry_collector
from app.backend.telemetry.events import BaseTelemetryRecord

logger = logging.getLogger("app.backend.agents.agent_factory")

COLOR_PALETTE = [
    "#38bdf8",  # Sky Blue
    "#f43f5e",  # Rose Red
    "#10b981",  # Emerald Green
    "#a855f7",  # Violet Purple
    "#f59e0b",  # Amber Yellow
    "#06b6d4",  # Cyan
    "#ec4899",  # Pink
    "#84cc16",  # Lime
]


class CouncilAgent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    agent_id: str
    paper_id: str
    role: str  # advocate | moderator
    display_name: str
    color: str
    system_persona: str
    persona_tokens: int


class AgentFactory:
    """Spawns virtual advocate agents from extracted paper schemas without loading extra LLM instances."""

    def __init__(self) -> None:
        pass

    async def create_advocate(
        self,
        paper_id: str,
        slot_index: int,
        extraction: PaperExtractionSchema | None = None,
    ) -> CouncilAgent:
        """Create a dedicated virtual advocate for a selected research paper."""
        agent_id = f"advocate:{paper_id}"

        # Bind retrieval partition handle
        partition_manager.create_handle(agent_id=agent_id, paper_id=paper_id)

        meta = await paper_store.read_metadata(paper_id) or {}
        title = meta.get("title", paper_id)
        short_name = f"Paper #{slot_index + 1} ({paper_id[:8]})"
        color = COLOR_PALETTE[slot_index % len(COLOR_PALETTE)]

        if extraction:
            persona = (
                f"You are the Lead Author and Principal Advocate for {short_name}.\n"
                f"Paper Title: {title}\n"
                f"Core Methodology: {extraction.methodology[:200]}\n"
                f"Key Empirical Results: {', '.join(extraction.key_results[:2])}\n"
                f"Admitted Gaps: {', '.join(extraction.research_gaps_identified[:1])}\n"
                f"Rules: Defend your architecture with rigor using strictly cited evidence [P{slot_index + 1} §Section #Chunk]. "
                f"Critique opponents' scaling and methodological assumptions constructively."
            )
        else:
            persona = (
                f"You are the Lead Author and Advocate for {short_name}: '{title}'.\n"
                f"Defend your methodology with citations and analyze trade-offs in competing approaches."
            )

        tokens = max(1, len(persona.split()))

        agent = CouncilAgent(
            agent_id=agent_id,
            paper_id=paper_id,
            role="advocate",
            display_name=short_name,
            color=color,
            system_persona=persona,
            persona_tokens=tokens,
        )

        telemetry_collector.emit_nowait(
            BaseTelemetryRecord(
                component="agent_factory",
                session_id=agent_id,
            )
        )
        return agent

    def create_moderator(self, debate_prompt: str = "") -> CouncilAgent:
        """Create the debate moderator / guiding agent."""
        persona = (
            "You are the Council Moderator and Principal Research Director.\n"
            "Your duties:\n"
            "1. Steer the debate trajectory constructively; intervene if agents hallucinate or loop.\n"
            "2. Challenge advocates on edge cases, hardware bounds, and theoretical scaling limits.\n"
            "3. Synthesize an objective final comparative trade-off matrix and hybrid research roadmap.\n"
            f"User Research Query: {debate_prompt or 'Compare architectural trade-offs and scaling bounds.'}"
        )
        tokens = max(1, len(persona.split()))

        return CouncilAgent(
            agent_id="moderator",
            paper_id="",
            role="moderator",
            display_name="Council Moderator",
            color="#e2e8f0",
            system_persona=persona,
            persona_tokens=tokens,
        )


agent_factory = AgentFactory()
