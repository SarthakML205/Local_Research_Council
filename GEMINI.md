# GEMINI.md — Principal AI Systems Architecture & Execution Contract

> **Single Source of Truth:** Always read `@MASTER_ARCHITECTURE_SPECIFICATION.md` before proposing, modifying, or generating any module. Every architectural constraint, memory ceiling, and latency gate in that specification is a hard invariant.

---

## 1. System Identity & Hardware Physics (Apple M5 24 GB)

We are building the **Local Research Council (LRC)** — a 100% local, zero-cloud, multi-agent research copilot and context-partitioned debate engine running on Apple Silicon (M5, 24.0 GB Unified Memory).

### Non-Negotiable Operational Ceilings
- **Zero Cloud Egress:** Only `127.0.0.1` / `localhost` (Qdrant gRPC `6334` / HTTP `6333`, local inference) and `export.arxiv.org` are permitted. Any external WAN socket triggers `NETWORK_GUARD_TRIGGER`.
- **Unified Memory Envelope:**
  - Operational Target: `<= 12.0 GB`
  - Telemetry Warning Tripwire: `16.0 GB` (`MEMORY_WARNING`)
  - Hard Engine Abort Ceiling: `18.0 GB` (`MEMORY_CEILING` -> cancel active task group + `mlx.core.metal.clear_cache()`).
- **Hard `< 2,048` Prompt Token Budget:** Every inference call during multi-agent debates is strictly bounded to `<= 2,048` tokens across three fixed compartments:
  - `256` tokens: System Persona & Debate Rules
  - `1,024` tokens: Partitioned RAG Grounding Context (knapsack priority-packed by RRF/cross-encoder score)
  - `768` tokens: Shared Debate History (`<= 384` tokens for `N` agent position cards scaled via `min(96, floor(384 / N))` + remaining tokens for FIFO recent turns).
- **Storage Invariant:** Zero relational databases (no SQLite, no Postgres).
  - Source of truth for papers: `data/papers/<paper_id>/` managed atomically via `paper_store.py`.
  - Metadata, debates, and telemetry: CSV / JSONL / JSON managed exclusively through `app/core/file_store.py` (temp write -> `fsync` -> `os.replace`, `fcntl` + `asyncio.Lock`, 5 rolling backups).
  - Vector & Council Context Store: Containerized Rust Qdrant (`AsyncQdrantClient(prefer_grpc=True)`), one collection per paper (`paper__<sanitized_id>`).

---

## 2. Principal Engineering Code Style & Idioms

When generating or refactoring Python code in this repository, enforce Staff/Principal engineering standards:

1. **Pure Systems Python Over Wrapper Frameworks:**
   - Never import `langchain`, `llamaindex`, or `autogen`.
   - Write explicit state machines (`app/core/state.py`), bounded concurrency pools (`asyncio.TaskGroup`, `asyncio.Semaphore`), and deterministic knapsack packers in pure Python 3.11+.
2. **Strict Static Typing (`mypy --strict` compliant):**
   - Every function signature, coroutine, generator, and class attribute must carry full type annotations (`typing.Protocol`, `TypeAlias`, `Final`, `Literal`, `Annotated`).
   - Use `Pydantic v2` (`ConfigDict(frozen=True, extra="forbid", strict=True)`) for all data contracts, events, and GBNF grammar schemas.
3. **Zero Sequential I/O or Unbatched Compute:**
   - Never call `await` inside a sequential `for` loop when operations are independent; use `asyncio.TaskGroup` gated by a bounded `asyncio.Semaphore`.
   - Never embed or rerank chunks one by one; always batch contiguous arrays into Apple Metal (`mlx.core.array`).
   - Never run synchronous disk I/O (`fitz.open`, heavy JSON serialization) directly on the main event loop if it exceeds `0.5 ms`; offload CPU-bound parsing where appropriate or use atomic buffered writes.
4. **Instrument First, Never Silent (`app/backend/telemetry/`):**
   - Bare `except Exception: pass` or silent `logger.error()` calls are strictly forbidden.
   - Every exception, retry, timeout, schema failure, or partition violation must emit a typed `FailureRecord` with an explicit taxonomy code (`LLM_SCHEMA_VIOLATION`, `PARTITION_VIOLATION`, `TOKEN_BUDGET_BREACH`, etc.) and `trace_id` via `contextvars`.
   - Every LLM call, embedding batch, and Qdrant query must be wrapped with `@instrument_llm`, `@instrument_embeddings`, or `@instrument_retrieval`.

---

## 3. Verification-Driven Development ("Zero Vibe-Checks")

No module or feature is ever considered complete based on manual inspection or "it runs." Every implementation turn in Antigravity must include:

1. **Deterministic Unit & Concurrency Tests (`pytest`, `pytest-asyncio`):**
   - Verify race-free execution under `100` concurrent coroutines.
   - Verify fault injection (e.g., mid-write crash recovery in `file_store.py`, corrupt PDF hash mismatch in `paper_store.py`, Qdrant outage retry-then-pause in `context_provider.py`).
2. **Quantitative Benchmark Assertions (`tests/benchmarks/`):**
   - Assert exact p50 / p95 / p99 latencies (`time.perf_counter_ns()`), Unified Memory delta (`psutil` + `mlx.core.metal.get_active_memory()`), token counts, or retrieval `Recall@5` / `MRR`.
3. **Living Architecture Decision Records (ADRs):**
   - Whenever we make a non-trivial systems trade-off (e.g., dual-stage cross-encoder extractive history pruning vs. async LLM position-card compaction), append a concise, metric-backed ADR entry to `docs/BACKEND_OPTIMIZATIONS.md`.

---

## 4. How the AI Agent Must Respond in This Workspace

- **No Boilerplate Lectures:** Skip introductory fluff, framework comparisons, and high-level tutorials.
- **No Truncated Code:** Never output `# ... rest of implementation here` or `# TODO: implement`. Deliver complete, production-ready modules that pass linting and type-checking immediately.
- **Systems Root-Cause Diagnosis:** When debugging a failure or latency spike, analyze event-loop blocking, GIL contention, Metal buffer fragmentation, KV-cache growth, or HNSW/gRPC serialization overhead first.
- **Scope Discipline:** Prioritize backend reliability, retrieval precision, token determinism, and telemetry verification over frontend visual polish.