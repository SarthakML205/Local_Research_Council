"""Async arXiv search and non-blocking PDF downloader with network egress guard."""

import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from app.backend.library.paper_store import paper_store
from app.backend.telemetry.events import FailureCode, Severity
from app.backend.telemetry.failure_log import failure_logger
from app.core.engine import engine

logger = logging.getLogger("app.backend.ingest.arxiv_client")

ARXIV_API_HOST = "export.arxiv.org"
ALLOWED_HOSTS = {ARXIV_API_HOST, "localhost", "127.0.0.1"}


class ArxivClient:
    """Queries arXiv API and streams PDF binaries directly into paper folders."""

    def __init__(self, timeout_s: float = 20.0) -> None:
        self.timeout_s = timeout_s

    def _verify_host(self, url: str) -> None:
        """Enforce Zero-Cloud Egress Invariant."""
        for allowed in ALLOWED_HOSTS:
            if f"://{allowed}" in url or url.startswith(f"http://{allowed}"):
                return
        raise PermissionError(f"NETWORK_GUARD_TRIGGER: External egress to unauthorized host blocked: {url}")

    async def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Query arXiv Atom feed asynchronously for relevant papers."""
        url = f"http://{ARXIV_API_HOST}/api/query?search_query=all:{query}&start=0&max_results={max_results}&sortBy=relevance"
        self._verify_host(url)

        async def _fetch() -> list[dict[str, Any]]:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    raise RuntimeError(f"arXiv API error {resp.status_code}: {resp.text}")
                return self._parse_atom_feed(resp.text)

        try:
            return await engine.run_io_bounded(_fetch())
        except Exception as exc:
            await failure_logger.log_failure(
                code=FailureCode.ARXIV_FETCH_ERROR,
                message=f"arXiv query failed for '{query}': {exc}",
                severity=Severity.ERROR,
                exception=exc,
                component="arxiv_client",
            )
            return []

    def _parse_atom_feed(self, xml_text: str) -> list[dict[str, Any]]:
        """Parse arXiv Atom XML response."""
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        root = ET.fromstring(xml_text)
        entries: list[dict[str, Any]] = []

        for entry in root.findall("atom:entry", ns):
            id_url = entry.findtext("atom:id", "", ns)
            # Extract arxiv id, e.g. http://arxiv.org/abs/2301.00123v1 -> 2301.00123v1
            arxiv_id = id_url.split("/abs/")[-1] if "/abs/" in id_url else id_url.split("/")[-1]
            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
            summary = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")
            published = entry.findtext("atom:published", "", ns)
            authors = [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)]

            categories = [
                c.attrib.get("term", "")
                for c in entry.findall("atom:category", ns)
                if c.attrib.get("term")
            ]

            pdf_url = f"http://{ARXIV_API_HOST}/pdf/{arxiv_id}.pdf"
            entries.append({
                "paper_id": arxiv_id,
                "arxiv_id": arxiv_id,
                "title": title,
                "summary": summary,
                "published": published,
                "authors": authors,
                "categories": categories,
                "pdf_url": pdf_url,
            })
        return entries

    async def download_paper(self, paper_meta: dict[str, Any]) -> bool:
        """Download paper PDF directly into its local paper folder if not already cached."""
        paper_id = paper_meta["paper_id"]

        # Check local folder cache first
        manifest = await paper_store.get_manifest(paper_id)
        if manifest and "downloaded" in manifest.stages_completed:
            if await paper_store.verify_integrity(paper_id):
                logger.info(f"Paper {paper_id} already cached locally with verified integrity.")
                return True

        pdf_url = paper_meta.get("pdf_url") or f"http://{ARXIV_API_HOST}/pdf/{paper_id}.pdf"
        self._verify_host(pdf_url)

        async def _stream_download() -> bytes:
            async with httpx.AsyncClient(timeout=self.timeout_s, follow_redirects=True) as client:
                resp = await client.get(pdf_url)
                if resp.status_code != 200:
                    raise RuntimeError(f"Failed to download PDF: HTTP {resp.status_code}")
                return resp.content

        try:
            pdf_bytes = await engine.run_io_bounded(_stream_download())
            await paper_store.init_paper_folder(paper_id, pdf_bytes, paper_meta)
            return True
        except Exception as exc:
            await failure_logger.log_failure(
                code=FailureCode.ARXIV_FETCH_ERROR,
                message=f"Failed downloading PDF for {paper_id}: {exc}",
                severity=Severity.ERROR,
                paper_id=paper_id,
                exception=exc,
                component="arxiv_client",
            )
            await paper_store.mark_stage_failed(paper_id, str(exc))
            return False


arxiv_client = ArxivClient()
