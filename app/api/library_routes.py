"""LRC Library & Paper Management API Routes.

Exposes endpoints for local paper registry, arXiv paper downloads,
inbox imports, user collections, and council tray staging.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.backend.ingest.arxiv_client import ArxivClient
from app.backend.ingest.chunker import TextChunker
from app.backend.ingest.extractor import PDFExtractor
from app.backend.library.inbox_watcher import InboxWatcher
from app.backend.library.library_store import LibraryStore
from app.backend.library.paper_store import PaperStore

logger: Final = logging.getLogger(__name__)

router: Final[APIRouter] = APIRouter(prefix="/library", tags=["Library"])

paper_store: Final[PaperStore] = PaperStore()
library_store: Final[LibraryStore] = LibraryStore()
arxiv_client: Final[ArxivClient] = ArxivClient()
pdf_extractor: Final[PDFExtractor] = PDFExtractor()
text_chunker: Final[TextChunker] = TextChunker()
inbox_watcher: Final[InboxWatcher] = InboxWatcher(
    paper_store_instance=paper_store,
    library_store_instance=library_store,
)


class ArxivFetchRequest(BaseModel):
    arxiv_id: str = Field(..., description="arXiv paper ID (e.g., 2301.07041 or 1706.03762)")


class TrayUpdateRequest(BaseModel):
    paper_ids: list[str] = Field(..., description="List of 2 to 6 paper IDs to convene")


class CollectionCreateRequest(BaseModel):
    collection_id: str
    name: str
    description: str = ""
    paper_ids: list[str] = Field(default_factory=list)


@router.get("/papers")
async def list_papers() -> list[dict[str, Any]]:
    """List all registered papers in the library with metadata."""
    return await library_store.get_papers()


@router.get("/papers/{paper_id}")
async def get_paper(paper_id: str) -> dict[str, Any]:
    """Retrieve complete paper bundle: metadata, manifest, and extraction."""
    manifest = await paper_store.read_manifest(paper_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper '{paper_id}' not found in local store",
        )
    metadata = await paper_store.read_metadata(paper_id)
    extraction = await paper_store.read_extraction(paper_id)
    return {
        "paper_id": paper_id,
        "metadata": metadata,
        "manifest": manifest,
        "extraction": extraction,
    }


@router.post("/arxiv/fetch")
async def fetch_arxiv_paper(req: ArxivFetchRequest) -> dict[str, Any]:
    """Download paper from arXiv and run local ingestion pipeline."""
    # 1. Search metadata on arXiv
    results = await arxiv_client.search(req.arxiv_id, max_results=1)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"arXiv ID '{req.arxiv_id}' could not be resolved",
        )
    paper_meta = results[0]
    p_id = paper_meta["paper_id"]

    # 2. Download PDF into sovereign paper folder
    success = await arxiv_client.download_paper(paper_meta)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download PDF for arXiv ID '{req.arxiv_id}'",
        )

    # 3. Slice first 6-8 pages and clean text
    clean_text = await pdf_extractor.slice_paper(p_id)

    # 4. Chunk text into 256-512 token windows
    chunks = text_chunker.chunk_text(p_id, clean_text)

    # 5. Index in LibraryStore
    await library_store.upsert_paper({
        "paper_id": p_id,
        "title": paper_meta.get("title", p_id),
        "authors": paper_meta.get("authors", []),
        "year": paper_meta.get("published", "")[:4],
        "arxiv_id": req.arxiv_id,
        "chunk_count": len(chunks),
    })

    return {
        "status": "success",
        "paper_id": p_id,
        "title": paper_meta.get("title", p_id),
        "chunk_count": len(chunks),
    }


@router.post("/inbox/scan")
async def scan_inbox() -> dict[str, Any]:
    """Scan the _inbox directory and import all pending PDF files."""
    imported_ids = await inbox_watcher.scan_inbox_once()
    return {"status": "success", "imported_count": len(imported_ids), "imported_ids": imported_ids}


@router.get("/collections")
async def list_collections() -> list[dict[str, Any]]:
    """List all user collections."""
    return await library_store.get_collections()


@router.post("/collections")
async def create_collection(req: CollectionCreateRequest) -> dict[str, Any]:
    """Create or update a user collection."""
    await library_store.save_collection(req.model_dump())
    return {"status": "success", "collection_id": req.collection_id}


@router.get("/tray")
async def get_council_tray() -> list[str]:
    """Get the active list of paper IDs staged in the Council Tray."""
    tray = await library_store.get_council_tray()
    p_ids: list[str] = tray.get("paper_ids", [])
    return p_ids


@router.post("/tray")
async def update_council_tray(req: TrayUpdateRequest) -> dict[str, Any]:
    """Update Council Tray paper IDs, enforcing 2 <= count <= 6."""
    count = len(req.paper_ids)
    if count < 2 or count > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Council Tray requires between 2 and 6 papers. Provided: {count}",
        )
    await library_store.update_council_tray(req.paper_ids)
    return {"status": "success", "council_tray": req.paper_ids}


@router.post("/tray/clear")
async def clear_council_tray() -> dict[str, Any]:
    """Clear the Council Tray."""
    await library_store.update_council_tray([])
    return {"status": "success", "council_tray": []}
