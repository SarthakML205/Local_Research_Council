"""Council Context Provider: serves packed, cited ContextBundles and verifies citations."""

import logging
import re
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.backend.retrieval.hybrid_search import hybrid_search
from app.backend.retrieval.partition_manager import partition_manager
from app.backend.telemetry.events import FailureCode, Severity
from app.backend.telemetry.failure_log import failure_logger
from app.config import settings

logger = logging.getLogger("app.backend.retrieval.context_provider")

CITATION_TAG_PATTERN = re.compile(r"\[(?:P\d+\s+)?§([^#\]]+)\s+#(\d+)\]")


class GroundingChunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    paper_id: str
    chunk_index: int
    section_title: str
    citation_tag: str
    score: float
    token_count: int
    text: str


class ContextBundle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    debate_id: str
    agent_id: str
    paper_id: str
    chunks: list[GroundingChunk]
    packed_tokens: int
    dropped_candidates_count: int
    grounding_prompt_text: str


class ContextProvider:
    """Sole context provider for the Council: retrieves, packs, cites, and audits grounding text."""

    def __init__(
        self,
        rag_budget: int = settings.RAG_TOKEN_BUDGET,
        search_pipeline: Any = None,
    ) -> None:
        self.rag_budget = rag_budget
        self.search_pipeline = search_pipeline or hybrid_search

    async def provide(
        self,
        debate_id: str,
        agent_id: str,
        paper_id: str,
        query_text: str,
        paper_num: int = 1,
        token_budget: int | None = None,
    ) -> ContextBundle:
        """Retrieve, rank, and knapsack-pack grounding chunks for a debating advocate."""
        budget = token_budget or self.rag_budget

        # 1. Resolve or verify partition handle
        if agent_id in partition_manager._assigned_handles:
            await partition_manager.verify_partition_access(agent_id, paper_id)
        handle = partition_manager.create_handle(agent_id, paper_id)

        # 2. Retrieve candidates with 1 retry on Qdrant failure
        candidates: list[dict[str, Any]] = []
        for attempt in (1, 2):
            try:
                candidates, _ = await self.search_pipeline.search(
                    handle=handle,
                    query=query_text,
                    limit=12,
                    debate_id=debate_id,
                    agent_id=agent_id,
                )
                break
            except Exception as exc:
                if attempt == 2:
                    await failure_logger.log_failure(
                        code=FailureCode.QDRANT_ERROR,
                        message=f"Qdrant outage during context provision for {agent_id}: {exc}",
                        debate_id=debate_id,
                        paper_id=paper_id,
                        severity=Severity.FATAL,
                        component="context_provider",
                    )
                    raise

        # 3. Knapsack priority-packing into the 1,024-token budget
        packed_chunks: list[GroundingChunk] = []
        total_tokens = 0
        dropped_count = 0

        for cand in candidates:
            cand_tokens = int(cand["token_count"])
            if total_tokens + cand_tokens <= budget:
                chunk_idx = int(cand["chunk_index"])
                sec_title = str(cand["section_title"])
                tag = f"[P{paper_num} §{sec_title} #{chunk_idx}]"

                packed_chunks.append(
                    GroundingChunk(
                        paper_id=paper_id,
                        chunk_index=chunk_idx,
                        section_title=sec_title,
                        citation_tag=tag,
                        score=float(cand["score"]),
                        token_count=cand_tokens,
                        text=str(cand["text"]),
                    )
                )
                total_tokens += cand_tokens
            else:
                dropped_count += 1

        # Format grounding text for RAG compartment
        prompt_sections = [
            f"{c.citation_tag}\n{c.text}" for c in packed_chunks
        ]
        grounding_text = "\n\n".join(prompt_sections)

        return ContextBundle(
            debate_id=debate_id,
            agent_id=agent_id,
            paper_id=paper_id,
            chunks=packed_chunks,
            packed_tokens=total_tokens,
            dropped_candidates_count=dropped_count,
            grounding_prompt_text=grounding_text,
        )

    async def validate_citations(
        self,
        generated_text: str,
        supplied_bundle: ContextBundle,
    ) -> list[str]:
        """Verify that every citation tag in agent output references a chunk provided in this call."""
        matches = CITATION_TAG_PATTERN.findall(generated_text)
        supplied_indices = {c.chunk_index for c in supplied_bundle.chunks}
        ungrounded: list[str] = []

        for sec, idx_str in matches:
            idx = int(idx_str)
            if idx not in supplied_indices:
                ungrounded.append(f"[§{sec} #{idx}]")
                await failure_logger.log_failure(
                    code=FailureCode.CITATION_UNGROUNDED,
                    message=f"Agent '{supplied_bundle.agent_id}' cited unsupplied chunk #{idx} in debate '{supplied_bundle.debate_id}'.",
                    debate_id=supplied_bundle.debate_id,
                    paper_id=supplied_bundle.paper_id,
                    severity=Severity.WARNING,
                    component="context_provider",
                )

        return ungrounded


context_provider = ContextProvider()
