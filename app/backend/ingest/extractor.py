import asyncio
import logging
import re

import fitz  # type: ignore[import-untyped]

from app.backend.library.paper_store import paper_store
from app.backend.telemetry.events import FailureCode, Severity
from app.backend.telemetry.failure_log import failure_logger
from app.config import settings
from app.core.engine import engine

logger = logging.getLogger("app.backend.ingest.extractor")

LIGATURE_REPLACEMENTS = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬀ": "ff",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
}

# Regex for stripping reference lists and appendix dumps
REFERENCES_PATTERN = re.compile(
    r"\n\s*(?:(?:[0-9]+\.?\s*)?(?:References|REFERENCES|Bibliography|BIBLIOGRAPHY))\s*\n.*",
    re.DOTALL,
)
APPENDIX_PATTERN = re.compile(
    r"\n\s*(?:(?:[0-9]+\.?\s*)?(?:Appendix|APPENDIX))\s*\n.*",
    re.DOTALL,
)
PAGE_NUMBER_PATTERN = re.compile(r"^\s*(?:Page\s+)?\d+\s*$", re.MULTILINE)


class PDFExtractor:
    """Slices first 6-8 pages of research PDFs and strips citations/bibliography noise."""

    def __init__(self, max_pages: int = settings.PDF_MAX_PAGES) -> None:
        self.max_pages = max_pages

    def clean_text(self, text: str) -> str:
        """Strip ligatures, headers/footers, and truncate before references/appendices."""
        for lig, repl in LIGATURE_REPLACEMENTS.items():
            text = text.replace(lig, repl)

        # Truncate at References or Appendix boundaries
        text = REFERENCES_PATTERN.sub("", text)
        text = APPENDIX_PATTERN.sub("", text)

        # Strip page numbers
        text = PAGE_NUMBER_PATTERN.sub("", text)

        # Normalize redundant newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    async def slice_paper(self, paper_id: str) -> str:
        """Slice and clean text from the paper's local PDF."""
        folder = paper_store.get_paper_folder(paper_id)
        pdf_path = folder / "paper.pdf"

        if not pdf_path.exists():
            await failure_logger.log_failure(
                code=FailureCode.PDF_PARSE_ERROR,
                message=f"PDF not found for slicing: {pdf_path}",
                paper_id=paper_id,
                severity=Severity.ERROR,
                component="extractor",
            )
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        def _sync_slice() -> str:
            doc = fitz.open(pdf_path)
            try:
                page_count = min(len(doc), self.max_pages)
                extracted_pages: list[str] = []
                for page_idx in range(page_count):
                    page = doc[page_idx]
                    page_text = page.get_text("text")
                    if page_text:
                        extracted_pages.append(page_text)

                combined_text = "\n\n".join(extracted_pages)
                return self.clean_text(combined_text)
            finally:
                doc.close()

        try:
            cleaned: str = await engine.run_io_bounded(asyncio.to_thread(_sync_slice))
            if not cleaned:
                raise ValueError("PyMuPDF extracted 0 readable text characters")

            await paper_store.save_sliced_text(paper_id, cleaned)
            return cleaned
        except Exception as exc:
            await failure_logger.log_failure(
                code=FailureCode.PDF_PARSE_ERROR,
                message=f"Failed slicing PDF for {paper_id}: {exc}",
                paper_id=paper_id,
                severity=Severity.ERROR,
                exception=exc,
                component="extractor",
            )
            await paper_store.mark_stage_failed(paper_id, str(exc))
            raise


pdf_extractor = PDFExtractor()
