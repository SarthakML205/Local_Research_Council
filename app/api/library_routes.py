"""LRC Library & Paper Management API Routes.

Exposes endpoints for local paper registry, arXiv paper downloads,
inbox imports, user collections, and council tray staging.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.stream import broadcaster
from app.backend.extraction.batch_processor import batch_extractor
from app.backend.graph.mindmap_synthesizer import mindmap_synthesizer
from app.backend.ingest.arxiv_client import ArxivClient
from app.backend.ingest.chunker import TextChunker
from app.backend.ingest.extractor import PDFExtractor
from app.backend.library.inbox_watcher import InboxWatcher
from app.backend.library.library_store import LibraryStore
from app.backend.library.paper_store import PaperStore
from app.backend.retrieval.qdrant_store import qdrant_store

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


class ResearchSessionRequest(BaseModel):
    problem_statement: str = Field(..., description="Research question, problem statement, or technical doubt")
    max_papers: int = Field(default=3, ge=2, le=6)


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
    """Retrieve complete paper bundle: metadata, manifest, extraction, text, and chunks."""
    manifest = await paper_store.read_manifest(paper_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper '{paper_id}' not found in local store",
        )
    metadata = await paper_store.read_metadata(paper_id)
    extraction = await paper_store.read_extraction(paper_id)
    chunks = await paper_store.read_chunks(paper_id)

    # Read sliced text snippet
    folder = paper_store.get_paper_folder(paper_id)
    sliced_text_file = folder / "sliced_text.txt"
    sliced_text = ""
    if sliced_text_file.exists():
        try:
            sliced_text = sliced_text_file.read_text(encoding="utf-8")
        except Exception:
            pass

    # Ensure rich extraction is generated if missing
    if not extraction:
        try:
            ext_model = await batch_extractor.extract_paper(
                paper_id,
                (metadata or {}).get("summary", ""),
                sliced_text,
            )
            extraction = ext_model.model_dump()
        except Exception as exc:
            logger.warning(f"Could not auto-extract dossier for {paper_id}: {exc}")

    return {
        "paper_id": paper_id,
        "metadata": metadata or {},
        "manifest": manifest,
        "extraction": extraction or {},
        "sliced_text": sliced_text,
        "chunks": chunks,
        "chunk_count": len(chunks),
    }


@router.get("/papers/{paper_id}/pdf")
async def get_paper_pdf(paper_id: str) -> FileResponse:
    """Stream raw PDF binary for embedded reading."""
    pdf_path = paper_store.get_paper_folder(paper_id) / "paper.pdf"
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF for paper '{paper_id}' not found on disk",
        )
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{paper_id}.pdf",
    )


@router.get("/papers/{paper_id}/chunks")
async def get_paper_chunks(paper_id: str) -> list[dict[str, Any]]:
    """Retrieve indexed chunks with token counts and section names."""
    return await paper_store.read_chunks(paper_id)


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
    await paper_store.save_sliced_text(p_id, clean_text)

    # 4. Chunk text into 256-512 token windows
    chunks = text_chunker.chunk_text(p_id, clean_text)
    await paper_store.save_chunks(p_id, chunks)

    # 5. Embed and Index in Qdrant Vector Store
    try:
        await qdrant_store.index_paper_chunks(p_id, chunks)
    except Exception as exc:
        logger.warning(f"Qdrant indexing deferred for {p_id}: {exc}")

    # 6. Index in LibraryStore
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


@router.post("/research/session")
async def start_research_session(req: ResearchSessionRequest) -> dict[str, Any]:
    """Screen 1: Accept problem statement, query arXiv, download, slice, index, and stage papers."""
    # 1. Pipeline stage: Querying arXiv index
    await broadcaster.publish("pipeline_progress", {
        "stage": "querying_arxiv",
        "message": f"Querying arXiv Index for: '{req.problem_statement}'",
        "step": 1,
        "total_steps": 5,
    })

    results = await arxiv_client.search(req.problem_statement, max_results=req.max_papers)
    if not results:
        # Fallback query with broader terms if exact doubt produced 0 hits
        simplified_query = " ".join(req.problem_statement.split()[:4])
        results = await arxiv_client.search(simplified_query, max_results=req.max_papers)

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No matching arXiv papers found for query: '{req.problem_statement}'",
        )

    staged_paper_ids: list[str] = []
    staged_papers_info: list[dict[str, Any]] = []

    # 2. Process each paper through the sovereign pipeline
    for idx, paper_meta in enumerate(results):
        p_id = paper_meta["paper_id"]
        title = paper_meta.get("title", p_id)
        staged_paper_ids.append(p_id)

        # Stage 2: Streaming PDF to disk
        await broadcaster.publish("pipeline_progress", {
            "stage": "streaming_pdf",
            "message": f"[{idx+1}/{len(results)}] Streaming PDF to Disk: {title[:50]}...",
            "step": 2,
            "total_steps": 5,
            "paper_id": p_id,
        })
        try:
            await arxiv_client.download_paper(paper_meta)
        except Exception as exc:
            logger.warning(f"Download issue for {p_id}: {exc}")

        # Stage 3: Slicing high-density pages
        await broadcaster.publish("pipeline_progress", {
            "stage": "slicing_pages",
            "message": f"[{idx+1}/{len(results)}] Slicing High-Density Pages: {p_id}",
            "step": 3,
            "total_steps": 5,
            "paper_id": p_id,
        })
        try:
            clean_text = await pdf_extractor.slice_paper(p_id)
            await paper_store.save_sliced_text(p_id, clean_text)
            chunks = text_chunker.chunk_text(p_id, clean_text)
            await paper_store.save_chunks(p_id, chunks)
            # Embed and Index in Qdrant Vector Store
            try:
                await qdrant_store.index_paper_chunks(p_id, chunks)
            except Exception as q_exc:
                logger.warning(f"Qdrant indexing deferred for {p_id}: {q_exc}")

            # Extract rich structured technical profile
            try:
                await batch_extractor.extract_paper(p_id, paper_meta.get("summary", ""), clean_text)
            except Exception as ext_exc:
                logger.warning(f"Extraction deferred for {p_id}: {ext_exc}")
        except Exception:
            chunks = []

        # Index paper
        await library_store.upsert_paper({
            "paper_id": p_id,
            "title": title,
            "authors": paper_meta.get("authors", []),
            "year": paper_meta.get("published", "")[:4],
            "arxiv_id": paper_meta.get("arxiv_id", p_id),
            "chunk_count": len(chunks),
        })

        staged_papers_info.append({
            "paper_id": p_id,
            "title": title,
            "authors": paper_meta.get("authors", []),
            "chunk_count": len(chunks),
        })

    # Stage 4: Stage in Council Tray
    await library_store.update_council_tray(staged_paper_ids, prompt=req.problem_statement)

    # Stage 5: Synthesize Knowledge Graph
    await broadcaster.publish("pipeline_progress", {
        "stage": "synthesizing_mindmap",
        "message": f"Synthesizing Knowledge Graph across {len(staged_paper_ids)} papers...",
        "step": 5,
        "total_steps": 5,
    })

    graph = await mindmap_synthesizer.build_graph(staged_paper_ids)

    await broadcaster.publish("pipeline_completed", {
        "problem_statement": req.problem_statement,
        "paper_ids": staged_paper_ids,
        "status": "ready",
    })

    return {
        "status": "completed",
        "problem_statement": req.problem_statement,
        "paper_ids": staged_paper_ids,
        "papers": staged_papers_info,
        "graph": graph.model_dump(),
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
