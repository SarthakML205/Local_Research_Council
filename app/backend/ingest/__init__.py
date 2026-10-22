"""Ingestion engine: arXiv scraping, high-density PDF slicing, and exact chunking."""

from app.backend.ingest.arxiv_client import (
    ArxivClient,
    arxiv_client,
    build_arxiv_boolean_query,
    local_cross_encoder_rerank,
    search_and_filter_papers,
)
from app.backend.ingest.batcher import MicroBatcher, batcher
from app.backend.ingest.chunker import TextChunker, chunker
from app.backend.ingest.extractor import PDFExtractor, pdf_extractor

__all__ = [
    "ArxivClient",
    "arxiv_client",
    "build_arxiv_boolean_query",
    "local_cross_encoder_rerank",
    "search_and_filter_papers",
    "PDFExtractor",
    "pdf_extractor",
    "TextChunker",
    "chunker",
    "MicroBatcher",
    "batcher",
]
