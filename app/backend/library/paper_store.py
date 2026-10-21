"""Atomic paper folder store: source of truth for PDF, metadata, text, chunks, and manifests."""

import hashlib
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.backend.telemetry.events import FailureCode, Severity
from app.backend.telemetry.failure_log import failure_logger
from app.config import settings
from app.core.file_store import file_store

logger = logging.getLogger("app.backend.library.paper_store")

StageName = Literal["downloaded", "sliced", "chunked", "extracted", "indexed"]


class PaperManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    paper_id: str
    content_hash: str
    schema_version: int = 1
    stages_completed: list[StageName] = Field(default_factory=list)
    created_at_ns: int = Field(default_factory=time.perf_counter_ns)
    updated_at_ns: int = Field(default_factory=time.perf_counter_ns)
    error_state: str | None = None


class PaperStore:
    """Manages the local paper folders in PAPERS_DIR as the authoritative single source of truth."""

    def __init__(self, base_dir: Path = settings.PAPERS_DIR) -> None:
        self.base_dir = base_dir

    def sanitize_paper_id(self, paper_id: str) -> str:
        """Sanitize paper identifier for folder and collection naming."""
        clean = paper_id.replace("/", "_").replace(":", "_").replace(" ", "_")
        return clean.strip("._")

    def get_paper_folder(self, paper_id: str) -> Path:
        sanitized = self.sanitize_paper_id(paper_id)
        return self.base_dir / sanitized

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    async def init_paper_folder(
        self,
        paper_id: str,
        pdf_bytes: bytes,
        metadata: dict[str, Any],
    ) -> PaperManifest:
        """Atomically initialize a paper folder with PDF binary, metadata, and manifest."""
        folder = self.get_paper_folder(paper_id)
        folder.mkdir(parents=True, exist_ok=True)

        pdf_path = folder / "paper.pdf"
        temp_pdf = folder / "paper.pdf.tmp"

        # Write PDF atomically
        with open(temp_pdf, "wb") as f:
            f.write(pdf_bytes)
            f.flush()
        temp_pdf.replace(pdf_path)

        content_hash = self.compute_sha256(pdf_path)

        # Write metadata.json
        meta_path = folder / "metadata.json"
        await file_store.write_json_atomic(meta_path, metadata)

        # Write manifest.json
        manifest = PaperManifest(
            paper_id=paper_id,
            content_hash=content_hash,
            stages_completed=["downloaded"],
            created_at_ns=time.perf_counter_ns(),
            updated_at_ns=time.perf_counter_ns(),
        )
        await self.save_manifest(paper_id, manifest)
        return manifest

    async def get_manifest(self, paper_id: str) -> PaperManifest | None:
        folder = self.get_paper_folder(paper_id)
        manifest_path = folder / "manifest.json"
        if not manifest_path.exists():
            return None
        try:
            data = await file_store.read_json_safe(manifest_path)
            if isinstance(data, dict):
                return PaperManifest.model_validate(data)
        except Exception as exc:
            logger.error(f"Failed to read manifest for {paper_id}: {exc}")
        return None

    async def save_manifest(self, paper_id: str, manifest: PaperManifest | dict[str, Any]) -> None:
        folder = self.get_paper_folder(paper_id)
        folder.mkdir(parents=True, exist_ok=True)
        manifest_path = folder / "manifest.json"
        dumped = manifest.model_dump() if hasattr(manifest, "model_dump") else manifest
        await file_store.write_json_atomic(manifest_path, dumped)

    async def verify_integrity(self, paper_id: str) -> bool:
        """Verify that paper.pdf exists and its SHA256 hash matches the manifest."""
        folder = self.get_paper_folder(paper_id)
        manifest = await self.get_manifest(paper_id)
        pdf_path = folder / "paper.pdf"

        if not manifest or not pdf_path.exists():
            await failure_logger.log_failure(
                code=FailureCode.PAPER_STORAGE_ERROR,
                message=f"Integrity check failed: missing files for paper {paper_id}",
                paper_id=paper_id,
                severity=Severity.ERROR,
            )
            return False

        current_hash = self.compute_sha256(pdf_path)
        if current_hash != manifest.content_hash:
            await failure_logger.log_failure(
                code=FailureCode.PAPER_STORAGE_ERROR,
                message=f"Hash mismatch for paper {paper_id}: manifest={manifest.content_hash}, file={current_hash}",
                paper_id=paper_id,
                severity=Severity.ERROR,
            )
            return False
        return True

    async def mark_stage_completed(self, paper_id: str, stage: StageName) -> PaperManifest:
        """Record completed pipeline stage in manifest."""
        manifest = await self.get_manifest(paper_id)
        if not manifest:
            raise FileNotFoundError(f"Manifest missing for paper {paper_id}")

        stages = list(manifest.stages_completed)
        if stage not in stages:
            stages.append(stage)

        updated = PaperManifest(
            paper_id=manifest.paper_id,
            content_hash=manifest.content_hash,
            schema_version=manifest.schema_version,
            stages_completed=stages,
            created_at_ns=manifest.created_at_ns,
            updated_at_ns=time.perf_counter_ns(),
            error_state=None,
        )
        await self.save_manifest(paper_id, updated)
        return updated

    async def mark_stage_failed(self, paper_id: str, error_msg: str) -> None:
        manifest = await self.get_manifest(paper_id)
        if manifest:
            updated = PaperManifest(
                paper_id=manifest.paper_id,
                content_hash=manifest.content_hash,
                schema_version=manifest.schema_version,
                stages_completed=manifest.stages_completed,
                created_at_ns=manifest.created_at_ns,
                updated_at_ns=time.perf_counter_ns(),
                error_state=error_msg,
            )
            await self.save_manifest(paper_id, updated)

    async def save_sliced_text(self, paper_id: str, text: str) -> None:
        folder = self.get_paper_folder(paper_id)
        folder.mkdir(parents=True, exist_ok=True)
        txt_path = folder / "sliced_text.txt"
        tmp_path = folder / "sliced_text.txt.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
        tmp_path.replace(txt_path)
        await self.mark_stage_completed(paper_id, "sliced")

    async def save_chunks(self, paper_id: str, chunks: list[dict[str, Any]]) -> None:
        folder = self.get_paper_folder(paper_id)
        folder.mkdir(parents=True, exist_ok=True)
        chunks_path = folder / "chunks.jsonl"
        await file_store.append_jsonl(chunks_path, chunks, sync_immediately=True)
        await self.mark_stage_completed(paper_id, "chunked")

    async def save_extraction(self, paper_id: str, extraction_data: dict[str, Any]) -> None:
        folder = self.get_paper_folder(paper_id)
        folder.mkdir(parents=True, exist_ok=True)
        ext_path = folder / "extraction.json"
        await file_store.write_json_atomic(ext_path, extraction_data)
        await self.mark_stage_completed(paper_id, "extracted")

    async def read_chunks(self, paper_id: str) -> list[dict[str, Any]]:
        folder = self.get_paper_folder(paper_id)
        chunks_path = folder / "chunks.jsonl"
        records, _ = await file_store.read_jsonl_tolerant(chunks_path)
        return records

    async def read_extraction(self, paper_id: str) -> dict[str, Any] | None:
        folder = self.get_paper_folder(paper_id)
        ext_path = folder / "extraction.json"
        if not ext_path.exists():
            return None
        data = await file_store.read_json_safe(ext_path)
        return data if isinstance(data, dict) else None

    async def read_metadata(self, paper_id: str) -> dict[str, Any] | None:
        folder = self.get_paper_folder(paper_id)
        meta_path = folder / "metadata.json"
        if not meta_path.exists():
            return None
        data = await file_store.read_json_safe(meta_path)
        return data if isinstance(data, dict) else None

    async def save_metadata(self, paper_id: str, metadata: dict[str, Any]) -> None:
        folder = self.get_paper_folder(paper_id)
        folder.mkdir(parents=True, exist_ok=True)
        meta_path = folder / "metadata.json"
        await file_store.write_json_atomic(meta_path, metadata)

    async def read_manifest(self, paper_id: str) -> dict[str, Any] | None:
        manifest = await self.get_manifest(paper_id)
        return manifest.model_dump() if manifest else None

    async def save_pdf(self, paper_id: str, pdf_bytes: bytes) -> None:
        folder = self.get_paper_folder(paper_id)
        folder.mkdir(parents=True, exist_ok=True)
        pdf_path = folder / "paper.pdf"
        tmp_path = folder / "paper.pdf.tmp"
        with open(tmp_path, "wb") as f:
            f.write(pdf_bytes)
            f.flush()
        tmp_path.replace(pdf_path)

    def get_paper_dir(self, paper_id: str) -> Path:
        return self.get_paper_folder(paper_id)

    def remove_paper(self, paper_id: str) -> bool:
        """Remove paper folder to trash/delete."""
        folder = self.get_paper_folder(paper_id)
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
            return True
        return False


paper_store = PaperStore()
