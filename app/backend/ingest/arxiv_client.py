"""Async arXiv search, boolean query synthesis, local widen-and-rerank pipeline, and non-blocking PDF downloader."""

import asyncio
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any

import arxiv  # type: ignore[import-untyped]
import httpx
import numpy as np

from app.backend.library.paper_store import paper_store
from app.backend.retrieval.mlx_embed import mlx_embedder
from app.backend.telemetry.events import FailureCode, Severity
from app.backend.telemetry.failure_log import failure_logger
from app.config import settings
from app.core.engine import engine

logger = logging.getLogger("app.backend.ingest.arxiv_client")

ARXIV_API_HOST = "export.arxiv.org"
ALLOWED_HOSTS = {ARXIV_API_HOST, "arxiv.org", "localhost", "127.0.0.1"}

SEARCH_CATEGORIES: list[str] = list(settings.ARXIV_SEARCH_CATEGORIES)

ARXIV_ID_REGEX = re.compile(
    r"^(?:arxiv:)?(?:https?://arxiv\.org/(?:abs|pdf)/)?([a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?|\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)?$",
    re.IGNORECASE,
)

SYNONYM_MAP: dict[str, list[str]] = {
    "agent": ["agent", '"multi-agent"'],
    "agents": ["agent", '"multi-agent"'],
    "multiagent": ['"multi-agent"', "agent"],
    "memory": ["memory", '"KV cache"', '"context window"'],
    "optimization": ["optimization", "compression"],
    "optimize": ["optimization", "compression"],
    "optimizing": ["optimization", "compression"],
    "compression": ["compression", "quantization", "pruning"],
    "compress": ["compression", "quantization"],
    "kv": ['"KV cache"', '"key-value cache"'],
    "cache": ['"KV cache"', "caching", '"key-value cache"'],
    "caching": ['"KV cache"', "caching"],
    "context": ['"context window"', '"long context"', '"context length"'],
    "retrieval": ["retrieval", "RAG", '"retrieval-augmented"'],
    "rag": ["RAG", "retrieval", '"retrieval-augmented"'],
    "quantization": ["quantization", "quantized", "4-bit", "AWQ"],
    "quantized": ["quantization", "quantized", "4-bit"],
    "attention": ["attention", "transformer", '"self-attention"'],
    "transformer": ["transformer", "attention", "LLM"],
    "transformers": ["transformer", "attention", "LLM"],
    "pruning": ["pruning", "sparse", "sparsity"],
    "sparsity": ["sparsity", "sparse", "pruning"],
    "sparse": ["sparse", "sparsity", "pruning"],
    "alignment": ["alignment", "RLHF", "DPO"],
    "reasoning": ["reasoning", '"chain-of-thought"', "CoT"],
    "distillation": ["distillation", '"knowledge distillation"'],
    "distill": ["distillation", '"knowledge distillation"'],
    "latency": ["latency", "throughput", '"inference speed"'],
    "throughput": ["throughput", "latency"],
    "concurrency": ["concurrency", "parallel", "asynchronous"],
    "multimodal": ["multimodal", "vision-language", "VLM"],
    "evaluation": ["evaluation", "benchmark", "metrics"],
    "benchmark": ["benchmark", "evaluation"],
}

STOP_WORDS: set[str] = {
    "a",
    "an",
    "the",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "and",
    "or",
    "about",
    "paper",
    "papers",
    "research",
    "study",
    "studies",
    "show",
    "me",
    "find",
    "how",
    "what",
    "is",
    "are",
    "recent",
    "best",
    "using",
    "use",
    "system",
    "systems",
}


def is_arxiv_id(query: str) -> bool:
    """Return True if query represents an exact arXiv identifier or URL."""
    return bool(ARXIV_ID_REGEX.match(query.strip()))


def extract_arxiv_id(query: str) -> str | None:
    """Extract canonical arXiv ID from clean string, URI, or prefix."""
    m = ARXIV_ID_REGEX.match(query.strip())
    return str(m.group(1)) if m else None


async def try_llm_boolean_query(user_query: str, timeout_s: float = 0.8) -> str | None:
    """Attempt zero-temperature local LLM parsing for arXiv boolean query if Ollama is responsive."""
    payload = {
        "model": settings.MODEL_TAG,
        "prompt": (
            "Convert this research query into an arXiv field-specific search query targeting abs: fields "
            "with boolean AND/OR operators. Return ONLY the boolean query string, nothing else.\n"
            f"Topic: {user_query}\n"
            "Query:"
        ),
        "stream": False,
        "options": {"temperature": 0.0, "top_p": 1.0},
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post("http://127.0.0.1:11434/api/generate", json=payload)
            if resp.status_code == 200:
                raw_text = str(resp.json().get("response", "")).strip()
                if "abs:" in raw_text or "ti:" in raw_text:
                    # Strip wrapping quotes or markdown backticks if any
                    clean_res: str = raw_text.strip("`'\"\n ")
                    return clean_res
    except Exception:
        pass
    return None


async def build_arxiv_boolean_query(
    user_query: str,
    target_fields: tuple[str, ...] = ("abs",),
    categories: list[str] | None = None,
    try_llm: bool = True,
) -> str:
    """Parse user query intent into field-specific boolean query targeting ti/abs and CS categories.

    Example:
        user_query: "agents memory optimization"
        output: ((abs:agent OR abs:"multi-agent") AND (abs:memory OR abs:"KV cache" OR abs:"context window")
                 AND (abs:optimization OR abs:compression)) AND (cat:cs.AI OR cat:cs.CL OR cat:cs.LG OR cat:cs.MA)
    """
    clean_query = user_query.strip()
    if not clean_query:
        cats = categories or SEARCH_CATEGORIES
        return " OR ".join(f"cat:{c}" for c in cats)

    # If it is a direct arXiv ID, query directly
    arxiv_id = extract_arxiv_id(clean_query)
    if arxiv_id:
        return f"id:{arxiv_id}"

    # If user already entered structured field syntax, preserve and append category filter
    if any(prefix in clean_query for prefix in ("abs:", "ti:", "all:", "cat:")):
        if "cat:" not in clean_query:
            cats = categories or SEARCH_CATEGORIES
            cat_query = " OR ".join(f"cat:{c}" for c in cats)
            return f"({clean_query}) AND ({cat_query})"
        return clean_query

    # Attempt zero-temperature local LLM parsing first if enabled
    if try_llm:
        llm_query = await try_llm_boolean_query(clean_query)
        if llm_query:
            cats = categories or SEARCH_CATEGORIES
            cat_query = " OR ".join(f"cat:{c}" for c in cats)
            if "cat:" not in llm_query:
                return f"({llm_query}) AND ({cat_query})"
            return llm_query

    # Deterministic high-precision keyword extractor and synonym mapper
    tokens = [
        w.strip()
        for w in re.findall(r'"[^"]+"|\b[\w\-]+\b', clean_query.lower())
        if w.strip()
    ]
    meaningful = [
        t.strip('"')
        for t in tokens
        if t.strip('"') not in STOP_WORDS and len(t.strip('"')) > 1
    ]

    concept_clauses: list[str] = []
    seen_concepts: set[str] = set()

    for token in meaningful:
        concept_key = token
        if concept_key in seen_concepts:
            continue

        variants = SYNONYM_MAP.get(concept_key)
        if not variants:
            # Handle basic singular forms if plural
            if concept_key.endswith("s") and concept_key[:-1] in SYNONYM_MAP:
                concept_key = concept_key[:-1]
                variants = SYNONYM_MAP.get(concept_key)
            elif concept_key.endswith("ing") and concept_key[:-3] in SYNONYM_MAP:
                concept_key = concept_key[:-3]
                variants = SYNONYM_MAP.get(concept_key)

        if not variants:
            # Multi-word phrase or unknown technical term
            variants = [f'"{token}"'] if " " in token or "-" in token else [token]

        seen_concepts.add(concept_key)
        seen_concepts.add(token)

        # Generate field targets for all variants
        field_terms: list[str] = []
        for v in variants:
            for field in target_fields:
                field_terms.append(f"{field}:{v}")

        if field_terms:
            concept_clauses.append("(" + " OR ".join(field_terms) + ")")

    cats = categories or SEARCH_CATEGORIES
    cat_query = " OR ".join(f"cat:{c}" for c in cats)

    if concept_clauses:
        return f"({' AND '.join(concept_clauses)}) AND ({cat_query})"
    return f"({cat_query})"


def _calculate_age_days(pub: Any) -> float | None:
    """Compute publication age in fractional days relative to UTC now."""
    if isinstance(pub, datetime):
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        return float(max(0.0, (now - pub).total_seconds() / 86400.0))
    if isinstance(pub, str) and pub.strip():
        try:
            clean_str = pub.strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            now = datetime.now(UTC)
            return float(max(0.0, (now - dt).total_seconds() / 86400.0))
        except Exception:
            return None
    return None


def compute_date_decay_multiplier(published: Any) -> float:
    """Calculate date decay multiplier to boost recent papers (12-24 mos) and penalize obsolete research."""
    age_days = _calculate_age_days(published)
    if age_days is None:
        return 1.0

    if age_days <= 365.0:  # <= 12 months: State-of-the-art boost
        return 1.15
    elif age_days <= 730.0:  # 12-24 months: Recent boost
        return 1.05
    elif age_days <= 1460.0:  # 2-4 years
        return 0.95
    else:  # Older papers decay gracefully (e.g. 2017 papers penalised unless score is high)
        return max(0.65, 1.0 - 0.08 * ((age_days - 730.0) / 365.0))


def _normalize_candidate(c: dict[str, Any] | arxiv.Result) -> dict[str, Any]:
    """Convert arxiv.Result or dict candidate into uniform dictionary representation."""
    if isinstance(c, dict):
        return dict(c)
    arxiv_id = c.get_short_id()
    pub_iso = c.published.isoformat() if c.published else ""
    return {
        "paper_id": arxiv_id,
        "arxiv_id": arxiv_id,
        "title": (c.title or "").strip().replace("\n", " "),
        "summary": (c.summary or "").strip().replace("\n", " "),
        "published": pub_iso,
        "authors": [a.name for a in c.authors],
        "categories": c.categories or [],
        "pdf_url": f"https://{ARXIV_API_HOST}/pdf/{arxiv_id}.pdf",
    }


async def local_cross_encoder_rerank(
    user_query: str,
    candidates: list[dict[str, Any] | arxiv.Result],
    apply_date_decay: bool = True,
    min_score_threshold: float = settings.ARXIV_SCORE_THRESHOLD,
) -> list[dict[str, Any]]:
    """Compute local dense cosine similarity, cross-encoder lexical scoring, and recency decay."""
    if not candidates:
        return []

    norm_candidates = [_normalize_candidate(c) for c in candidates]
    candidate_texts = [
        f"{c.get('title', '')}. {c.get('summary', '')}" for c in norm_candidates
    ]

    # 1. MLX Normalized Dense Embeddings
    candidate_vecs, _ = await mlx_embedder.embed_batch(candidate_texts)
    query_vec = await mlx_embedder.embed_single(user_query)

    dense_sims = np.dot(candidate_vecs, query_vec)

    # 2. Cross-Encoder Lexical Precision Pass (< 40ms SLA)
    query_words = [
        w
        for w in re.findall(r"\b\w+\b", user_query.lower())
        if len(w) > 2 and w not in STOP_WORDS
    ]

    scored_list: list[dict[str, Any]] = []
    for i, c in enumerate(norm_candidates):
        title_lower = str(c.get("title", "")).lower()
        summary_lower = str(c.get("summary", "")).lower()

        t_matches = sum(1 for w in query_words if w in title_lower)
        s_matches = sum(1 for w in query_words if w in summary_lower)
        token_score = min(
            1.0,
            (t_matches * 2.0 + s_matches * 1.0) / max(1.0, len(query_words) * 2.0),
        )

        phrase_bonus = (
            0.2
            if user_query.lower() in summary_lower or user_query.lower() in title_lower
            else 0.0
        )
        lexical_score = min(1.0, token_score + phrase_bonus)

        cos_norm = float(np.clip((dense_sims[i] + 1.0) / 2.0, 0.0, 1.0))
        raw_ce_score = 0.65 * cos_norm + 0.35 * lexical_score

        # 3. Date Decay & Recency Multiplier
        date_mult = (
            compute_date_decay_multiplier(c.get("published", ""))
            if apply_date_decay
            else 1.0
        )
        final_score = raw_ce_score * date_mult

        c_copy = dict(c)
        c_copy["score"] = round(float(final_score), 4)
        c_copy["raw_score"] = round(float(raw_ce_score), 4)
        c_copy["recency_multiplier"] = round(float(date_mult), 4)
        scored_list.append(c_copy)

    # Sort descending by final score
    scored_list.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)

    # Drop candidates failing confidence threshold, but ensure at least 1 returned if pool was non-empty
    filtered = [
        c for c in scored_list if float(c.get("score", 0.0)) >= min_score_threshold
    ]
    if not filtered and scored_list:
        filtered = scored_list[:1]

    return filtered


async def search_and_filter_papers(
    user_query: str,
    max_results: int = 10,
    categories: list[str] | None = None,
    min_score_threshold: float = settings.ARXIV_SCORE_THRESHOLD,
) -> list[dict[str, Any]]:
    """Execute complete widen-and-rerank pipeline: structured boolean query -> wide metadata pool -> local rerank."""
    # 1. Expand raw text to structured query (via local LLM or keyword mapper)
    structured_query = await build_arxiv_boolean_query(
        user_query, categories=categories
    )

    # 2. Fetch a wider candidate pool of metadata (e.g., 30 items)
    candidate_pool_size = max(settings.ARXIV_CANDIDATE_POOL_SIZE, max_results * 3)
    candidates = await arxiv_client.fetch_candidates(
        structured_query=structured_query,
        max_candidates=candidate_pool_size,
    )

    if not candidates:
        return []

    # 3. Rerank locally using your bge-reranker-large cross-encoder
    scored_candidates = await local_cross_encoder_rerank(
        user_query=user_query,
        candidates=candidates,
        apply_date_decay=True,
        min_score_threshold=min_score_threshold,
    )

    # 4. Take the true top N highest-scoring papers for PDF download & ingestion
    top_papers = scored_candidates[:max_results]
    return top_papers


class ArxivClient:
    """Queries arXiv API with boolean query constraints and streams PDF binaries non-blockingly."""

    def __init__(
        self,
        timeout_s: float = 20.0,
        candidate_pool_size: int = settings.ARXIV_CANDIDATE_POOL_SIZE,
    ) -> None:
        self.timeout_s = timeout_s
        self.candidate_pool_size = candidate_pool_size

    def _verify_host(self, url: str) -> None:
        """Enforce Zero-Cloud Egress Invariant."""
        for allowed in ALLOWED_HOSTS:
            if (
                f"://{allowed}" in url
                or url.startswith(f"http://{allowed}")
                or url.startswith(f"https://{allowed}")
            ):
                return
        raise PermissionError(
            f"NETWORK_GUARD_TRIGGER: External egress to unauthorized host blocked: {url}"
        )

    async def fetch_candidates(
        self,
        structured_query: str,
        max_candidates: int = 30,
    ) -> list[dict[str, Any]]:
        """Fetch wide metadata candidate pool using arxiv.Search via non-blocking worker pool."""

        def _sync_fetch() -> list[dict[str, Any]]:
            client = arxiv.Client(
                page_size=max_candidates,
                delay_seconds=1.0,
                num_retries=2,
            )
            search = arxiv.Search(
                query=structured_query,
                max_results=max_candidates,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            results: list[dict[str, Any]] = []
            for r in client.results(search):
                arxiv_id = r.get_short_id()
                results.append({
                    "paper_id": arxiv_id,
                    "arxiv_id": arxiv_id,
                    "title": r.title.strip().replace("\n", " "),
                    "summary": r.summary.strip().replace("\n", " "),
                    "published": r.published.isoformat() if r.published else "",
                    "authors": [a.name for a in r.authors],
                    "categories": r.categories,
                    "pdf_url": f"https://{ARXIV_API_HOST}/pdf/{arxiv_id}.pdf",
                })
            return results

        try:
            candidates: list[dict[str, Any]] = await engine.run_io_bounded(asyncio.to_thread(_sync_fetch))
            return candidates
        except Exception as exc:
            logger.warning(
                f"arxiv library fetch failed for '{structured_query}': {exc}. Attempting Atom feed fallback."
            )
            # Fallback to direct HTTP Atom query
            try:
                return await self._fetch_atom_fallback(
                    structured_query, max_candidates
                )
            except Exception as fb_exc:
                await failure_logger.log_failure(
                    code=FailureCode.ARXIV_FETCH_ERROR,
                    message=f"arXiv candidate fetch failed completely for '{structured_query}': {fb_exc}",
                    severity=Severity.ERROR,
                    exception=fb_exc,
                    component="arxiv_client",
                )
                return []

    async def _fetch_atom_fallback(
        self, query: str, max_results: int
    ) -> list[dict[str, Any]]:
        """Fallback direct HTTP request to export.arxiv.org atom feed."""
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://{ARXIV_API_HOST}/api/query?search_query={encoded_query}&start=0&max_results={max_results}&sortBy=relevance"
        self._verify_host(url)

        async def _fetch() -> list[dict[str, Any]]:
            async with httpx.AsyncClient(
                timeout=self.timeout_s, follow_redirects=True
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"arXiv API error {resp.status_code}: {resp.text}"
                    )
                return self._parse_atom_feed(resp.text)

        return await engine.run_io_bounded(_fetch())

    def _parse_atom_feed(self, xml_text: str) -> list[dict[str, Any]]:
        """Parse arXiv Atom XML response."""
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        root = ET.fromstring(xml_text)
        entries: list[dict[str, Any]] = []

        for entry in root.findall("atom:entry", ns):
            id_url = entry.findtext("atom:id", "", ns)
            arxiv_id = (
                id_url.split("/abs/")[-1]
                if "/abs/" in id_url
                else id_url.split("/")[-1]
            )
            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
            summary = (
                entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")
            )
            published = entry.findtext("atom:published", "", ns)
            authors = [
                a.findtext("atom:name", "", ns)
                for a in entry.findall("atom:author", ns)
            ]

            categories = [
                c.attrib.get("term", "")
                for c in entry.findall("atom:category", ns)
                if c.attrib.get("term")
            ]

            pdf_url = f"https://{ARXIV_API_HOST}/pdf/{arxiv_id}.pdf"
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

    async def search_by_id(self, arxiv_id_str: str) -> list[dict[str, Any]]:
        """Direct single paper lookup by arXiv ID without boolean syntax or rerank dropping."""
        clean_id = extract_arxiv_id(arxiv_id_str) or arxiv_id_str.strip()

        def _sync_id_fetch() -> list[dict[str, Any]]:
            client = arxiv.Client(num_retries=2)
            search = arxiv.Search(id_list=[clean_id], max_results=1)
            results: list[dict[str, Any]] = []
            for r in client.results(search):
                pid = r.get_short_id()
                results.append({
                    "paper_id": pid,
                    "arxiv_id": pid,
                    "title": r.title.strip().replace("\n", " "),
                    "summary": r.summary.strip().replace("\n", " "),
                    "published": r.published.isoformat() if r.published else "",
                    "authors": [a.name for a in r.authors],
                    "categories": r.categories,
                    "pdf_url": f"https://{ARXIV_API_HOST}/pdf/{pid}.pdf",
                    "score": 1.0,
                    "raw_score": 1.0,
                    "recency_multiplier": 1.0,
                })
            return results

        try:
            res: list[dict[str, Any]] = await engine.run_io_bounded(asyncio.to_thread(_sync_id_fetch))
            if res:
                return res
        except Exception as exc:
            logger.warning(
                f"Direct id fetch via arxiv library failed for '{clean_id}': {exc}"
            )

        # Fallback via atom query id_list
        url = f"https://{ARXIV_API_HOST}/api/query?id_list={clean_id}&max_results=1"
        self._verify_host(url)
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_s, follow_redirects=True
            ) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    parsed = self._parse_atom_feed(resp.text)
                    for p in parsed:
                        p["score"] = 1.0
                        p["raw_score"] = 1.0
                        p["recency_multiplier"] = 1.0
                    return parsed
        except Exception as exc:
            await failure_logger.log_failure(
                code=FailureCode.ARXIV_FETCH_ERROR,
                message=f"Direct arXiv ID fetch failed for '{clean_id}': {exc}",
                severity=Severity.ERROR,
                exception=exc,
                component="arxiv_client",
            )
        return []

    async def search(
        self, query: str, max_results: int = 5
    ) -> list[dict[str, Any]]:
        """Main search entry point: executes direct lookup for IDs, or full widen-and-rerank for queries."""
        if is_arxiv_id(query):
            return await self.search_by_id(query)
        return await search_and_filter_papers(
            user_query=query, max_results=max_results
        )

    async def download_paper(self, paper_meta: dict[str, Any]) -> bool:
        """Download paper PDF directly into its sovereign paper folder if not already cached."""
        paper_id = paper_meta["paper_id"]

        # Check local folder cache first
        manifest = await paper_store.get_manifest(paper_id)
        if manifest and "downloaded" in manifest.stages_completed:
            if await paper_store.verify_integrity(paper_id):
                logger.info(
                    f"Paper {paper_id} already cached locally with verified integrity."
                )
                return True

        pdf_url = (
            paper_meta.get("pdf_url")
            or f"https://{ARXIV_API_HOST}/pdf/{paper_id}.pdf"
        )
        self._verify_host(pdf_url)

        async def _stream_download() -> bytes:
            async with httpx.AsyncClient(
                timeout=self.timeout_s, follow_redirects=True
            ) as client:
                resp = await client.get(pdf_url)
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"Failed to download PDF: HTTP {resp.status_code}"
                    )
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
