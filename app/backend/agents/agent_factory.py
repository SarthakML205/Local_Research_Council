"""Dynamic agent spawning: generates virtual advocate personas and moderator.

Humanized Stark AI Personas (J.A.R.V.I.S., F.R.I.D.A.Y., E.D.I.T.H., etc.)
with star constellation symbols and rigorous academic debate constraints.
"""

import logging

from pydantic import BaseModel, ConfigDict

from app.backend.extraction.schemas import PaperExtractionSchema
from app.backend.library.paper_store import paper_store
from app.backend.retrieval.partition_manager import partition_manager
from app.backend.telemetry.collector import telemetry_collector
from app.backend.telemetry.events import BaseTelemetryRecord

logger = logging.getLogger("app.backend.agents.agent_factory")

STARK_ADVOCATE_PERSONAS: list[dict[str, str]] = [
    {
        "stark_name": "F.R.I.D.A.Y.",
        "codename": "Friday",
        "title": "Lead Architecture Advocate",
        "avatar_symbol": "✦",
        "color": "#38bdf8",
        "glow": "rgba(56, 189, 248, 0.4)",
    },
    {
        "stark_name": "E.D.I.T.H.",
        "codename": "Edith",
        "title": "Empirical Benchmark Advocate",
        "avatar_symbol": "★",
        "color": "#10b981",
        "glow": "rgba(16, 185, 129, 0.4)",
    },
    {
        "stark_name": "K.A.R.E.N.",
        "codename": "Karen",
        "title": "Theoretical Systems Advocate",
        "avatar_symbol": "✧",
        "color": "#a855f7",
        "glow": "rgba(168, 85, 247, 0.4)",
    },
    {
        "stark_name": "J.O.C.A.S.T.A.",
        "codename": "Jocasta",
        "title": "Algorithmic Precision Advocate",
        "avatar_symbol": "✪",
        "color": "#f59e0b",
        "glow": "rgba(245, 158, 11, 0.4)",
    },
    {
        "stark_name": "V.E.R.O.N.I.C.A.",
        "codename": "Veronica",
        "title": "Hardware Saturation Advocate",
        "avatar_symbol": "✷",
        "color": "#f43f5e",
        "glow": "rgba(244, 63, 94, 0.4)",
    },
    {
        "stark_name": "T.A.D.A.S.H.I.",
        "codename": "Tadashi",
        "title": "Low-Latency Kernel Advocate",
        "avatar_symbol": "✹",
        "color": "#06b6d4",
        "glow": "rgba(6, 182, 212, 0.4)",
    },
]

MODERATOR_STARK_PERSONA: dict[str, str] = {
    "stark_name": "J.A.R.V.I.S.",
    "codename": "Jarvis",
    "title": "Council Moderator & Grand Synthesizer",
    "avatar_symbol": "❂",
    "color": "#fbbf24",
    "glow": "rgba(251, 191, 36, 0.45)",
}


class CouncilAgent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    agent_id: str
    paper_id: str
    role: str  # advocate | moderator
    display_name: str
    stark_name: str = "F.R.I.D.A.Y."
    stark_title: str = "Lead Defense Advocate"
    avatar_symbol: str = "✦"
    color: str = "#38bdf8"
    glow: str = "rgba(56, 189, 248, 0.4)"
    system_persona: str
    persona_tokens: int
    paper_title: str = ""
    assigned_slot: int = 0


class AgentFactory:
    """Spawns virtual advocate agents from extracted paper schemas with Stark AI personas."""

    def __init__(self) -> None:
        pass

    async def create_advocate(
        self,
        paper_id: str,
        slot_index: int,
        extraction: PaperExtractionSchema | None = None,
    ) -> CouncilAgent:
        """Create a dedicated virtual advocate with a distinct Tony Stark AI persona."""
        agent_id = f"advocate:{paper_id}"

        # Bind retrieval partition handle
        partition_manager.create_handle(agent_id=agent_id, paper_id=paper_id)

        meta = await paper_store.read_metadata(paper_id) or {}
        title = meta.get("title", paper_id)

        persona_template = STARK_ADVOCATE_PERSONAS[slot_index % len(STARK_ADVOCATE_PERSONAS)]
        stark_name = persona_template["stark_name"]
        avatar_symbol = persona_template["avatar_symbol"]
        color = persona_template["color"]
        glow = persona_template["glow"]
        stark_title = f"{persona_template['title']} for {title[:40]}"

        # Academic persona prompt enforcing humanized reactive debate
        methodology = extraction.methodology[:200] if extraction else "Empirical architectural proofs"
        problem = extraction.problem_statement[:150] if extraction else "Foundational scaling bounds"
        gaps = (
            ", ".join(extraction.research_gaps_identified[:2])
            if extraction and extraction.research_gaps_identified
            else "Hardware-specific cache paging"
        )

        persona = (
            f"You are {stark_name}, defending the research paper: '{title}'.\n"
            f"Core Problem: {problem}\n"
            f"Your Methodology: {methodology}\n"
            f"Known Limitations: {gaps}\n\n"
            "CRITICAL DEBATE RULES:\n"
            "1. WRITING STYLE: Write in professional, formal academic prose (paragraphs). "
            "NEVER use raw unformatted bullet points or conversational AI filler ('Sure, I can help with that!').\n"
            "2. REACTIVE DEBATE: You are speaking to peer researchers who hold opposing views. Maintain a formal, "
            "academic, yet combative tone. When responding, you must directly address the previous speaker's claims:\n"
            "   - 'While [Opponent] contends that..., their methodology fails to account for...'\n"
            "   - 'Our empirical findings directly challenge [Opponent]'s baseline because...'\n"
            f"3. GROUNDING: Back your arguments strictly using isolated evidence tags [P{slot_index + 1} §Section #Chunk]. "
            "Expose logical or architectural flaws in opposing papers."
        )

        tokens = max(1, len(persona.split()))

        agent = CouncilAgent(
            agent_id=agent_id,
            paper_id=paper_id,
            role="advocate",
            display_name=f"{stark_name} • {title[:32]}...",
            stark_name=stark_name,
            stark_title=stark_title,
            avatar_symbol=avatar_symbol,
            color=color,
            glow=glow,
            system_persona=persona,
            persona_tokens=tokens,
            paper_title=title,
            assigned_slot=slot_index + 1,
        )

        telemetry_collector.emit_nowait(
            BaseTelemetryRecord(
                component="agent_factory",
                session_id=agent_id,
            )
        )
        return agent

    def create_moderator(self, debate_prompt: str = "") -> CouncilAgent:
        """Create the debate moderator J.A.R.V.I.S."""
        persona = (
            "You are J.A.R.V.I.S., Council Moderator and Grand Research Synthesizer.\n"
            "Your duties:\n"
            "1. Steer the council trajectory constructively; intervene if advocates talk past each other or loop.\n"
            "2. Challenge advocates on hardware saturation limits, empirical validity, and unified memory bounds.\n"
            "3. Synthesize an objective final comparative trade-off matrix exposing the architectural Pareto frontier.\n"
            f"Research Inquiry: {debate_prompt or 'Compare architectural trade-offs and scaling bounds.'}"
        )
        tokens = max(1, len(persona.split()))

        return CouncilAgent(
            agent_id="moderator",
            paper_id="",
            role="moderator",
            display_name="J.A.R.V.I.S. • Council Moderator",
            stark_name=MODERATOR_STARK_PERSONA["stark_name"],
            stark_title=MODERATOR_STARK_PERSONA["title"],
            avatar_symbol=MODERATOR_STARK_PERSONA["avatar_symbol"],
            color=MODERATOR_STARK_PERSONA["color"],
            glow=MODERATOR_STARK_PERSONA["glow"],
            system_persona=persona,
            persona_tokens=tokens,
            paper_title="Council Steering Dais",
            assigned_slot=0,
        )


agent_factory = AgentFactory()
