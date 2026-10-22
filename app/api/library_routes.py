"""LRC Library & Paper Management API Routes.

Exposes endpoints for local paper registry, arXiv paper downloads,
inbox imports, user collections, and council tray staging.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Final

import fitz  # type: ignore[import-untyped]
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
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
from app.backend.retrieval.comparison_engine import compare_all_strategies
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
    strategy: str = Field(
        default="strategy_c_hybrid_rerank",
        description="Retrieval strategy: strategy_a_code_only | strategy_b_local_llm | strategy_c_hybrid_rerank",
    )
    selected_paper_ids: list[str] = Field(
        default_factory=list,
        description="Optional pre-selected paper IDs if chosen from comparison view",
    )


class StrategyComparisonRequest(BaseModel):
    query: str = Field(..., description="Research query or technical problem statement")
    max_papers: int = Field(default=4, ge=2, le=6)


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


@router.post("/research/compare")
async def compare_retrieval_strategies(req: StrategyComparisonRequest) -> dict[str, Any]:
    """Execute 3-way retrieval strategy comparison concurrently (Code vs Local LLM vs Hybrid Rerank)."""
    comparison = await compare_all_strategies(
        query=req.query,
        max_papers=req.max_papers,
    )
    return comparison.model_dump()


@router.post("/research/session")
async def start_research_session(req: ResearchSessionRequest) -> dict[str, Any]:
    """Screen 1: Accept problem statement, query arXiv, download, slice, index, and stage papers."""
    # 1. Pipeline stage: Querying arXiv index
    await broadcaster.publish("pipeline_progress", {
        "stage": "querying_arxiv",
        "message": f"Querying arXiv Index using {req.strategy}: '{req.problem_statement}'",
        "step": 1,
        "total_steps": 5,
    })

    results: list[dict[str, Any]] = []

    # If specific paper IDs were selected from comparison view, resolve them directly
    if req.selected_paper_ids:
        for pid in req.selected_paper_ids[:req.max_papers]:
            p_res = await arxiv_client.search_by_id(pid)
            if p_res:
                results.append(p_res[0])
    elif req.strategy != "strategy_c_hybrid_rerank":
        # Run specific non-default strategy via comparison engine
        comparison = await compare_all_strategies(req.problem_statement, max_papers=req.max_papers)
        chosen_strat = comparison.strategies.get(req.strategy)
        if chosen_strat and chosen_strat.papers:
            for m in chosen_strat.papers:
                results.append({
                    "paper_id": m.paper_id,
                    "arxiv_id": m.arxiv_id,
                    "title": m.title,
                    "summary": m.summary,
                    "published": m.published,
                    "authors": m.authors,
                    "score": m.score,
                    "pdf_url": f"https://export.arxiv.org/pdf/{m.arxiv_id}.pdf",
                })

    # Default to Strategy C (Flagship Hybrid Rerank)
    if not results:
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


@router.post("/upload")
async def upload_pdf_papers(
    files: list[UploadFile] = File(...),
    problem_statement: str = Form(default=""),
    auto_stage_tray: bool = Form(default=True),
) -> dict[str, Any]:
    """Upload one or more PDF research papers directly into local sovereign library.

    Extracts high-density pages, chunks text, computes MLX embeddings, indexes into Qdrant,
    generates mind map relationships, and optionally stages into Council Tray.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No PDF files provided for upload.",
        )

    uploaded_ids: list[str] = []
    uploaded_papers_info: list[dict[str, Any]] = []
    total_files = len(files)

    for idx, file in enumerate(files):
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            continue

        raw_bytes = await file.read()
        if not raw_bytes:
            continue

        content_hash = hashlib.sha256(raw_bytes).hexdigest()
        paper_id = f"local-{content_hash[:12]}"
        uploaded_ids.append(paper_id)

        clean_stem = Path(file.filename).stem.replace("_", " ").replace("-", " ").title()
        title = clean_stem
        authors = ["Local Researcher"]
        abstract = ""

        try:
            doc = fitz.open(stream=raw_bytes, filetype="pdf")
            if len(doc) > 0:
                first_page = doc[0].get_text("text")
                lines = [line.strip() for line in first_page.split("\n") if line.strip()]
                if lines:
                    title = lines[0][:150]
                if len(lines) > 1 and len(lines[1]) < 100 and not lines[1].lower().startswith("abstract"):
                    authors = [a.strip() for a in lines[1].split(",") if a.strip()][:4]
                if "Abstract" in first_page:
                    parts = first_page.split("Abstract", 1)
                    abstract = parts[1][:1000].strip()
            doc.close()
        except Exception as exc:
            logger.warning(f"Could not parse PDF metadata via PyMuPDF for {file.filename}: {exc}")

        # Broadcast progress: Storing to disk
        await broadcaster.publish("pipeline_progress", {
            "stage": "streaming_pdf",
            "message": f"[{idx+1}/{total_files}] Ingesting Local PDF to Disk: {title[:50]}...",
            "step": 2,
            "total_steps": 5,
            "paper_id": paper_id,
        })

        metadata: dict[str, Any] = {
            "paper_id": paper_id,
            "arxiv_id": f"local/{file.filename}",
            "title": title,
            "summary": abstract or f"Locally uploaded research document '{file.filename}'.",
            "published": "2026",
            "authors": authors,
            "categories": ["local.upload"],
            "pdf_url": "",
        }

        # Initialize sovereign paper folder atomically
        await paper_store.init_paper_folder(paper_id, raw_bytes, metadata)

        # Slicing high-density pages
        await broadcaster.publish("pipeline_progress", {
            "stage": "slicing_pages",
            "message": f"[{idx+1}/{total_files}] Slicing Dense Technical Content: {paper_id}",
            "step": 3,
            "total_steps": 5,
            "paper_id": paper_id,
        })

        chunks: list[dict[str, Any]] = []
        try:
            clean_text = await pdf_extractor.slice_paper(paper_id)
            await paper_store.save_sliced_text(paper_id, clean_text)
            chunks = text_chunker.chunk_text(paper_id, clean_text)
            await paper_store.save_chunks(paper_id, chunks)

            # Embed & Index into Qdrant
            try:
                await qdrant_store.index_paper_chunks(paper_id, chunks)
                await paper_store.mark_stage_completed(paper_id, "indexed")
            except Exception as q_exc:
                logger.warning(f"Qdrant indexing deferred for {paper_id}: {q_exc}")

            # Extract structured technical profile
            try:
                await batch_extractor.extract_paper(paper_id, abstract, clean_text)
            except Exception as ext_exc:
                logger.warning(f"Extraction deferred for {paper_id}: {ext_exc}")
        except Exception as exc:
            logger.error(f"Failed processing PDF pipeline for {paper_id}: {exc}")

        # Register in Library Store
        await library_store.upsert_paper({
            "paper_id": paper_id,
            "title": title,
            "authors": authors,
            "year": "2026",
            "arxiv_id": f"upload/{file.filename}",
            "chunk_count": len(chunks),
            "content_hash": content_hash,
            "source": "local_import",
        })

        uploaded_papers_info.append({
            "paper_id": paper_id,
            "title": title,
            "authors": authors,
            "chunk_count": len(chunks),
            "filename": file.filename,
        })

    if not uploaded_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid PDF documents could be processed.",
        )

    # Optional auto-staging into Council Tray
    if auto_stage_tray:
        tray = await library_store.get_council_tray()
        existing = tray.get("paper_ids", [])
        if len(uploaded_ids) >= 2:
            staged = uploaded_ids[:6]
        else:
            staged = list(dict.fromkeys(uploaded_ids + existing))[:6]
            if len(staged) < 2:
                all_p = await library_store.get_papers()
                for p in all_p:
                    p_id = p.get("paper_id")
                    if p_id and p_id not in staged:
                        staged.append(p_id)
                        if len(staged) >= 2:
                            break
        if len(staged) >= 2:
            await library_store.update_council_tray(staged, prompt=problem_statement or "Uploaded PDF Debate")

    # Synthesize Knowledge Graph
    await broadcaster.publish("pipeline_progress", {
        "stage": "synthesizing_mindmap",
        "message": f"Synthesizing Knowledge Graph across {len(uploaded_ids)} uploaded papers...",
        "step": 5,
        "total_steps": 5,
    })

    graph = await mindmap_synthesizer.build_graph(uploaded_ids)

    await broadcaster.publish("pipeline_completed", {
        "problem_statement": problem_statement or "Local PDF Upload",
        "paper_ids": uploaded_ids,
        "status": "ready",
    })

    tray_data = await library_store.get_council_tray()

    return {
        "status": "completed",
        "problem_statement": problem_statement,
        "paper_ids": uploaded_ids,
        "papers": uploaded_papers_info,
        "graph": graph.model_dump(),
        "council_tray": tray_data.get("paper_ids", []),
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
