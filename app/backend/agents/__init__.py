"""Paper council agents: dynamic spawning, history compression, and turn management."""

from app.backend.agents.agent_factory import CouncilAgent, agent_factory
from app.backend.agents.compression import PositionCard, history_compressor
from app.backend.agents.turn_manager import DebateSession, DebateTurnRecord, turn_manager

__all__ = [
    "CouncilAgent",
    "agent_factory",
    "PositionCard",
    "history_compressor",
    "DebateTurnRecord",
    "DebateSession",
    "turn_manager",
]
