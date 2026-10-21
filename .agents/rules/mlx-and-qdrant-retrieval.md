---
trigger: model_decision
description: Apply whenever implementing or modifying MLX embeddings, Qdrant vector/sparse indexing, RRF hybrid search, context partitioning, or local LLM inference in app/backend/retrieval/, app/backend/extraction/, or app/core/inference.py.
---

# MLX, Local Inference & Qdrant Retrieval Rules

1. **Zero-Copy Apple Silicon (`MLX`):**
   - Keep `bge-large-en-v1.5` embedding arrays in unified memory; batch chunk inputs to maintain `>= 120 chunks/sec` throughput.
   - After heavy batch extraction or embedding bursts, check `profiler.py` pressure and invoke `mlx.core.metal.clear_cache()` if active Metal memory approaches the 16.0 GB warning line.
2. **Containerized Qdrant (`AsyncQdrantClient`):**
   - Always connect via `AsyncQdrantClient(url=settings.QDRANT_URL, prefer_grpc=True)`.
   - Maintain strict 1-collection-per-paper isolation (`paper__<sanitized_id>`) with named `dense` (1024-dim Cosine) and `sparse` (BM25 IDF) vectors.
   - Enforce defense-in-depth: even inside a single-paper collection, attach a `models.Filter` asserting `paper_id == target_paper_id`.
3. **Deterministic Structured Generation:**
   - All `extraction/` and `graph/` LLM calls must enforce `temperature=0.0` and strict Pydantic JSON schema / GBNF grammar validation.
   - On `LLM_SCHEMA_VIOLATION`, log the failure with `retry_attempt` and retry up to `MAX_SCHEMA_RETRIES = 3` before marking the paper stage failed.