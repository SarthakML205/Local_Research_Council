import csv
import fcntl
import logging
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.backend.library.paper_store import paper_store
from app.config import settings
from app.core.file_store import _get_path_lock, file_store

logger = logging.getLogger("app.backend.library.library_store")

PAPERS_CSV_HEADERS = [
    "paper_id",
    "arxiv_id",
    "version",
    "title",
    "authors",
    "published",
    "categories",
    "folder_path",
    "pdf_path",
    "source",
    "content_hash",
    "pages_sliced",
    "chunk_count",
    "ingest_status",
    "indexed",
    "study_rank",
    "first_seen_session",
    "last_used_at",
    "times_debated",
    "cover_seed",
]


class LibraryPaperRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    paper_id: str
    arxiv_id: str
    version: str = "1"
    title: str
    authors: str  # Semicolon joined
    published: str
    categories: str  # Semicolon joined
    folder_path: str
    pdf_path: str
    source: str = "arxiv"  # arxiv | local_import
    content_hash: str
    pages_sliced: int = 0
    chunk_count: int = 0
    ingest_status: str = "ingested"  # ingested | indexed | failed
    indexed: bool = False
    study_rank: int = 0
    first_seen_session: str = ""
    last_used_at: str = ""
    times_debated: int = 0
    cover_seed: int = 42


class LibraryStore:
    """Zero-database library catalog using CSV and JSON files with rolling backups."""

    def __init__(self, base_dir: Path = settings.LIBRARY_DIR) -> None:
        self.base_dir = base_dir
        self.papers_csv = base_dir / "papers.csv"
        self.collections_json = base_dir / "collections.json"
        self.relations_json = base_dir / "relations.json"
        self.tray_json = base_dir / "council_tray.json"

    async def list_papers(self) -> list[dict[str, str]]:
        """Read all papers registered in the library index."""
        rows, _ = await file_store.read_csv_tolerant(self.papers_csv)
        return rows

    async def register_or_update_paper(self, record: LibraryPaperRecord) -> None:
        """Atomically register or update a paper in papers.csv."""
        existing_rows, _ = await file_store.read_csv_tolerant(self.papers_csv)
        updated_rows: list[dict[str, Any]] = []
        found = False

        for row in existing_rows:
            if row.get("paper_id") == record.paper_id or (
                row.get("content_hash") == record.content_hash and record.content_hash != ""
            ):
                updated_rows.append(record.model_dump())
                found = True
            else:
                updated_rows.append(row)

        if not found:
            updated_rows.append(record.model_dump())

        # Rewrite CSV atomically via temp file in library directory
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Use file_store's backup and atomic write mechanism
        lock_file = self.papers_csv.with_suffix(".csv.lock")

        path_lock = await _get_path_lock(self.papers_csv)
        async with path_lock:
            with open(lock_file, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    file_store._rotate_backups(self.papers_csv)
                    with tempfile.NamedTemporaryFile("w", dir=self.base_dir, delete=False, newline="", encoding="utf-8") as tf:
                        temp_path = Path(tf.name)
                        writer = csv.DictWriter(tf, fieldnames=PAPERS_CSV_HEADERS, extrasaction="ignore")
                        writer.writeheader()
                        for row in updated_rows:
                            writer.writerow(row)
                        tf.flush()
                        os.fsync(tf.fileno())
                    os.replace(temp_path, self.papers_csv)
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    async def get_council_tray(self) -> dict[str, Any]:
        """Read staged papers for the Council tray."""
        data = await file_store.read_json_safe(self.tray_json, fallback_default={"paper_ids": [], "prompt": ""})
        return data if isinstance(data, dict) else {"paper_ids": [], "prompt": ""}

    async def update_council_tray(self, paper_ids: list[str], prompt: str = "") -> dict[str, Any]:
        """Update council tray staging. Enforces 2 to COUNCIL_MAX_PAPERS bounds."""
        if len(paper_ids) > settings.COUNCIL_MAX_PAPERS:
            raise ValueError(
                f"Council tray cannot exceed {settings.COUNCIL_MAX_PAPERS} papers. Got {len(paper_ids)}."
            )

        payload = {
            "paper_ids": paper_ids,
            "prompt": prompt,
            "updated_at": time.time(),
        }
        await file_store.write_json_atomic(self.tray_json, payload)
        return payload

    async def get_relations(self) -> list[dict[str, Any]]:
        data = await file_store.read_json_safe(self.relations_json, fallback_default=[])
        return data if isinstance(data, list) else []

    async def save_relations(self, relations: list[dict[str, Any]]) -> None:
        await file_store.write_json_atomic(self.relations_json, relations)

    async def add_relation(
        self,
        paper_a: str,
        paper_b: str,
        rel_type: str,
        note: str = "",
        source: str = "user",
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        relations = await self.get_relations()
        rel_record = {
            "relation_id": str(uuid.uuid4())[:8],
            "paper_a": paper_a,
            "paper_b": paper_b,
            "type": rel_type,
            "note": note,
            "source": source,
            "confidence": confidence,
            "created_at": time.time(),
        }
        relations.append(rel_record)
        await self.save_relations(relations)
        return rel_record

    async def remove_paper(self, paper_id: str) -> None:
        """Remove a paper from the library index, tray, and relations, then drop local folder."""
        existing_rows, _ = await file_store.read_csv_tolerant(self.papers_csv)
        filtered = [r for r in existing_rows if r.get("paper_id") != paper_id]

        # Rewrite CSV
        lock_file = self.papers_csv.with_suffix(".csv.lock")
        path_lock = await _get_path_lock(self.papers_csv)
        async with path_lock:
            with open(lock_file, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    with tempfile.NamedTemporaryFile("w", dir=self.base_dir, delete=False, newline="", encoding="utf-8") as tf:
                        temp_path = Path(tf.name)
                        writer = csv.DictWriter(tf, fieldnames=PAPERS_CSV_HEADERS, extrasaction="ignore")
                        writer.writeheader()
                        for row in filtered:
                            writer.writerow(row)
                        tf.flush()
                        os.fsync(tf.fileno())
                    os.replace(temp_path, self.papers_csv)
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

        # Update tray
        tray = await self.get_council_tray()
        if paper_id in tray.get("paper_ids", []):
            staged = [p for p in tray.get("paper_ids", []) if p != paper_id]
            await self.update_council_tray(staged, tray.get("prompt", ""))

        # Update relations
        rels = await self.get_relations()
        updated_rels = [r for r in rels if r.get("paper_a") != paper_id and r.get("paper_b") != paper_id]
        await self.save_relations(updated_rels)

        # Remove local folder
        paper_store.remove_paper(paper_id)

    async def get_papers(self) -> list[dict[str, Any]]:
        return await self.list_papers()

    async def upsert_paper(self, record: dict[str, Any]) -> None:
        paper_rec = LibraryPaperRecord(
            paper_id=record["paper_id"],
            arxiv_id=record.get("arxiv_id", ""),
            title=record.get("title", ""),
            authors="; ".join(record.get("authors", [])) if isinstance(record.get("authors"), list) else str(record.get("authors", "")),
            published=str(record.get("year", "")),
            categories="",
            folder_path=str(self.base_dir / record["paper_id"]),
            pdf_path=str(self.base_dir / record["paper_id"] / "paper.pdf"),
            source="arxiv",
            content_hash=record.get("content_hash", ""),
            chunk_count=int(record.get("chunk_count", 0)),
        )
        await self.register_or_update_paper(paper_rec)

    async def get_collections(self) -> list[dict[str, Any]]:
        data = await file_store.read_json_safe(self.base_dir / "collections.json", fallback_default=[])
        return data if isinstance(data, list) else []

    async def save_collection(self, collection_data: dict[str, Any]) -> None:
        collections = await self.get_collections()
        updated = [c for c in collections if c.get("collection_id") != collection_data.get("collection_id")]
        updated.append(collection_data)
        await file_store.write_json_atomic(self.base_dir / "collections.json", updated)


library_store = LibraryStore()
