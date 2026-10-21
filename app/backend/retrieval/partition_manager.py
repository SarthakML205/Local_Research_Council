"""Context partition manager: enforces structural and logical cross-paper isolation."""

import logging

from qdrant_client import models

from app.backend.retrieval.qdrant_store import qdrant_store
from app.backend.telemetry.events import FailureCode, Severity
from app.backend.telemetry.failure_log import failure_logger

logger = logging.getLogger("app.backend.retrieval.partition_manager")


class PaperIndexHandle:
    """Isolated query handle bound strictly to one paper collection."""

    def __init__(self, paper_id: str, agent_id: str) -> None:
        self.paper_id = paper_id
        self.agent_id = agent_id
        self.collection_name = qdrant_store.get_collection_name(paper_id)

    async def search_dense(
        self,
        query_vector: list[float],
        limit: int = 10,
    ) -> list[models.ScoredPoint]:
        """Execute dense vector search restricted to this paper's collection and paper_id filter."""
        client = await qdrant_store.get_client()

        # Defense-in-depth: collection isolation + payload filter
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="paper_id",
                    match=models.MatchValue(value=self.paper_id),
                )
            ]
        )

        try:
            res = await client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="dense",
                query_filter=query_filter,
                limit=limit,
            )
            return list(res.points)
        except Exception as exc:
            # Check for collection missing or qdrant error
            await failure_logger.log_failure(
                code=FailureCode.QDRANT_ERROR,
                message=f"Search failed on collection {self.collection_name}: {exc}",
                paper_id=self.paper_id,
                severity=Severity.WARNING,
                component="partition_manager",
            )
            return []

    async def search_sparse(
        self,
        query_words: list[str],
        limit: int = 10,
    ) -> list[models.ScoredPoint]:
        """Execute sparse BM25-surrogate search restricted to this paper."""
        client = await qdrant_store.get_client()
        sparse_indices = [abs(hash(w)) % 100000 for w in query_words]
        sparse_values = [1.0] * len(sparse_indices)

        sparse_vector = models.SparseVector(indices=sparse_indices, values=sparse_values)

        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="paper_id",
                    match=models.MatchValue(value=self.paper_id),
                )
            ]
        )

        try:
            res = await client.query_points(
                collection_name=self.collection_name,
                query=sparse_vector,
                using="sparse",
                query_filter=query_filter,
                limit=limit,
            )
            return list(res.points)
        except Exception as exc:
            logger.error(f"Sparse search error on {self.collection_name}: {exc}")
            return []


class PartitionManager:
    """Creates strictly partitioned handles and enforces zero cross-talk between paper advocates."""

    def __init__(self) -> None:
        self._assigned_handles: dict[str, str] = {}  # agent_id -> paper_id

    def create_handle(self, agent_id: str, paper_id: str) -> PaperIndexHandle:
        """Hand out an isolated PaperIndexHandle to an authorized agent."""
        if agent_id == "moderator":
            raise PermissionError("PARTITION_VIOLATION: Moderator agent has 0 Qdrant access by design.")

        # Record assignment
        self._assigned_handles[agent_id] = paper_id
        return PaperIndexHandle(paper_id=paper_id, agent_id=agent_id)

    async def verify_partition_access(self, agent_id: str, target_paper_id: str) -> None:
        """Assert that an agent is never accessing an opponent's paper partition."""
        assigned = self._assigned_handles.get(agent_id)
        if assigned != target_paper_id:
            await failure_logger.log_failure(
                code=FailureCode.PARTITION_VIOLATION,
                message=f"Agent '{agent_id}' attempted unauthorized access to partition '{target_paper_id}' (assigned: '{assigned}').",
                paper_id=target_paper_id,
                severity=Severity.FATAL,
                component="partition_manager",
            )
            raise PermissionError(
                f"PARTITION_VIOLATION: Agent '{agent_id}' cannot access paper '{target_paper_id}'."
            )


partition_manager = PartitionManager()
