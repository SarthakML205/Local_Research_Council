"""Watches data/papers/_inbox/ and automatically imports user-dropped PDFs."""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any

import fitz  # type: ignore[import-untyped]

from app.backend.library.library_store import LibraryPaperRecord, library_store
from app.backend.library.paper_store import paper_store
from app.backend.telemetry.events import FailureCode, Severity
from app.backend.telemetry.failure_log import failure_logger
from app.config import settings

logger = logging.getLogger("app.backend.library.inbox_watcher")


class InboxWatcher:
    """Monitors _inbox/ folder to ingest local user PDFs into sovereign paper folders."""

    def __init__(
        self,
        inbox_dir: Path = settings.PAPERS_DIR / "_inbox",
        paper_store_instance: Any = None,
        library_store_instance: Any = None,
    ) -> None:
        self.inbox_dir = inbox_dir
        self.paper_store = paper_store_instance or paper_store
        self.library_store = library_store_instance or library_store
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def import_pdf(self, source_pdf: Path) -> str:
        """Import a PDF file into the local paper store as local-<hash12>."""
        if not source_pdf.exists() or source_pdf.suffix.lower() != ".pdf":
            raise ValueError(f"Invalid PDF path: {source_pdf}")

        with open(source_pdf, "rb") as f:
            pdf_bytes = f.read()

        hasher = hashlib.sha256(pdf_bytes)
        content_hash = hasher.hexdigest()
        paper_id = f"local-{content_hash[:12]}"

        # Extract title and abstract from page 1 using fitz
        title = source_pdf.stem.replace("_", " ").replace("-", " ").title()
        abstract = ""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if len(doc) > 0:
                first_page_text = doc[0].get_text("text")
                lines = [line.strip() for line in first_page_text.split("\n") if line.strip()]
                if lines:
                    title = lines[0][:150]
                # Look for abstract block
                if "Abstract" in first_page_text:
                    parts = first_page_text.split("Abstract", 1)
                    abstract = parts[1][:1000].strip()
            doc.close()
        except Exception as exc:
            logger.warning(f"Could not extract metadata from {source_pdf}: {exc}")

        metadata: dict[str, Any] = {
            "paper_id": paper_id,
            "arxiv_id": "",
            "title": title,
            "summary": abstract or "User-imported local PDF document.",
            "published": "",
            "authors": ["Local User"],
            "categories": ["local.import"],
            "pdf_url": "",
        }

        # Save to local paper store
        await self.paper_store.init_paper_folder(paper_id, pdf_bytes, metadata)

        # Register in library index
        record = LibraryPaperRecord(
            paper_id=paper_id,
            arxiv_id="",
            version="1",
            title=title,
            authors="Local User",
            published="",
            categories="local.import",
            folder_path=str(self.paper_store.get_paper_folder(paper_id)),
            pdf_path=str(self.paper_store.get_paper_folder(paper_id) / "paper.pdf"),
            source="local_import",
            content_hash=content_hash,
            ingest_status="ingested",
        )
        await self.library_store.register_or_update_paper(record)

        # Remove imported file from inbox
        try:
            source_pdf.unlink()
        except Exception:
            pass

        return paper_id

    async def scan_inbox_once(self) -> list[str]:
        """Scan inbox directory once and import all pending PDFs."""
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        imported_ids: list[str] = []
        for pdf_file in self.inbox_dir.glob("*.pdf"):
            try:
                pid = await self.import_pdf(pdf_file)
                imported_ids.append(pid)
            except Exception as exc:
                await failure_logger.log_failure(
                    code=FailureCode.PAPER_STORAGE_ERROR,
                    message=f"Failed importing inbox PDF {pdf_file.name}: {exc}",
                    severity=Severity.ERROR,
                    component="inbox_watcher",
                )
        return imported_ids

    async def _loop(self) -> None:
        while self._running:
            await self.scan_inbox_once()
            await asyncio.sleep(2.0)

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop(), name="InboxWatcher")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


inbox_watcher = InboxWatcher()
