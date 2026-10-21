"""Async GBNF-constrained batch extraction and pedagogical study order reranker."""

import json
import logging
import time
from typing import Any

import httpx
from pydantic import ValidationError

from app.backend.extraction.schemas import (
    PaperExtractionSchema,
    StudyCurriculumSchema,
    StudyRankItem,
)
from app.backend.library.paper_store import paper_store
from app.backend.telemetry.collector import telemetry_collector
from app.backend.telemetry.events import FailureCode, LLMCallRecord, Severity
from app.backend.telemetry.failure_log import failure_logger
from app.config import settings
from app.core.engine import engine

logger = logging.getLogger("app.backend.extraction.batch_processor")

MAX_SCHEMA_RETRIES = 3


class BatchExtractor:
    """Extracts 9-field technical profiles and pedagogical curricula via grammar-constrained local LLM."""

    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434/api/generate",
        model_tag: str = settings.MODEL_TAG,
        timeout_s: float = 60.0,
    ) -> None:
        self.ollama_url = ollama_url
        self.model_tag = model_tag
        self.timeout_s = timeout_s

    async def _call_ollama_json(
        self,
        prompt: str,
        json_schema: dict[str, Any],
        purpose: Any,
        paper_id: str = "",
    ) -> tuple[dict[str, Any], LLMCallRecord]:
        """Invoke local inference with temperature=0.0 and JSON schema enforcement."""
        t_start = time.perf_counter_ns()
        payload = {
            "model": self.model_tag,
            "prompt": prompt,
            "stream": False,
            "format": json_schema,
            "options": {
                "temperature": 0.0,
                "top_p": 1.0,
            },
        }

        async def _request() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(self.ollama_url, json=payload)
                if resp.status_code != 200:
                    raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
                return resp.json()  # type: ignore[no-any-return]

        raw_response: dict[str, Any] = {}
        status = "ok"
        error_msg = ""
        prompt_tokens = max(1, len(prompt.split()))
        completion_tokens = 0

        try:
            raw_response = await engine.run_inference_bounded(_request())
            response_text = raw_response.get("response", "{}")
            parsed_json = json.loads(response_text)
            completion_tokens = raw_response.get("eval_count", max(1, len(response_text.split())))
            prompt_tokens = raw_response.get("prompt_eval_count", prompt_tokens)
        except Exception as exc:
            status = "error"
            error_msg = str(exc)
            parsed_json = {}

        elapsed_ms = (time.perf_counter_ns() - t_start) / 1_000_000.0
        tokens_sec = (completion_tokens / (elapsed_ms / 1000.0)) if elapsed_ms > 0 else 0.0

        record = LLMCallRecord(
            purpose=purpose,
            paper_ids=paper_id,
            model_tag=self.model_tag,
            backend="ollama",
            sampling_temp=0.0,
            prompt_tokens_total=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            total_latency_ms=elapsed_ms,
            tokens_per_sec=tokens_sec,
            schema_valid=(status == "ok"),
            status="ok" if status == "ok" else "error",
            error_ref=error_msg,
        )
        telemetry_collector.emit_nowait(record)

        if status != "ok":
            raise RuntimeError(error_msg)

        return parsed_json, record

    async def extract_paper(
        self,
        paper_id: str,
        abstract: str,
        sliced_text: str,
        mock_fallback: PaperExtractionSchema | None = None,
    ) -> PaperExtractionSchema:
        """Extract structured 9-field profile with retries and schema validation."""
        # Check cache
        cached = await paper_store.read_extraction(paper_id)
        if cached:
            try:
                return PaperExtractionSchema.model_validate(cached)
            except ValidationError:
                pass

        if mock_fallback is not None:
            await paper_store.save_extraction(paper_id, mock_fallback.model_dump())
            return mock_fallback

        prompt = (
            f"You are a principal systems researcher. Extract this academic paper into strict JSON.\n"
            f"Original Abstract: {abstract}\n\n"
            f"High-Density Sliced Content:\n{sliced_text[:4000]}\n"
        )
        schema = PaperExtractionSchema.model_json_schema()

        last_err: Exception | None = None
        for attempt in range(1, MAX_SCHEMA_RETRIES + 1):
            try:
                data, call_rec = await self._call_ollama_json(
                    prompt=prompt,
                    json_schema=schema,
                    purpose="paper_extraction",
                    paper_id=paper_id,
                )
                extraction = PaperExtractionSchema.model_validate(data)
                await paper_store.save_extraction(paper_id, extraction.model_dump())
                return extraction
            except (ValidationError, json.JSONDecodeError, RuntimeError) as exc:
                last_err = exc
                await failure_logger.log_failure(
                    code=FailureCode.LLM_SCHEMA_VIOLATION,
                    message=f"Schema violation extracting {paper_id} (attempt {attempt}/{MAX_SCHEMA_RETRIES}): {exc}",
                    severity=Severity.WARNING if attempt < MAX_SCHEMA_RETRIES else Severity.ERROR,
                    paper_id=paper_id,
                    retry_attempt=attempt,
                    component="batch_processor",
                )

        raise RuntimeError(f"Failed extracting {paper_id} after {MAX_SCHEMA_RETRIES} attempts: {last_err}")

    async def rerank_pedagogical_study_order(
        self,
        extractions: dict[str, PaperExtractionSchema],
        mock_order: list[str] | None = None,
    ) -> StudyCurriculumSchema:
        """Order papers into optimal pedagogical study sequence: fundamentals -> core architectures -> SOTA."""
        if mock_order is not None:
            items: list[StudyRankItem] = []
            for rank, pid in enumerate(mock_order, start=1):
                ext = extractions.get(pid)
                items.append(
                    StudyRankItem(
                        paper_id=pid,
                        study_rank=rank,
                        rationale=f"Foundational step {rank}: introduces {ext.methodology if ext else pid}",
                        prerequisite_concepts=["Linear Algebra", "Transformers"] if rank > 1 else [],
                        is_foundational=(rank == 1),
                    )
                )
            curriculum = StudyCurriculumSchema(
                reading_order=items,
                pedagogical_summary="Pedagogical reading order established from fundamentals to optimizations.",
            )
            return curriculum

        paper_summaries = "\n\n".join(
            f"Paper ID: {pid}\nTLDR: {ext.tldr}\nMethodology: {ext.methodology}\nAudience: {ext.audience}"
            for pid, ext in extractions.items()
        )
        prompt = (
            f"You are a graduate research director. Sequence these papers into an optimal pedagogical study curriculum.\n"
            f"Order them: foundational/prerequisite concepts -> core architectural shifts -> state-of-the-art optimizations.\n\n"
            f"{paper_summaries}"
        )
        schema = StudyCurriculumSchema.model_json_schema()

        data, _ = await self._call_ollama_json(
            prompt=prompt,
            json_schema=schema,
            purpose="study_rerank",
        )
        return StudyCurriculumSchema.model_validate(data)


batch_extractor = BatchExtractor()
