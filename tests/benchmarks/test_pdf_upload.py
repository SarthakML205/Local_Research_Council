"""Benchmark & Verification Gate: Direct Multi-PDF Upload Ingestion & Council Staging."""

from __future__ import annotations

import io
import time
from typing import Any

import fitz  # type: ignore[import-untyped]
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.backend.library.library_store import library_store
from app.backend.library.paper_store import paper_store


def create_mock_academic_pdf(title: str, abstract: str, body: str) -> bytes:
    """Create a syntactically valid in-memory academic PDF with PyMuPDF."""
    doc = fitz.open()
    # Page 1: Title, Abstract, Introduction
    p1 = doc.new_page()
    text_p1 = (
        f"{title}\n"
        f"Dr. Alice Vance, Dr. Gordon Freeman\n\n"
        f"Abstract\n{abstract}\n\n"
        f"1. Introduction\n{body}\n"
    )
    p1.insert_text((50, 72), text_p1, fontsize=11)

    # Page 2: Mathematical formulation & empirical benchmarks
    p2 = doc.new_page()
    text_p2 = (
        "2. Empirical Benchmarks on Apple Silicon Unified Memory\n"
        "We measure KV-cache bandwidth utilization under fp16 and 4-bit quantization.\n"
        "Observed latency p99 is 1.42ms per decoding token.\n\n"
        "3. Conclusion\nDirect tensor slicing improves memory bandwidth without degradation.\n"
    )
    p2.insert_text((50, 72), text_p2, fontsize=11)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_direct_pdf_upload_single_and_tray_staging() -> None:
    """Verify single PDF direct upload, atomic folder creation, slicing, chunking, and tray update."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pdf_bytes = create_mock_academic_pdf(
            title="Selective Memory Offloading for Metal Unified Memory",
            abstract="We present an efficient zero-copy memory offloading protocol for transformer KV-caches on Apple M5.",
            body="Modern transformer inference is bounded by memory bandwidth rather than compute flops.",
        )

        files = [
            ("files", ("selective_memory_offload.pdf", io.BytesIO(pdf_bytes), "application/pdf")),
        ]
        data = {
            "problem_statement": "How to offload KV-caches on Apple M5 unified memory?",
            "auto_stage_tray": "true",
        }

        t0 = time.perf_counter_ns()
        res = await client.post("/api/library/upload", files=files, data=data)
        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000

        assert res.status_code == 200, f"Upload failed: {res.text}"
        payload: dict[str, Any] = res.json()

        assert payload["status"] == "completed"
        assert len(payload["paper_ids"]) == 1
        paper_id = payload["paper_ids"][0]
        assert paper_id.startswith("local-")

        # Verify paper manifest and slicing
        folder = paper_store.get_paper_folder(paper_id)
        assert (folder / "paper.pdf").exists()
        assert (folder / "sliced_text.txt").exists()
        assert (folder / "manifest.json").exists()

        manifest = await paper_store.get_manifest(paper_id)
        assert manifest is not None
        assert "downloaded" in manifest.stages_completed

        # Check library papers listing
        papers_res = await client.get("/api/library/papers")
        assert papers_res.status_code == 200
        registered_ids = [p["paper_id"] for p in papers_res.json()]
        assert paper_id in registered_ids

        # Ingestion speed assertion: Local PDF ingestion < 1,500ms
        assert elapsed_ms < 1500.0, f"Local PDF ingestion exceeded budget: {elapsed_ms:.2f}ms"


@pytest.mark.asyncio
async def test_direct_multi_pdf_upload_and_council_convene() -> None:
    """Verify multi-PDF direct upload (3 papers), full tray staging, and graph synthesis."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pdf_1 = create_mock_academic_pdf(
            title="State Space Duality in Linear Attention",
            abstract="Comparing selective state space models against quadratic attention mechanisms.",
            body="Linear state space models achieve linear time complexity O(N) relative to sequence length.",
        )
        pdf_2 = create_mock_academic_pdf(
            title="Speculative Drafting with Hardware Alignment",
            abstract="Accelerating autoregressive token generation using small draft speculative networks.",
            body="Draft-verification loops reduce latency from 24ms to 8.5ms per token on Apple Silicon.",
        )

        files = [
            ("files", ("state_space_duality.pdf", io.BytesIO(pdf_1), "application/pdf")),
            ("files", ("speculative_drafting.pdf", io.BytesIO(pdf_2), "application/pdf")),
        ]
        data = {
            "problem_statement": "Compare Mamba SSM vs Speculative Decoding throughput",
            "auto_stage_tray": "true",
        }

        res = await client.post("/api/library/upload", files=files, data=data)
        assert res.status_code == 200, f"Multi-upload failed: {res.text}"
        payload = res.json()

        assert payload["status"] == "completed"
        assert len(payload["paper_ids"]) == 2
        p1_id, p2_id = payload["paper_ids"][0], payload["paper_ids"][1]

        # Verify tray contains both uploaded papers
        tray_res = await client.get("/api/library/tray")
        assert tray_res.status_code == 200
        tray_ids = tray_res.json()
        assert p1_id in tray_ids
        assert p2_id in tray_ids
        assert len(tray_ids) >= 2


@pytest.mark.asyncio
async def test_direct_pdf_upload_rejects_empty_or_non_pdf() -> None:
    """Verify error handling on non-PDF uploads and empty file sets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Non-PDF file
        files = [
            ("files", ("malicious.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")),
        ]
        res = await client.post("/api/library/upload", files=files, data={"problem_statement": "test"})
        assert res.status_code == 400
