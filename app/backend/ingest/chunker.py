"""Section-aware sliding window chunker with exact token boundaries (256-512 tokens)."""

import logging
import re
from typing import Any

import tiktoken

from app.backend.library.paper_store import paper_store
from app.backend.telemetry.events import FailureCode, Severity
from app.backend.telemetry.failure_log import failure_logger
from app.config import settings

logger = logging.getLogger("app.backend.ingest.chunker")

SECTION_HEADER_PATTERN = re.compile(
    r"^(?:(?:[0-9]+\.?)+\s+)?([A-Z][A-Za-z0-9\s\-_]{2,40})$",
    re.MULTILINE,
)


class TextChunker:
    """Splits semantic text into 256-512 token chunks with 10% overlap."""

    def __init__(
        self,
        min_tokens: int = settings.CHUNK_MIN_TOKENS,
        max_tokens: int = settings.CHUNK_MAX_TOKENS,
        overlap_percent: float = settings.CHUNK_OVERLAP_PERCENT,
    ) -> None:
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = int(max_tokens * overlap_percent)
        self.tokenizer: tiktoken.Encoding | None = None
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None

    def count_tokens(self, text: str) -> int:
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        return max(1, len(text.split()))

    def chunk_text(self, paper_id: str, raw_text: str) -> list[dict[str, Any]]:
        """Split text by sections then by token sliding windows."""
        sections = self._split_into_sections(raw_text)
        chunks: list[dict[str, Any]] = []
        global_chunk_idx = 0

        for section_title, section_text in sections:
            tokens = self.tokenizer.encode(section_text) if self.tokenizer else []
            if self.tokenizer and tokens:
                stride = self.max_tokens - self.overlap_tokens
                for i in range(0, len(tokens), stride):
                    window = tokens[i : i + self.max_tokens]
                    if len(window) < self.min_tokens and chunks and i > 0:
                        # Skip trailing undersized chunk if covered by previous window
                        continue
                    chunk_str = self.tokenizer.decode(window)
                    token_count = len(window)

                    # Assert SLA
                    if token_count > self.max_tokens:
                        logger.warning(f"Chunk exceeded max tokens: {token_count} > {self.max_tokens}")

                    chunks.append({
                        "paper_id": paper_id,
                        "section_title": section_title,
                        "chunk_index": global_chunk_idx,
                        "token_count": token_count,
                        "text": chunk_str,
                    })
                    global_chunk_idx += 1
            else:
                # Word-based fallback
                words = section_text.split()
                stride_words = int(self.max_tokens * 0.75) - int(self.overlap_tokens * 0.75)
                for i in range(0, len(words), max(1, stride_words)):
                    window_words = words[i : i + int(self.max_tokens * 0.75)]
                    chunk_str = " ".join(window_words)
                    token_count = len(window_words)
                    chunks.append({
                        "paper_id": paper_id,
                        "section_title": section_title,
                        "chunk_index": global_chunk_idx,
                        "token_count": token_count,
                        "text": chunk_str,
                    })
                    global_chunk_idx += 1

        return chunks

    def _split_into_sections(self, text: str) -> list[tuple[str, str]]:
        """Identify section headings and split text into section blocks."""
        lines = text.split("\n")
        sections: list[tuple[str, str]] = []
        current_title = "Introduction"
        current_lines: list[str] = []

        for line in lines:
            line_str = line.strip()
            if SECTION_HEADER_PATTERN.match(line_str) and len(line_str) < 50:
                if current_lines:
                    sections.append((current_title, "\n".join(current_lines)))
                    current_lines = []
                current_title = line_str
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_title, "\n".join(current_lines)))

        return sections or [("Main", text)]

    async def chunk_paper(self, paper_id: str) -> list[dict[str, Any]]:
        """Load sliced text and save structural chunks to chunks.jsonl."""
        folder = paper_store.get_paper_folder(paper_id)
        txt_path = folder / "sliced_text.txt"
        if not txt_path.exists():
            await failure_logger.log_failure(
                code=FailureCode.CHUNKING_ERROR,
                message=f"Sliced text not found for chunking: {txt_path}",
                paper_id=paper_id,
                severity=Severity.ERROR,
                component="chunker",
            )
            raise FileNotFoundError(f"Missing sliced text: {txt_path}")

        with open(txt_path, encoding="utf-8") as f:
            raw_text = f.read()

        try:
            chunks = self.chunk_text(paper_id, raw_text)
            if not chunks:
                raise ValueError("Chunking produced 0 chunks")
            await paper_store.save_chunks(paper_id, chunks)
            return chunks
        except Exception as exc:
            await failure_logger.log_failure(
                code=FailureCode.CHUNKING_ERROR,
                message=f"Chunking failed for {paper_id}: {exc}",
                paper_id=paper_id,
                severity=Severity.ERROR,
                exception=exc,
                component="chunker",
            )
            await paper_store.mark_stage_failed(paper_id, str(exc))
            raise


chunker = TextChunker()
