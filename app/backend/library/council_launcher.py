"""Council Launcher: validates 2..N paper selection, injects relation context, and launches debate."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Final

from app.backend.agents.turn_manager import ActiveDebateState, turn_manager
from app.backend.ingest.chunker import TextChunker
from app.backend.ingest.extractor import PDFExtractor
from app.backend.library.library_store import LibraryStore
from app.backend.library.library_store import library_store as default_lib_store
from app.backend.library.paper_store import PaperStore
from app.backend.library.paper_store import paper_store as default_paper_store
from app.backend.retrieval.qdrant_store import qdrant_store
from app.backend.telemetry.events import FailureCode, Severity
from app.backend.telemetry.failure_log import failure_logger
from app.config import settings

logger: Final = logging.getLogger("app.backend.library.council_launcher")

pdf_extractor: Final[PDFExtractor] = PDFExtractor()
text_chunker: Final[TextChunker] = TextChunker()


class CouncilLauncher:
    """Validates paper selection bounds (2 to 6) and stages debate execution."""

    def __init__(
        self,
        paper_store_instance: PaperStore | None = None,
        library_store_instance: LibraryStore | None = None,
        min_papers: int = settings.COUNCIL_MIN_PAPERS,
        max_papers: int = settings.COUNCIL_MAX_PAPERS,
    ) -> None:
        self.paper_store = paper_store_instance or default_paper_store
        self.library_store = library_store_instance or default_lib_store
        self.min_papers = min_papers
        self.max_papers = max_papers

    async def _ensure_qdrant_indexed(self, paper_id: str) -> None:
        """Guarantee paper chunks are embedded and present in Qdrant before debate."""
        try:
            points = await qdrant_store.count_points(paper_id)
            if points > 0:
                return

            chunks = await self.paper_store.read_chunks(paper_id)
            if not chunks:
                # Sliced text check
                folder = self.paper_store.get_paper_folder(paper_id)
                sliced_file = folder / "sliced_text.txt"
                if sliced_file.exists():
                    text = sliced_file.read_text(encoding="utf-8")
                else:
                    text = await pdf_extractor.slice_paper(paper_id)
                    await self.paper_store.save_sliced_text(paper_id, text)
                chunks = text_chunker.chunk_text(paper_id, text)
                await self.paper_store.save_chunks(paper_id, chunks)

            if chunks:
                await qdrant_store.index_paper_chunks(paper_id, chunks)
        except Exception as exc:
            logger.warning(f"Could not auto-index {paper_id} in Qdrant: {exc}")

    async def stage_debate(
        self,
        paper_ids: list[str],
        user_agenda: str,
    ) -> dict[str, Any]:
        """Validate selection bounds and return staged manifest."""
        if len(paper_ids) < self.min_papers or len(paper_ids) > self.max_papers:
            await failure_logger.log_failure(
                code=FailureCode.COUNCIL_SELECTION_INVALID,
                message=f"Council selection must be between {self.min_papers} and {self.max_papers} papers. Got {len(paper_ids)}.",
                severity=Severity.WARNING,
                component="council_launcher",
            )
            raise ValueError(
                f"Selection rejected: Council debate requires between {self.min_papers} and {self.max_papers} papers. Got {len(paper_ids)}."
            )

        staged_papers: list[dict[str, Any]] = []
        for pid in paper_ids:
            manifest = await self.paper_store.get_manifest(pid)
            meta = await self.paper_store.read_metadata(pid) or {}
            await self._ensure_qdrant_indexed(pid)
            staged_papers.append({
                "paper_id": pid,
                "title": meta.get("title", pid),
                "has_manifest": manifest is not None,
            })

        return {
            "status": "staged",
            "paper_count": len(paper_ids),
            "papers": staged_papers,
            "agenda": user_agenda,
        }

    async def launch_debate(
        self,
        paper_ids: list[str],
        prompt: str,
        rounds: int = 2,
    ) -> ActiveDebateState:
        """Validate selection bounds and launch debate."""
        # Selection bounds validation
        if len(paper_ids) < self.min_papers or len(paper_ids) > self.max_papers:
            await failure_logger.log_failure(
                code=FailureCode.COUNCIL_SELECTION_INVALID,
                message=f"Council selection must be between {self.min_papers} and {self.max_papers} papers. Got {len(paper_ids)}.",
                severity=Severity.WARNING,
                component="council_launcher",
            )
            raise ValueError(
                f"Selection rejected: Council debate requires between {self.min_papers} and {self.max_papers} papers. Got {len(paper_ids)}."
            )

        # Integrity check for each paper
        for pid in paper_ids:
            manifest = await self.paper_store.get_manifest(pid)
            if not manifest:
                await failure_logger.log_failure(
                    code=FailureCode.LIBRARY_ERROR,
                    message=f"Cannot launch debate: Paper '{pid}' folder or manifest not found.",
                    paper_id=pid,
                    severity=Severity.ERROR,
                    component="council_launcher",
                )
                raise FileNotFoundError(f"Paper '{pid}' is not ready for debate (missing manifest).")

        # Fetch relation context
        all_relations = await self.library_store.get_relations()
        relevant_relations = [
            r for r in all_relations
            if r.get("paper_a") in paper_ids and r.get("paper_b") in paper_ids
        ]

        relation_notes: list[str] = []
        for r in relevant_relations:
            relation_notes.append(
                f"Relation: {r.get('paper_a')} {r.get('type')} {r.get('paper_b')}. Note: {r.get('note', '')}"
            )

        enriched_prompt = prompt
        if relation_notes:
            enriched_prompt += "\n\nKnown Relations:\n" + "\n".join(relation_notes)

        debate_id = str(uuid.uuid4())[:8]

        session = await turn_manager.create_session(
            debate_id=debate_id,
            paper_ids=paper_ids,
            prompt=enriched_prompt,
            rounds=rounds,
        )
        return session


council_launcher: Final[CouncilLauncher] = CouncilLauncher()
