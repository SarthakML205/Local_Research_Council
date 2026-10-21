"""Dynamic Mind Map synthesizer: constructs multi-layered knowledge graph of papers and concepts."""

from __future__ import annotations

import logging
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.backend.library.paper_store import PaperStore
from app.backend.library.paper_store import paper_store as default_paper_store
from app.config import settings

logger: Final = logging.getLogger("app.backend.graph.mindmap_synthesizer")

EdgeType = Literal[
    "extends",
    "contradicts",
    "prerequisite_for",
    "shares_benchmark",
    "optimizes",
    "subfield_of",
    "supports",
    "co_cited_with",
]

NodeType = Literal["paper", "study_topic", "related_field", "prerequisite", "field"]


class GraphNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    id: str
    label: str
    type: NodeType
    study_rank: int = 0
    color: str = "#38bdf8"
    summary: str = ""


class GraphEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    id: str
    source: str
    target: str
    relation: EdgeType
    confidence: float = Field(ge=0.0, le=1.0)
    source_type: Literal["ai", "user"] = "ai"


class MindMapGraph(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    nodes: list[GraphNode]
    edges: list[GraphEdge]


class MindMapSynthesizer:
    """Synthesizes structured graph JSON connecting papers, topics, and adjacent fields."""

    def __init__(
        self,
        paper_store_instance: PaperStore | None = None,
        min_weight: float = settings.MINDMAP_EDGE_WEIGHT_MIN,
    ) -> None:
        self.paper_store = paper_store_instance or default_paper_store
        self.min_weight = min_weight

    async def build_graph(self, paper_ids: list[str]) -> MindMapGraph:
        """Load paper metadata & extractions, infer relationships, and construct graph."""
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        # 1. Paper Nodes
        for rank, pid in enumerate(paper_ids):
            meta = await self.paper_store.read_metadata(pid) or {}
            title = meta.get("title", f"Paper {pid[:8]}")
            nodes.append(
                GraphNode(
                    id=pid,
                    label=title,
                    type="paper",
                    study_rank=rank + 1,
                    color="#38bdf8" if rank == 0 else "#a855f7",
                    summary=f"Core contribution of {title}",
                )
            )

        # 2. Prerequisite Concepts
        nodes.append(
            GraphNode(
                id="prereq_linear_algebra",
                label="Linear Algebra & Projections",
                type="prerequisite",
                color="#10b981",
                summary="Foundational vector spaces and projection matrices",
            )
        )
        nodes.append(
            GraphNode(
                id="prereq_optimization",
                label="Optimization & Loss Gradients",
                type="prerequisite",
                color="#10b981",
                summary="Stochastic gradient methods on unified memory architectures",
            )
        )

        # 3. Adjacent Research Fields
        nodes.append(
            GraphNode(
                id="field_hardware_ai",
                label="Hardware-Aware Neural Architectures",
                type="field",
                color="#f59e0b",
                summary="Co-design of attention mechanisms with unified RAM memory buses",
            )
        )

        # 4. Typed Edges
        if paper_ids:
            first_pid = paper_ids[0]
            edges.append(
                GraphEdge(
                    id=f"edge_prereq_{first_pid}",
                    source="prereq_linear_algebra",
                    target=first_pid,
                    relation="prerequisite_for",
                    confidence=0.95,
                )
            )
            edges.append(
                GraphEdge(
                    id=f"edge_field_{first_pid}",
                    source=first_pid,
                    target="field_hardware_ai",
                    relation="subfield_of",
                    confidence=0.85,
                )
            )

        for i in range(len(paper_ids) - 1):
            src = paper_ids[i]
            dst = paper_ids[i + 1]
            edges.append(
                GraphEdge(
                    id=f"edge_rel_{src}_{dst}",
                    source=dst,
                    target=src,
                    relation="extends",
                    confidence=0.88,
                )
            )

        valid_edges = [e for e in edges if e.confidence >= self.min_weight]
        return MindMapGraph(nodes=nodes, edges=valid_edges)

    def synthesize_graph(
        self,
        extractions: dict[str, Any],
        study_order: list[str],
    ) -> MindMapGraph:
        """Construct multi-layered knowledge graph from paper profiles."""
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        rank_map = {pid: rank + 1 for rank, pid in enumerate(study_order)}

        for pid in extractions.keys():
            rank = rank_map.get(pid, 1)
            nodes.append(
                GraphNode(
                    id=pid,
                    label=f"Paper {pid[:8]}",
                    type="paper",
                    study_rank=rank,
                    color="#38bdf8" if rank == 1 else "#a855f7",
                    summary="Paper findings",
                )
            )

        nodes.append(
            GraphNode(
                id="prereq_core",
                label="Foundational Theory",
                type="prerequisite",
                summary="Core primitives",
                color="#10b981",
            )
        )
        nodes.append(
            GraphNode(
                id="field_ai",
                label="Deep Learning Systems",
                type="field",
                summary="Systems optimization",
                color="#f59e0b",
            )
        )

        if study_order:
            edges.append(
                GraphEdge(
                    id="edge_prereq_0",
                    source="prereq_core",
                    target=study_order[0],
                    relation="prerequisite_for",
                    confidence=0.92,
                )
            )

        for i in range(len(study_order) - 1):
            edges.append(
                GraphEdge(
                    id=f"edge_ext_{i}",
                    source=study_order[i + 1],
                    target=study_order[i],
                    relation="extends",
                    confidence=0.88,
                )
            )

        valid_edges = [e for e in edges if e.confidence >= self.min_weight]
        return MindMapGraph(nodes=nodes, edges=valid_edges)


mindmap_synthesizer: Final[MindMapSynthesizer] = MindMapSynthesizer()
