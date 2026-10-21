# MASTER_ARCHITECTURE_SPECIFICATION.md

| Field | Value |
| :--- | :--- |
| **Project Name** | Local Research Council (LRC) |
| **Document Version** | 1.0.0-PROD |
| **Target Hardware Profile** | Apple Silicon Mac (M5 Architecture, 24 GB Unified Memory) |
| **Execution Paradigm** | 100% On-Device / Zero-Cloud Sovereign AI Engine |
| **Backend Stack** | Python 3.11+, `asyncio`, Apple `MLX`, `PyMuPDF` (`fitz`), Embedded `Qdrant` (daemonless, local path; the vector + context store), `Ollama` / `Llama.cpp` (GBNF Constrained), plain **JSON / CSV / JSONL files** for the library, debates, and telemetry (no relational database) |
| **Frontend Stack** | Vite + React 18+, `@xyflow/react` (React Flow), Tailwind CSS, Recharts (dashboard charts), Server-Sent Events (SSE) |

---

## Table of Contents

1. [Executive Summary & System Vision](#1-executive-summary--system-vision)
2. [Hard Engineering Constraints & Operational Ceilings](#2-hard-engineering-constraints--operational-ceilings)
3. [Hardware Resource Budget (M5 24 GB Unified Memory)](#3-hardware-resource-budget-m5-24-gb-unified-memory)
4. [End-to-End System Topology](#4-end-to-end-system-topology)
5. [Deep-Dive Module Specifications](#5-deep-dive-module-specifications)
6. [Repository Directory Structure](#6-repository-directory-structure)
7. [Engineering Rules, Coding Persona & Interview Strategy](#7-engineering-rules-coding-persona--interview-strategy-cursorrules)
8. [4-Phase Execution Blueprint & Verification Gates](#8-4-phase-execution-blueprint--verification-gates)

---

## 1. Executive Summary & System Vision

The **Local Research Council (LRC)** is a production-grade, fully offline AI research copilot and multi-agent debate engine designed to help engineers and scientists dissect academic literature, uncover structural limitations, and develop a sharp research mindset.

Instead of relying on cloud APIs or fragile wrapper frameworks, LRC is engineered from the ground up to operate within the strict physical limits of an **Apple M5 24 GB Unified Memory** machine. The application operates across two core phases:

### Phase 1: Automated Ingestion, GBNF Synthesis & Dynamic Knowledge Graph

Accepts a research query or doubt, then:

- Asynchronously scrapes the top 5–10 papers from arXiv.
- Extracts high-density text sections in parallel.
- Generates deterministic structured analyses via grammar-constrained local inference.
- Reranks papers into an optimal pedagogical study order.
- Renders an interactive, sci-fi-styled knowledge graph.

### Phase 2: The Context-Partitioned Paper Council (Multi-Agent Debate)

- Pits **2 or more papers** against each other in a structured multi-agent debate: **one dedicated agent is spawned per selected paper** (default maximum 6 papers, configurable up to 10).
- Each agent represents a single paper and is strictly isolated to its own hybrid vector partition (Dense MLX + Sparse BM25 in that paper's own Qdrant collection). **Qdrant is the council's sole context provider:** agents receive grounding text only through it.
- Controlled by a single virtualized local LLM engine and a Moderator agent.
- The council debates methodologies, exposes flaws, and synthesizes novel research directions under a hard **< 2,048 token context budget**.

### Cross-Cutting Capabilities

Two capabilities span both phases and every module:

1. **Paper Library (Bookshelf UI):** A persistent, cross-session library that shows **every research paper ever used** by the system (downloaded, extracted, indexed, or debated) as a "book" on a virtual shelf. The user can open any book, create relations between books, select **two or more** of them (up to the configured Council maximum), and **send them straight to the Council** to start a debate.
2. **Full-Fidelity Observability & Failure Logging:** Every LLM call, embedding batch, retrieval query, ingestion step, state transition, and failure is captured as a structured telemetry event (tokens consumed, time to first token, total response time, memory, status, and more), persisted locally, and surfaced in a **real-time Telemetry Dashboard**. Failures are never silent: every failure is logged, classified, and visible in the UI.

---

## 2. Hard Engineering Constraints & Operational Ceilings

| Constraint Category | Specification / Enforcement Rule | Failure Threshold / Mitigation |
| :--- | :--- | :--- |
| **Cloud Dependency** | **Zero.** No OpenAI, Anthropic, or external cloud API calls. All weights, embeddings, and indices run locally. | Hard abort if any external network socket (outside `export.arxiv.org`) is opened. |
| **Unified Memory Budget** | **24.0 GB Total System RAM.** Hard runtime ceiling of **18.0 GB**; operational target of **≤ 12.0 GB**. | Background memory profiler triggers warnings at 16.0 GB and hard task termination at 18.0 GB. |
| **Model Quantization** | **4-bit Quantization (`q4_K_M`).** Uses `llama3.1:8b-instruct-q4_K_M` or `mistral:7b-instruct-q4_K_M`. | Unquantized FP16/FP32 LLM weights are prohibited. |
| **Compute Acceleration** | **Native Apple Silicon (`MLX` / Metal).** Embeddings and array math use Apple's Unified Memory architecture. | Zero redundant CPU-to-GPU tensor copies. |
| **Context Token Ceiling** | **< 2,048 Tokens** per inference call during multi-agent debates. | Knapsack priority packing drops lowest-ranked RRF chunks if prompt reaches ≥ 2,049 tokens. |
| **PDF Slicing Depth** | **First 6–8 Pages Maximum** (or structural section cutoff before References/Appendices). | Strips citations, author blocks, and bibliography noise to prevent context pollution. |
| **Output Determinism** | **100% Schema Conformance.** Uses Pydantic-derived JSON Schemas and GBNF grammars. | Zero tolerance for malformed JSON or conversational filler in structured pipelines. |
| **Data Storage (JSON/CSV)** | **No relational database** (no SQLite, no Postgres). The library, debates, and telemetry are plain **JSON / CSV / JSONL** files written through one shared `file_store.py` with atomic writes (temp file + fsync + rename), a single-writer lock, rolling backups, and a schema version in every file. The **only** database-like component is embedded Qdrant, used solely as the vector/context store. | Corrupt or unreadable file → fall back to the last good backup, log `DATA_FILE_CORRUPT`, and continue. A torn final line in an append-only file is skipped, never fatal. |
| **Vector Store Runtime** | **Daemonless Embedded Qdrant** running in-process on a local path (`QdrantClient(path="data/qdrant_db")`), one collection per paper. No Docker and no background database server. | Qdrant failure → `QDRANT_ERROR`, retry once, then pause the debate. The system never falls back to ungrounded or unfiltered context. |
| **Council Context Source** | **Qdrant is the sole context provider for the Council.** Every grounding chunk an agent sees is served by `context_provider.py` from that agent's own paper collection; agents see opponents only through public debate turns. | A prompt containing grounding text that did not come from the provider fails the budgeter's validation; citations to chunks not provided in that call are flagged as `CITATION_UNGROUNDED`. |
| **Observability Coverage** | **100%** of LLM calls, embedding batches, retrieval queries, ingestion steps, and state transitions emit a structured telemetry event with a trace ID. | Any un-instrumented model/IO call fails the CI telemetry-coverage test. |
| **Failure Logging** | **No silent failures.** Every exception, retry, timeout, schema violation, token-budget breach, partition violation, and watchdog trip is persisted with severity, error code, stack trace, and trace context. | If the primary log sink fails, fall back to append-only JSONL, then `stderr`. Logging must never crash the pipeline. |
| **Telemetry Locality** | All telemetry and library data stored **on-device** as CSV + JSONL + JSON files. No external exporters. | External telemetry exporters are prohibited and blocked by the same network guard as cloud APIs. |
| **Telemetry Overhead** | **< 1 ms** p99 per event on the hot path (async bounded queue, batched writes); **< 2%** generation-throughput impact. | Under queue pressure, drop `DEBUG` events first; `ERROR`/`FATAL` events are never dropped. |
| **Library Persistence** | Every paper touched at any point is auto-registered in the library and persists across sessions until the user explicitly removes it. | Removal requires confirmation, moves that paper's local folder to the Trash, drops its Qdrant collection, and removes it from `papers.csv`, collections, and relations. |
| **Local Paper Storage** | **All papers live in local folders** under `PAPERS_DIR` (default `data/papers/`), one folder per paper holding the PDF, metadata, sliced text, chunks, and extraction. These folders are the **single source of truth**; every pipeline stage and every debate reads from them, never from the network. | Missing or corrupt file (hash mismatch) triggers `PAPER_STORAGE_ERROR`, marks the paper `⚠ Failed`, and offers re-download or re-import. The library index (`papers.csv`) and the Qdrant collections are derived data and can be rebuilt from the folders. |
| **Council Size** | **2 to `COUNCIL_MAX_PAPERS` papers per debate** (default max **6**, configurable up to **10**). One agent per paper plus one Moderator. | Selections outside the range are rejected with an explanation. The 2,048-token ceiling holds for every call regardless of agent count. |

---

## 3. Hardware Resource Budget (M5 24 GB Unified Memory)

```text
========================================================================================
                      TOTAL APPLE SILICON M5 UNIFIED RAM: 24.0 GB
========================================================================================
  [ Core Reasoning LLM: Llama-3.1-8B-Instruct (q4_K_M) ]    -->  ~5.20 GB
  [ Native MLX Embedding Model: bge-large-en-v1.5 (FP16) ]  -->  ~1.20 GB
  [ Local Cross-Encoder Reranker: bge-reranker-large ]      -->  ~1.30 GB
  [ Active KV Cache & Working Context (< 2,048 Tokens) ]    -->  ~1.80 GB
  [ Embedded Qdrant (dense + sparse BM25 + payloads) ]      -->  ~1.50 GB
  [ Python Asyncio Core + FastAPI + Fast Tokenizer ]        -->  ~0.50 GB
----------------------------------------------------------------------------------------
  [ TARGET PEAK ENGINE FOOTPRINT ]                          --> ~11.50 GB (<= 12.0 GB)
  [ HARD ENGINE ABORT CEILING ]                             -->  18.00 GB
  [ HOST OS, WINDOW SERVER & REACT UI HEADROOM ]            --> ~6.00 - 12.50 GB Reserve
========================================================================================
```

### Budget Summary

| Component | Footprint |
| :--- | :--- |
| Core Reasoning LLM (Llama-3.1-8B-Instruct, q4_K_M) | ~5.20 GB |
| MLX Embedding Model (bge-large-en-v1.5, FP16) | ~1.20 GB |
| Cross-Encoder Reranker (bge-reranker-large) | ~1.30 GB |
| Active KV Cache & Working Context (< 2,048 tokens) | ~1.80 GB |
| Embedded Qdrant (dense + sparse BM25 vectors + chunk payloads) | ~1.50 GB |
| Python asyncio core + FastAPI + fast tokenizer | ~0.50 GB |
| **Target peak engine footprint** | **~11.50 GB (≤ 12.0 GB)** |
| **Hard engine abort ceiling** | **18.00 GB** |
| Host OS, window server & React UI headroom | ~6.00 – 12.50 GB reserve |

> **Telemetry & library memory:** The telemetry collector (bounded in-RAM ring buffer capped at ~50 MB), the CSV/JSONL telemetry files, and the JSON/CSV library registry (loaded into memory at startup) live inside the existing **~0.50 GB Python asyncio core** allocation. They add no new line item to the peak footprint.

---

## 4. End-to-End System Topology

```text
                             [ User Topic / Problem Statement ]
                                             │
                                             ▼
                       ┌───────────────────────────────────────────┐
                       │     Module 1: Async Ingestion Engine      │
                       │    (arXiv Search & Non-blocking Fetch)    │
                       └─────────────────────┬─────────────────────┘
                                             │ Parallel Download (5-10 PDFs)
                                             ▼
                       ┌───────────────────────────────────────────┐
                       │   Module 2: High-Density PDF Normalizer   │
                       │   (PyMuPDF 6-8 Page Slicing & Chunker)    │
                       └─────────────────────┬─────────────────────┘
                                             │ Clean Semantic Streams
                                             ▼
                       ┌───────────────────────────────────────────┐
                       │    Module 3: Batched GBNF Extractor       │
                       │  (Pydantic Schema + Study Order Reranker) │
                       └─────────────────────┬─────────────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
       ┌────────────────────────────┐                ┌────────────────────────────┐
       │ Module 4: Graph Synthesizer│                │ Module 5: Hybrid Retrieval │
       │ (Nodes, Edges, Study Map)  │                │ (MLX Dense + BM25 Qdrant)  │
       └──────────────┬─────────────┘                └──────────────┬─────────────┘
                      │ Deterministic Graph JSON                    │ Isolated Paper Partitions
                      ▼                                             ▼
       ┌────────────────────────────┐                ┌────────────────────────────┐
       │  Module 7: Sci-Fi Web UI   │                │ Module 6: Paper Council    │
       │ (React Flow + HUD + Stream)│◄───────────────┤ (Single-LLM State Machine) │
       └────────────────────────────┘   SSE Stream   └────────────────────────────┘
```

### Cross-Cutting Layer: Library & Telemetry

```text
   ┌────────────────────────────────────────────────────────────────────────────────┐
   │  Module 8: Paper Library (JSON/CSV) ── registers every paper at ingest time    │
   │  papers · collections · user/AI relations · debate history · Council launcher  │
   └───────────────▲───────────────────────────────────────────────┬────────────────┘
                   │ auto-register                                 │ launch(2..N papers, prompt)
   Modules 1-5 ────┘                                               ▼
                                                          Module 6: Paper Council

   ┌────────────────────────────────────────────────────────────────────────────────┐
   │  Module 9: Telemetry & Failure Log  (instruments EVERY module above)           │
   │  tracer → async collector → CSV + JSONL files → aggregates → SSE → Dashboard   │
   └────────────────────────────────────────────────────────────────────────────────┘
```

> **Note on numbering:** The topology diagram labels the ingestion engine and PDF normalizer as Modules 1 and 2, whereas Section 5 below groups the async runtime core, state machine, and profiler as "Module 1" and shifts ingestion to "Module 2." Both numbering schemes are preserved from the source specification; Section 5 is the authoritative module breakdown for implementation. Modules 8 (Library) and 9 (Telemetry) are cross-cutting additions defined in Section 5.

---

## 5. Deep-Dive Module Specifications

### Module 1: Async Runtime Core, State Machine & M5 Profiler (`app/core/`)

#### `engine.py` — Async Dispatcher

- Pure `asyncio` task orchestrator.
- Uses `asyncio.TaskGroup` and bounded `asyncio.Semaphore` pools to prevent event-loop starvation during concurrent file I/O and local model requests.

#### `state.py` — Immutable State Container

- Tracks application lifecycle:

  `IDLE` → `SCRAPING` → `EXTRACTING` → `INDEXING` → `GRAPH_READY` → `DEBATING`

- Every state transition generates a **monotonic revision hash**, enabling:
  - Deterministic state rollbacks on failure.
  - Clean event broadcasting over SSE.

#### `profiler.py` — Hardware Watchdog

- Background coroutine sampling:
  - Process Resident Set Size (RSS) via `psutil`.
  - Active Apple Metal buffers via `mlx.core.metal.get_active_memory()`.
- Sampling interval: **20 ms**.
- Emits telemetry warnings at **16 GB**.
- Triggers safe task cancellation + cache clearing (`mlx.core.metal.clear_cache()`) if unified memory hits **18 GB**.

#### `file_store.py` — Shared JSON/CSV Persistence Layer

The single gateway for every JSON/CSV/JSONL read/write in the system (library, debates, telemetry). Nothing else opens those data files directly. (Qdrant manages its own on-disk storage under `data/qdrant_db/` and is accessed only through `qdrant_store.py`.)

- **Atomic JSON writes:** write to a temp file in the same directory → `fsync` → `os.replace` onto the target, so a crash can never leave a half-written file.
- **Append-only CSV / JSONL writers:** header written once on file creation (CSV); rows appended in batches; `fsync` for `ERROR`/`FATAL` records and periodically for the rest.
- **Concurrency:** one asyncio write lock per file plus an OS-level lock file (`fcntl`) so a second process cannot corrupt a file. Read-modify-write operations on JSON documents are serialized.
- **Rolling backups:** the last 5 versions of each mutable JSON/CSV file are kept in a sibling `backups/` folder.
- **Schema versioning:** every JSON document carries `schema_version`; CSV readers key by **column name** (header row is authoritative), and columns are only ever appended, so old files stay readable.
- **Corruption handling:** parse failure → load the newest valid backup, emit `DATA_FILE_CORRUPT`, and keep running. Torn trailing lines in JSONL/CSV are skipped and counted.
- **In-memory working set:** small mutable stores (library registry, collections, relations) are loaded into memory at startup and written back through this layer on every change.
- **Scale envelope:** sized for roughly ≤ 1,000 papers and ≤ ~1M retained telemetry rows. Daily rotation and optional gzip of old telemetry keep file sizes bounded.

---

### Module 2: Async Ingestion & High-Density PDF Slicer (`app/backend/ingest/`)

#### `arxiv_client.py` — Non-Blocking Scraper

- Queries the arXiv API using `asyncio.to_thread` wrappers around the `arxiv` SDK.
- Fetches the top **5–10 papers** by relevance.
- Checks the local paper folders (`data/papers/<paper_id>/`, see Module 8) before downloading anything.
- Streams missing PDF binaries asynchronously **directly into the paper's local folder** (written atomically: temp file, integrity check, rename).
- After download, the network is never needed again for that paper.

#### `extractor.py` — High-Density Slicer

- Uses PyMuPDF (`fitz`) to extract text from the **first 6–8 pages**, capturing:
  - Abstract
  - Introduction
  - Methodology
  - Architecture
  - Core Results
- Strips, via regex boundaries:
  - Reference lists
  - Appendix dumps
  - Headers/footers
  - Broken LaTeX ligatures

#### `chunker.py` — Token-Exact Structural Chunker

- Splits normalized text by section headings into sliding windows of **256 to 512 tokens** with a **10% token overlap** (verified via local `tiktoken` / HuggingFace `tokenizers`).
- Attaches metadata to every chunk:
  - `paper_id`
  - `section_title`
  - `chunk_index`

#### `batcher.py` — Micro-Batch Stream Aggregator

- Aggregates chunk streams into micro-batches for downstream processing.

---

### Module 3: Batched GBNF Structured Extractor & Pedagogical Reranker (`app/backend/extraction/`)

#### `schemas.py` — Strict Pydantic Contracts

- Enforces exact JSON grammar rules inside Ollama/Llama.cpp:
  - `format=Schema.model_json_schema()`
  - `temperature=0.0`

**Per-Paper Extracted Fields (`PaperExtractionSchema`) — 9 fields:**

| # | Field | Description |
| :-: | :--- | :--- |
| 1 | `tldr` | Single-sentence, high-impact technical summary. |
| 2 | `problem_statement` | Core bottleneck or theoretical limitation addressed. |
| 3 | `methodology` | Underlying architecture, mathematical formulation, or algorithmic contribution. |
| 4 | `key_results` | Bullet points of quantitative benchmarks, ablation outcomes, and empirical gains. |
| 5 | `why_it_matters` | Strategic importance of the paper to the broader field. |
| 6 | `audience` | Primary technical persona who benefits most (e.g., Applied RL Researchers, Systems Infra Engineers). |
| 7 | `original_abstract` | Unmodified abstract text from arXiv metadata. |
| 8 | `research_gaps_identified` | Explicit limitations and boundary conditions admitted by the authors. |
| 9 | `ai_suggested_gaps` | Novel criticisms, unaddressed edge cases, hardware scaling bottlenecks, or methodological flaws synthesized by the local LLM. |

#### `batch_processor.py` — Batched Inference & Pedagogical Reranker

- Processes paper extractions in **concurrent micro-batches** via `httpx.AsyncClient` to maximize local GPU utilization without exhausting KV-cache memory.
- **Study Order Reranker:**
  - Evaluates all extracted paper profiles.
  - Orders them into a sequential Curriculum / Reading Path:
    **foundational/prerequisite concepts → core architectural shifts → state-of-the-art optimizations**.
  - Outputs a rationale for each paper's rank.

---

### Module 4: Dynamic Mind Map & Curriculum Synthesizer (`app/backend/graph/`)

#### `mindmap_synthesizer.py`

Aggregates the extracted schemas across all 5–10 papers and prompts the local LLM (via GBNF schema) to construct a multi-layered knowledge graph containing:

| Element | Description |
| :--- | :--- |
| **Paper Nodes** | The downloaded papers, color-coded by study order priority. |
| **Study Topic Nodes** | Core prerequisite concepts required to understand the papers. |
| **Related Field Nodes** | Adjacent sub-fields or mathematical domains to explore next. |
| **Typed Relational Edges** | Directed edges linking papers and concepts with explicit semantic labels and confidence weights. |

- **Edge labels:** `extends`, `contradicts`, `prerequisite_for`, `shares_benchmark`, `optimizes`.
- **Confidence weights:** 0.0 → 1.0, filtered by `MINDMAP_EDGE_WEIGHT_MIN = 0.35`.

---

### Module 5: MLX Hybrid Retrieval & Context Partitioning (`app/backend/retrieval/`)

#### `mlx_embed.py` — Native Apple Silicon Embedder

- Runs `bge-large-en-v1.5` natively on Apple Silicon via `mlx-embeddings` in batched arrays.
- Throughput: **≥ 120 chunks/sec**.
- Produces **1024-dimensional normalized dense vectors** directly in unified memory.

#### `qdrant_store.py` & `partition_manager.py` — Qdrant Collections & Isolated Partitions

- Initializes a local, on-disk, in-process Qdrant client: `QdrantClient(path="data/qdrant_db")`. No server, no Docker.
- **One collection per paper** (name derived from the sanitized `paper_id`, e.g. `paper__2401_01234v2`), so isolation is structural and removing a paper is a single collection drop.
- **Collection schema:**
  - Named vectors: `dense` (1024-dim, cosine, produced by the MLX embedder) and `sparse` (BM25 term weights, IDF modifier).
  - Point ID = `chunk_index`; **payload** = `paper_id`, `section_title`, `chunk_index`, `text`, `token_count`.
  - Storing chunk text in the payload lets Qdrant return ready-to-pack grounding text with no second lookup.
- **Writes:** chunks are embedded in batches and upserted in batches right after extraction; `manifest.json` records embedding model, dimension, and expected point count so a stale or incomplete collection is detected and rebuilt from `chunks.jsonl`.
- Enforces strict **Context Partitioning:**
  - `partition_manager.py` hands each advocate a `PaperIndexHandle` bound to **exactly one** collection. The handle exposes no way to query any other paper.
  - **Defense in depth:** every query also applies the payload filter `paper_id == P`.
  - An attempt to open a handle outside the agent's assignment raises `PARTITION_VIOLATION` and is logged.
  - The Moderator has no Qdrant access; it works only from agent position cards and debate history.
- **Deployment note:** embedded (local-path) mode serves each collection from process memory with exact vector search and persists it under `data/qdrant_db/`. This is ample for the target scale (≤ ~10,000 chunks, 6–8 pages per paper) and the directory is opened by one process at a time, which matches the single FastAPI process. If the corpus outgrows this, a config switch (`QDRANT_MODE=server`) can point the same code at a Qdrant binary on `localhost`, which adds HNSW indexing and memory-mapped storage while remaining fully local. Qdrant's on-disk files are managed by Qdrant and must not be edited by hand.

#### `hybrid_search.py` — Dense + Sparse BM25 + RRF + Cross-Encoder

- Executes **parallel** dense vector search and sparse BM25 keyword search against the agent's own Qdrant collection (exact search in embedded mode, HNSW in server mode); BM25 is crucial for exact variable names, theorem numbers, and loss equation terms.
- Merges results using **Reciprocal Rank Fusion (RRF):**

$$
RRF(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{60 + r_m(d)}
$$

- Applies a local cross-encoder reranker (`bge-reranker-large`) on the top candidates to yield the final high-precision grounding chunks in **< 40 ms**.

#### `context_provider.py` — Qdrant as the Council's Context Provider

The single entry point through which the Council obtains grounding text: `provide(debate_id, agent_id, query_text, token_budget=1024) → ContextBundle`.

1. **Resolve** the speaking agent's `PaperIndexHandle` (its one Qdrant collection).
2. **Build the query** from the debate prompt, the speaker's assigned task for this turn (e.g., "challenge Paper X on scaling"), and the latest claim being answered (taken from the public debate history or position cards).
3. **Embed** the query with the MLX embedder (cached per debate by query hash).
4. **Retrieve** in parallel from the collection: dense and sparse (BM25) searches with the `paper_id` filter.
5. **Fuse** with RRF, then **rerank** with the cross-encoder.
6. **Pack** with the knapsack packer into the 1,024-token RAG compartment, dropping the lowest-ranked chunks that do not fit.
7. **Return** a `ContextBundle`: ordered chunks, each with a citation tag such as `[P2 §Methodology #14]`, its score, and its token count, plus the list of dropped chunks.
8. **Record:** emit a retrieval telemetry event and write the chunk IDs into the turn's transcript record, so every claim in a debate can be audited back to the exact chunks the agent was shown.

Rules:

- **Isolation of evidence:** an agent never receives chunks from an opponent's paper; it learns about opponents only from their public turns in the debate history.
- **Citation validation:** after each generation, every citation tag in the output is checked against the chunk IDs supplied in that call. Citations to unsupplied chunks are logged as `CITATION_UNGROUNDED` (WARNING) and surfaced to the Moderator, which may intervene.
- **Failure policy:** on a Qdrant error the provider retries once, then pauses the debate and logs `QDRANT_ERROR`; it never proceeds with empty, unfiltered, or cross-paper context.
- **Caching:** query embeddings and results are cached per `(debate_id, agent_id, query_hash)` to avoid redundant work on repeated turns.

---

### Module 6: The Paper Council — Multi-Agent Debate & Token Budgeter (`app/backend/agents/`)

#### `turn_manager.py` — Single-Engine Virtualized Multi-Agent FSM

Avoids loading multiple LLMs into memory. Uses **one local 8B instance** and swaps persona system prompts, retrieval partitions, and conversation states across sequential turns.

**Dynamic agent roster (N papers → N advocates + 1 Moderator):**

| Agent | Role |
| :--- | :--- |
| **Paper Advocate #i** (one per selected paper, `advocate:<paper_id>`) | Defends its own paper's methodology and empirical results using strictly cited evidence from its own vector partition; challenges methodological flaws or scaling assumptions in the other papers; proposes alternative architectural approaches. Persona is generated from the paper's extraction (TLDR, methodology, key results, admitted gaps) by `agent_factory.py`. |
| **Moderator / Guiding Agent** | Monitors the debate trajectory after each round. Intervenes if agents hallucinate outside their papers, loop on minor points, or drift off-topic. Chooses who speaks next and whom they challenge. Synthesizes the final productive consensus report comparing trade-offs and proposing hybrid research directions. |

#### `agent_factory.py` — Dynamic Agent Spawning

- Given the selected `paper_ids`, creates one advocate per paper with a unique agent ID, display name (short paper handle), color slot, persona system prompt (fitted into the 256-token system compartment), and a locked retrieval partition.
- Agents are **virtual**: they are prompt + partition + position-card state, not separate model instances. Adding more papers adds **no model memory**; only one 8B model is ever loaded and only one prompt is in flight at a time.
- Agent and Moderator identities are written to the `participants` list in the debate's `debate.json` and emitted as `agent.spawned` telemetry events.

#### N-Agent Turn Scheduling

| Phase | Behavior |
| :--- | :--- |
| **1. Opening statements** | Each advocate presents its paper's position in turn, ordered by the pedagogical study rank (foundational papers first). |
| **2. Cross-examination rounds** | For each round, the Moderator assigns each speaker a **target** paper to challenge. Targets are chosen preferentially along `contradicts`, `extends`, `shares_benchmark`, and user-defined relations, then by least-previously-challenged pairs, so that for N > 3 the debate does not require every agent to answer every other agent. |
| **3. Moderator checkpoint** | After every round (or every `ceil(N/2)` turns for N > 4), the Moderator reviews drift, loops, and out-of-paper claims, and may redirect or re-assign targets. |
| **4. Closing positions** | Each advocate states a final one-paragraph position. |
| **5. Synthesis** | Moderator synthesis (hierarchical for N > 4, see below). |

- Default rounds: 3 for N ≤ 3, 2 for N > 3 (configurable `COUNCIL_ROUNDS`). Total LLM calls grow roughly linearly with N; the UI shows an **estimated duration** before launch, derived from historical tokens/sec in telemetry.

#### Hierarchical Synthesis (N > 4)

- Moderator groups papers into clusters of at most 3 (using relations, shared benchmarks, and similar methodology).
- **Stage 1:** one synthesis call per cluster from that cluster's position cards and recent turns.
- **Stage 2:** a final consensus call over the cluster syntheses, producing the trade-off matrix and hybrid research directions.
- Every call in both stages stays within the 2,048-token ceiling.

#### `token_budget.py` & `compression.py` — Hard < 2,048 Token Budgeter

Every prompt assembled for the local LLM is strictly validated to remain **≤ 2,048 tokens** across three fixed compartments:

| Compartment | Budget | Behavior |
| :--- | :-: | :--- |
| **System Persona & Debate Rules** | 256 tokens | Fixed ceiling. |
| **Partitioned RAG Grounding Context** | 1,024 tokens | Knapsack priority packer inserts top RRF chunks sequentially and drops lower-ranked chunks the moment adding a chunk would exceed 1,024 tokens. |
| **Shared Debate History Memory** | 768 tokens | Split into **agent position cards** (up to 384 tokens total) and a **recent-turns FIFO window** (remaining tokens). When history approaches 768 tokens, `compression.py` asynchronously triggers an abstractive compaction pass that summarizes prior debate rounds into a dense factual delta. |

**Scaling the budget to N agents (the 2,048-token ceiling is unchanged):**

- Each agent maintains a **position card**: a compact summary of its current stance, strongest cited evidence, and open challenges.
- Per-card budget = `min(96, floor(384 / N))` tokens (e.g., 96 for N ≤ 4, 64 for N = 6, 48 for N = 8, 38 for N = 10). Cards are refreshed by `compression.py` after each agent's turn.
- Because only **one agent speaks per call**, the RAG compartment still holds chunks from that single speaker's paper partition only; a larger N never enlarges any prompt.
- The recent-turns window shrinks as N grows (384 tokens of recent turns at N ≥ 4 when cards fill their share), so compression runs more often at higher N. Compression events are logged in telemetry.

---

### Module 7: Sci-Fi Interactive Frontend & Real-Time Telemetry (`app/frontend/` & `app/api/`)

#### `app/api/stream.py` — FastAPI SSE Event Bus

Exposes REST and Server-Sent Events (SSE) endpoints streaming:

- Real-time ingestion progress
- Mind map JSON payloads
- Token-by-token agent debate streams
- Live hardware/token telemetry

#### Screen 1: New Session & Live Processing Pipeline

- Clean dark-mode command input accepting a research topic, problem statement, or technical doubt.
- Step-by-step animated terminal progress pipeline:

  `[Querying arXiv Index]` → `[Streaming PDFs to Disk]` → `[Slicing High-Density Pages]` → `[Executing Batched GBNF Extractions]` → `[Computing MLX Embeddings & Qdrant Collections]` → `[Synthesizing Knowledge Graph]`

#### Screen 2: The Sci-Fi Discovery Workspace (Split-Screen)

**Left/Center Canvas — Dynamic Sci-Fi Mind Map (`@xyflow/react`):**

- Force-directed, interactive dark-mode node graph with glowing edges indicating relationship types (`contradicts`, `extends`, `prerequisite_for`).
- Displays the recommended **Pedagogical Study Order** ribbon, core **Study Topics**, and **Related Fields to Explore**.

**Right Inspector Panel — Paper Modular Tiles (HUD):**

Clicking any paper node smoothly opens a modular grid of dedicated tiles:

| Tile | Content |
| :-: | :--- |
| 1 | TLDR & Study Rank |
| 2 | Core Problem Statement |
| 3 | Methodology & Architecture |
| 4 | Key Quantitative Results |
| 5 | Why It Matters & Target Audience |
| 6 | Original arXiv Abstract |
| 7 | Author-Admitted Research Gaps |
| 8 | AI Critic Suggested Gaps & Next Steps |

#### Screen 3: The Paper Council Chamber (Live Multi-Agent Debate View)

- **Paper Selection Bar:** User selects **2 or more** ingested papers (up to `COUNCIL_MAX_PAPERS`) and sets a debate prompt/question. The bar can be **pre-filled from the Library's Council Tray** (Screen 4), including any user-defined relations between the selected papers, shown as relation chips.
- **Live Debate Terminal (dynamic layout):** Color-coded agent cards streaming live arguments, one card/lane **per selected paper** plus the Moderator.
  - 2–3 papers: split-pane layout.
  - 4+ papers: responsive grid of agent lanes with a **speaker queue** strip showing who speaks next and whom they target.
  - Each agent gets a distinct color from an 8-color palette (reused with distinguishing icons beyond 8); every card is labeled with its paper's short title.
  - Each advocate defends its own paper, challenges targeted papers from its own partition's evidence, and the Moderator injects course-corrections in real time.
  - A collapsible **position-card rail** shows each agent's current stance.
- **Real-Time Telemetry Footer:** Displays
  - Live token budget utilization, e.g.:
    `System: 210/256 | RAG Context: 940/1024 | History: 512/768 | Total: 1,662 / 2,048 Tokens`
  - Active MLX/Unified Memory footprint, e.g.: `11.4 GB / 18.0 GB Max`
  - Generation speed (tokens/sec).
  - Clicking the footer expands a **per-turn LLM call inspector** (prompt compartments, TTFT, total latency, status) and links to the full Dashboard (Screen 5).
- **Final Synthesis Banner:** Pinned bottom card rendering the Moderator's final technical verdict, comparative trade-off matrix, and actionable research synthesis.

#### Global Navigation Shell

- Persistent top navigation: **Session · Discovery · Library · Council · Dashboard**.
- **Live health LED:** green (healthy), amber (warnings, e.g. memory ≥ 16 GB or retries), red (unrecovered failure).
- **Failure badge** on the Dashboard tab showing the count of unacknowledged `ERROR`/`FATAL` events; new errors also raise a non-blocking toast with a deep link into the Failure Console.

#### Screen 4: The Paper Library (Bookshelf)

A persistent library of **all research papers used by the system at any point**, across all sessions, presented as a virtual bookshelf.

**Bookshelf visuals**

- **Books on shelves:** Each paper is rendered as a book. Toggle between **Spine view** (dense shelf) and **Cover view** (larger cards with title, authors, arXiv ID, year, TLDR).
- **Book encoding:**
  - Spine/cover color = pedagogical study-order priority (matches Mind Map color coding).
  - Spine thickness = page count or chunk count.
  - Title rendered vertically on the spine.
- **Status badges on each book:** `Ingested`, `Indexed`, `Debated N×`, and a `⚠ Failed` broken-ribbon state with a one-click **Retry** that re-runs the failed pipeline stage.
- **Shelf grouping (switchable):** by session, by topic/query, by study order, by user-defined collection, by date added, by times debated.
- **Search, filter & sort:** full-text across title/authors/abstract, filter by status/collection/category, sort by date, rank, or debate count.

**Interactions**

- **Open a book:** Opens a detail drawer containing the paper's 8 HUD tiles, original arXiv abstract, buttons to **Open PDF** and **Reveal local folder** in Finder, its debate history (with links to transcripts), and a mini telemetry panel (tokens spent, LLM calls, failures for that paper).
- **Multi-select:** Checkbox or Shift-click to select multiple books.
- **Relate mode:**
  - Select 2 or more books, then open the **Relation Composer**.
  - Pick a relation type (`extends`, `contradicts`, `compares_with`, `shares_benchmark`, `builds_on`, or custom) and add an optional note.
  - Relations are saved to the library and drawn as arcs between books on the shelf (toggleable overlay). AI-generated edges from the Mind Map appear alongside user-defined ones, visually distinguished by source (`user` vs `ai`).
- **Council Tray:** A docked tray that holds the papers staged for debate.
  - Add by drag-and-drop or an "Add to Council" button on any book.
  - **Minimum 2, maximum `COUNCIL_MAX_PAPERS`** (default 6, configurable up to 10), with a live counter (e.g., `4 / 6`). Adding beyond the limit is rejected with an explanation. Above 3 papers, the tray shows the estimated debate duration and notes that the Council will spawn one agent per paper.
  - Each staged paper shows a **readiness check** (paper folder intact, Qdrant collection present and up to date).
  - Shows the relations between the staged papers and a field for the **debate prompt/question**.
- **Send to Council:** Validates the selection, then navigates to Screen 3 and starts the debate with the chosen papers, prompt, and relation context.
- **Collections:** Create custom shelves (e.g., "Attention variants", "Quantization") and drag books into them.
- **Import PDF:** Button (and drag-and-drop) to add your own PDFs; they are copied into the local paper folders and indexed like any other paper (see `inbox_watcher.py`).
- **Remove paper:** Confirmation dialog; moves the paper's local folder to the macOS Trash, drops its Qdrant collection, and removes the paper from `papers.csv`, collections, and relations.

#### Screen 5: The Telemetry Dashboard (Everything, Live)

A full dashboard showing everything the system does, in live mode (SSE) or historical mode (time-range selector: last 5 min, 1 h, session, 24 h, all time, custom). Filterable by session, trace, agent, model, paper, and status.

| Panel | Contents |
| :--- | :--- |
| **Overview KPIs** | Total LLM calls, total tokens (prompt / completion), avg & p95 response time, avg tokens/sec, error rate, current & peak unified memory, active session state and revision hash. |
| **LLM Call Explorer** | Sortable, filterable table of every LLM call (timestamp, purpose, agent, model, prompt tokens, completion tokens, TTFT, total latency, tokens/sec, status). Click a row for a **detail drawer**: per-compartment token breakdown (system / RAG / history), chunks packed vs dropped, schema validation result, retries, memory before/after, trace link, and (if payload capture is enabled) the raw prompt and response. |
| **Token Analytics** | Stacked area chart of tokens over time by compartment; tokens by agent, by model, by paper, by session; cumulative consumption; budget-utilization gauge (x / 2,048) with per-compartment fill; knapsack drop counts; compression passes and tokens saved. |
| **Latency Analytics** | p50 / p95 / p99 for TTFT, total response time, and tokens/sec; histograms; breakdown by call purpose (extraction, rerank, mind map, debate turn, moderator, compression). |
| **Memory & Hardware** | Live RSS and Metal active memory charts with the 12 GB target, 16 GB warning, and 18 GB abort lines; peak per session; cache-clear events; KV-cache estimate. |
| **Pipeline Waterfall** | Gantt-style span view of ingestion and processing (arXiv query, per-PDF download, slicing, chunking, extraction, embedding, indexing, graph synthesis) showing time per stage and concurrency. |
| **Retrieval Analytics** | Per-query latency split by stage (dense, BM25, RRF, cross-encoder), candidate counts, chunks selected, partition used, partition-violation attempts (must be 0). |
| **Debate Analytics** | Per-debate timeline of turns, who spoke, tokens and latency per turn, moderator interventions, compression events, final synthesis. |
| **Paper Analytics** | Per-paper cost and activity: tokens consumed, LLM calls, embedding time, chunks, debates participated in, failures. |
| **Failure Console** | Live log tail and failure table filterable by severity, code, component, and trace. Grouped counts by error code, error-rate-over-time chart, recovery outcome (retried / rolled back / aborted / ignored), expandable stack traces, acknowledge/resolve actions, and a link to the related trace. |
| **Trace Explorer** | Select any trace to see the full chain of spans and events, including state transitions with revision hashes. |
| **Export** | Export any filtered view as local JSON or CSV. |

---

### Module 8: Paper Library & Council Launcher (`app/backend/library/`)

#### `paper_store.py` & `inbox_watcher.py` — Local Paper Folders (Source of Truth)

All papers used by the system are stored in **local folders** under `PAPERS_DIR` (default `data/papers/`, set in `app/config.py`). One folder per paper, named by `paper_id`:

```text
data/papers/
├── 2401.01234v2/                 # arXiv paper (folder name = arxiv_id + version)
│   ├── paper.pdf                 # Original PDF as downloaded
│   ├── metadata.json             # arXiv metadata (title, authors, abstract, categories, dates)
│   ├── sliced_text.txt           # Cleaned high-density text (first 6-8 pages, references stripped)
│   ├── chunks.jsonl              # 256-512 token chunks with paper_id / section_title / chunk_index
│   ├── extraction.json           # 9-field PaperExtractionSchema output
│   └── manifest.json             # content_hash, pipeline status per stage, timestamps, schema version
├── 2305.98765v1/
│   └── ...
├── local-3fa9c21b7d04/           # User-imported PDF (id = "local-" + first 12 chars of content hash)
│   └── ...
└── _inbox/                       # Drop any PDF here to auto-import it
```

- **Single source of truth:** every pipeline stage reads and writes through `paper_store.py`. Debates, re-indexing, the library UI, and the PDF viewer all read from these folders and **never touch the network**. Only first-time arXiv downloads use `export.arxiv.org`.
- **Atomic writes & integrity:** files are written to a temp path, hashed, then renamed. `manifest.json` records per-stage status and the PDF's `content_hash`; a hash mismatch or missing file raises `PAPER_STORAGE_ERROR`.
- **Rebuildable derived state:** `papers.csv` and the Qdrant collections are derived. A `rebuild-index` command reconstructs the registry from the folders (and `times_debated` from `data/debates/`), and re-embeds and re-upserts every paper's `chunks.jsonl` into fresh Qdrant collections, with no network. User-authored data (`collections.json`, `relations.json`) is authoritative, not derived, and is protected by rolling backups.
- **Resume & reuse:** a paper with completed stages in its manifest is never reprocessed; interrupted ingestion resumes from the last completed stage.
- **Manual import (`inbox_watcher.py`):** a file watcher on `_inbox/` (and the UI's Import PDF button) moves new PDFs into their own folder with ID `local-<hash12>`, extracts best-effort metadata (title and abstract from the first page), runs the standard slice → chunk → extract → index pipeline, and registers the book. The title can be edited in the UI.
- **Telemetry:** every file write, import, hash check, and removal emits a `paper_storage` event.

#### `library_store.py` — Persistent Library Registry (JSON/CSV)

No relational database. The library is a small set of JSON/CSV files managed through `file_store.py` and held in memory at runtime:

```text
data/library/
├── papers.csv            # Registry index: one row per paper (derived + library-level fields)
├── collections.json      # User-defined shelves and their paper IDs (authoritative)
├── relations.json        # User-defined and AI relations between papers (authoritative)
├── council_tray.json     # Currently staged paper IDs + debate prompt
└── backups/              # Rolling backups of the files above

data/debates/
├── index.csv             # One row per debate for fast listing
└── <debate_id>/
    ├── debate.json       # Papers, prompt, relation context, agents (participants), status, timestamps
    ├── transcript.jsonl  # One record per turn (agent, tokens, latency, citations, call_id)
    └── synthesis.json    # Moderator's final verdict, trade-off matrix, research directions
```

- **Auto-registration:** Every paper is registered the moment it is first touched by the ingestion pipeline and its row is updated as it progresses (downloaded → sliced → extracted → indexed → debated). A paper is never dropped from the library unless the user removes it.
- **Identity & dedup:** Papers are keyed by `arxiv_id` + `version`; a `content_hash` of the PDF detects duplicates and silent re-uploads. Re-ingesting a known paper reuses the contents of its local folder (PDF, chunks, extraction) and its existing Qdrant collection.
- **Per-paper truth vs. registry:** each paper's own `manifest.json` / `metadata.json` / `extraction.json` hold its pipeline state and content; `papers.csv` is the fast registry index for listing, search, and sorting.

**`papers.csv` columns:** `paper_id`, `arxiv_id`, `version`, `title`, `authors` (`;`-joined), `published`, `categories` (`;`-joined), `folder_path` (relative to `PAPERS_DIR`), `pdf_path`, `source` (`arxiv` or `local_import`), `content_hash`, `pages_sliced`, `chunk_count`, `ingest_status`, `indexed`, `study_rank`, `first_seen_session`, `last_used_at`, `times_debated`, `cover_seed`. (Abstract and the 9-field extraction stay in the paper's own JSON files, not in the CSV.)

| File | Contents |
| :--- | :--- |
| `collections.json` | `[{collection_id, name, paper_ids[], created_at}]` |
| `relations.json` | `[{relation_id, paper_a, paper_b, type, note, source ("user" or "ai"), confidence (AI only), created_at}]` |
| `council_tray.json` | `{paper_ids[], prompt, updated_at}` |
| `debate.json` | `{debate_id, paper_ids[], prompt, relation_context, participants[{agent_id, agent_role ("advocate" or "moderator"), paper_id, color_slot, turn_order}], status, started_at, ended_at}` |
| `debates/index.csv` | `debate_id`, `started_at`, `status`, `paper_ids` (semicolon-joined), `agent_count`, `total_tokens`, `duration_s` |

#### `relations.py` — User & AI Relations

- CRUD for user-defined relations between papers (types: `extends`, `contradicts`, `compares_with`, `shares_benchmark`, `builds_on`, custom).
- Merges with AI-generated Mind Map edges (filtered by `MINDMAP_EDGE_WEIGHT_MIN = 0.35`), preserving the `source` flag so the UI can distinguish them.

#### `council_launcher.py` — Library → Council Handoff

- Validates the selection: **between `COUNCIL_MIN_PAPERS` (2) and `COUNCIL_MAX_PAPERS` (default 6, up to 10) papers**, all with `indexed = true`, paper folders intact (manifest hash verified), Qdrant collection present with a point count equal to the chunk count, no paper in a failed state.
- Calls `agent_factory.py` to spawn one advocate per selected paper plus the Moderator, and computes an estimated debate duration from telemetry history.
- Creates a `debate_request` (papers, prompt, optional relation context) and hands it to `turn_manager.py`.
- **Relation context seeding:** User-defined relation labels and notes between the selected papers are injected into the Moderator's system prompt. This text counts against the 256-token system compartment and is truncated by the token budgeter if needed.
- Emits `debate.launched` telemetry and returns a `debate_id` that the UI uses to open Screen 3.

#### Library API Endpoints (`app/api/`)

| Endpoint | Purpose |
| :--- | :--- |
| `GET /api/library/papers` | List/search/filter/sort books |
| `GET /api/library/papers/{id}` | Book detail (tiles, debates, per-paper telemetry) |
| `DELETE /api/library/papers/{id}` | Remove paper (folder moved to Trash; Qdrant collection dropped; registry, collections, relations updated) |
| `POST /api/library/import` | Import a local PDF into the paper folders |
| `POST /api/library/rebuild-index` | Rebuild `papers.csv` and all Qdrant collections from the paper folders |
| `POST /api/library/papers/{id}/retry` | Retry failed pipeline stage |
| `GET/POST /api/library/collections` | Manage shelves |
| `GET/POST/DELETE /api/library/relations` | Manage relations |
| `PUT /api/library/council-tray` | Stage/unstage papers (enforces 2 to `COUNCIL_MAX_PAPERS`) |
| `POST /api/council/launch` | Validate and start a debate from the tray |

---

### Module 9: Telemetry, Tracing & Failure Logging (`app/backend/telemetry/`)

#### Design Principles

- **Instrument everything, centrally:** a decorator/context-manager API (`@instrument_llm`, `@instrument_retrieval`, `span("stage")`) wraps every model call, embedding batch, retrieval query, and I/O step so coverage cannot depend on developer discipline.
- **Never block the hot path:** events go into a bounded `asyncio.Queue`, are batched, and written off the critical path.
- **Never lose errors:** `ERROR` and `FATAL` events bypass drop policies and are fsynced.
- **Local only:** all data stays on-device.

#### Files

| File | Responsibility |
| :--- | :--- |
| `events.py` | Pydantic schemas for every event type |
| `tracer.py` | `session_id` / `trace_id` / `span_id` propagation via `contextvars`; instrumentation decorators |
| `collector.py` | Bounded async queue, batch writer, in-RAM ring buffer (≤ ~50 MB), SSE fan-out |
| `store.py` | Append-only CSV / JSONL writers (via `file_store.py`) with daily rotation, fsync policy, and a tolerant reader; no relational database |
| `failure_log.py` | Failure taxonomy, global handlers (asyncio loop exception handler, `sys.excepthook`, `TaskGroup` failures), retry/recovery records, sink-fallback chain |
| `aggregates.py` | Loads telemetry files into an in-memory columnar index (NumPy), builds rollups (per minute, session, model, agent, paper, call purpose) and percentiles, caches closed-day rollups as JSON, and tail-follows today's files for live mode |

#### Telemetry File Layout (CSV + JSONL, no relational database)

```text
data/telemetry/
├── llm_calls/YYYY-MM-DD.csv      # One row per LLM call (flat; per-compartment token columns)
├── retrieval/YYYY-MM-DD.csv      # One row per retrieval query (per-stage latencies)
├── embeddings/YYYY-MM-DD.csv     # One row per embedding batch
├── system/YYYY-MM-DD.csv         # Memory/hardware samples (persisted ~1 Hz; 20 ms samples live in the ring buffer)
├── events/YYYY-MM-DD.jsonl       # Nested events: spans, state transitions, ingestion, agent turns, paper storage, library actions, UI/SSE
├── failures/YYYY-MM-DD.jsonl     # Failure records and failure_ack records
├── rollups/YYYY-MM-DD.json       # Cached daily aggregates for closed days
└── payloads/<call_id>.json       # Optional raw prompt/response (off by default)
data/logs/fallback.jsonl          # Last-resort sink if the primary telemetry files cannot be written
```

- **CSV for flat, high-volume numeric records** (LLM calls, retrieval, embeddings, system): list fields are `|`-joined (e.g., `paper_ids`); prompt tokens are split into `prompt_tokens_system`, `prompt_tokens_rag`, `prompt_tokens_history`.
- **JSONL for nested or variable records** (events, failures with stack traces).
- **Failure acknowledgement** is append-only: acknowledging writes a `failure_ack` record; the current acknowledged state is computed by replay.
- **Rotation & retention:** daily files, a size cap per file (e.g., 64 MB, then suffix `.1`, `.2`), `TELEMETRY_RETENTION_DAYS` (configurable), optional gzip of closed days. Readers key by column name; columns are only ever appended.

#### Correlation Model

Every event carries: `event_id`, `timestamp` (monotonic + wall clock), `session_id`, `trace_id`, `span_id`, `parent_span_id`, `component`, `state_revision_hash`, and (when applicable) `debate_id`, `paper_ids`, `agent_role`.

#### LLM Call Record (one per inference call)

| Field | Description |
| :--- | :--- |
| `call_id`, `trace_id` | Identity and correlation |
| `purpose` | `paper_extraction`, `study_rerank`, `mindmap_synthesis`, `debate_turn`, `moderator_review`, `final_synthesis`, `history_compression` |
| `agent_role` | `advocate:<paper_id>` (one per selected paper) / `moderator` / `system` |
| `paper_ids` | Papers whose context was used |
| `model_tag`, `backend` | e.g. `llama3.1:8b-instruct-q4_K_M`, Ollama / Llama.cpp |
| `sampling` | Temperature, top-p, seed, max tokens |
| `grammar_mode` | GBNF / JSON-schema name, or none |
| `prompt_tokens` | Total plus per-compartment breakdown (system / RAG / history) |
| `completion_tokens` | Tokens generated |
| `total_tokens` | Sum, and utilization vs the 2,048 ceiling |
| `chunks_considered / packed / dropped` | Knapsack packing outcome |
| `queue_wait_ms` | Time waiting for the single engine / semaphore |
| `ttft_ms` | Time to first token |
| `total_latency_ms` | Request-to-complete time |
| `tokens_per_sec` | Generation speed |
| `schema_valid` | Pass/fail of GBNF/Pydantic validation |
| `retry_count`, `retry_reason` | Retry history |
| `status` | `ok`, `retried_ok`, `timeout`, `schema_error`, `budget_breach`, `cancelled`, `error` |
| `error_ref` | Link to failure record if any |
| `mem_before_gb`, `mem_after_gb`, `metal_active_gb` | Memory around the call |
| `payload_ref` | Optional stored prompt/response (off by default; local toggle) |

#### Other Event Types

| Event | Key Fields |
| :--- | :--- |
| **Embedding batch** | Batch size, chunk count, duration, chunks/sec, vector dim, memory delta, status |
| **Retrieval query / context provision** | Query hash, collection / `paper_id`, `debate_id`, `agent_id`, dense / BM25 / RRF / cross-encoder latency each, candidates per stage, chunk IDs returned, chunks packed vs dropped, tokens packed, total ms, partition-violation flag, citation-validation result |
| **Token budget packing** | Per-compartment fill, chunks packed/dropped, utilization %, whether compression triggered |
| **Compression pass** | Tokens before/after, latency, rounds summarized |
| **Ingestion step** | Stage (query / download / slice / chunk), paper ID, bytes, pages, chunk count, duration, cache hit/miss, status |
| **State transition** | From → to state, revision hash, trigger, duration in previous state, rollback flag |
| **Agent turn** | Debate ID, round, agent, tokens, latency, citations used, moderator intervention flag |
| **Debate summary** | Papers, rounds, total tokens, total time, interventions, final status |
| **System sample** | RSS, Metal active memory, peak, CPU, thermal state (sampled at 20 ms, downsampled for storage) |
| **UI/SSE** | Client connect/disconnect, stream lag, dropped frames |
| **Paper storage** | Operation (write / hash-check / import / remove / rebuild), paper ID, file, bytes, duration, hash match, status |
| **Agent spawned** | Debate ID, agent ID, role, paper ID, persona token count, color slot |
| **Library action** | Paper registered/removed, relation created, tray changed, debate launched |

#### Failure Log

Every failure produces a **failure record** and also appears in the dashboard's Failure Console.

| Field | Description |
| :--- | :--- |
| `failure_id`, `timestamp` | Identity |
| `severity` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `FATAL` |
| `code` | Taxonomy code (below) |
| `component` | Module/file where it occurred |
| `message`, `exception_type`, `stack_trace` | Details |
| `trace_id`, `span_id`, `call_id`, `paper_id`, `debate_id` | Correlation |
| `input_context` | Redacted/hashed summary of inputs (not raw content unless payload capture is on) |
| `retry_attempt` | Attempt number if part of a retry chain |
| `resolution` | `retried`, `rolled_back`, `aborted`, `degraded`, `ignored` |
| `recovered` | Boolean |
| `mem_snapshot`, `state_revision_hash` | System context at failure time |
| `acknowledged` | UI acknowledge flag |

**Failure taxonomy (initial set):**

| Code | Meaning |
| :--- | :--- |
| `ARXIV_FETCH_ERROR` | arXiv query or PDF download failed or timed out |
| `PDF_PARSE_ERROR` | PyMuPDF could not extract usable text |
| `CHUNKING_ERROR` | Chunk exceeded 512 tokens or structural split failed |
| `LLM_TIMEOUT` | Inference exceeded time limit |
| `LLM_SCHEMA_VIOLATION` | Output failed GBNF/Pydantic validation |
| `LLM_BACKEND_ERROR` | Ollama / Llama.cpp error or unavailable |
| `EMBED_ERROR` | MLX embedding failure |
| `QDRANT_ERROR` | Qdrant collection missing, stale, unreadable, or failed to read/write |
| `CITATION_UNGROUNDED` | An agent cited a chunk that the context provider did not supply in that call (WARNING) |
| `DATA_FILE_CORRUPT` | A JSON/CSV/JSONL file failed to parse; backup restored or torn lines skipped |
| `PARTITION_VIOLATION` | Agent attempted to query another paper's partition |
| `TOKEN_BUDGET_BREACH` | Prompt would exceed 2,048 tokens |
| `MEMORY_WARNING` / `MEMORY_CEILING` | 16 GB warning / 18 GB abort |
| `STATE_ROLLBACK` | FSM rolled back to a prior revision |
| `NETWORK_GUARD_TRIGGER` | Attempted socket outside `export.arxiv.org` |
| `SSE_DISCONNECT` | Frontend stream dropped |
| `LIBRARY_ERROR` | Library registry or launch validation failure |
| `PAPER_STORAGE_ERROR` | Paper folder file missing, corrupt (hash mismatch), unwritable, or import failed |
| `COUNCIL_SELECTION_INVALID` | Selection outside the allowed 2..N range or contains an unready paper |
| `TELEMETRY_SINK_FALLBACK` | Primary store failed; fell back to JSONL / `stderr` |
| `UNHANDLED_EXCEPTION` | Anything caught by the global handlers |

**Sink fallback chain:** primary telemetry files → `data/logs/fallback.jsonl` → `stderr`. A failure of the logger itself emits `TELEMETRY_SINK_FALLBACK` and never propagates to the pipeline.

#### Telemetry API (`app/api/`)

| Endpoint | Purpose |
| :--- | :--- |
| `GET /api/telemetry/llm-calls` | Paginated, filterable LLM call records |
| `GET /api/telemetry/llm-calls/{call_id}` | Full call detail |
| `GET /api/telemetry/aggregates` | Rollups for charts (by time bucket, model, agent, paper, purpose) |
| `GET /api/telemetry/traces/{trace_id}` | Full trace with spans and events |
| `GET /api/telemetry/failures` | Filterable failures; `POST .../{id}/ack` to acknowledge |
| `GET /api/telemetry/system` | Memory/hardware time series |
| `GET /api/telemetry/export` | JSON/CSV export of a filtered view |
| `GET /api/telemetry/stream` (SSE) | Live event stream powering dashboard and navigation badge |

---

## 6. Repository Directory Structure

```text
local-research-council/
├── .cursorrules                              # Global AI coding persona, MLX, batching & style rules
├── MASTER_ARCHITECTURE_SPECIFICATION.md      # This comprehensive master specification
├── requirements.txt                          # Pinned local dependencies (mlx, qdrant-client, numpy, pymupdf, etc.; no relational-DB packages)
├── app/
│   ├── __init__.py
│   ├── config.py                             # Pydantic BaseSettings: hardware limits, paths (PAPERS_DIR), model tags, council limits
│   ├── core/
│   │   ├── engine.py                         # Asyncio task dispatcher, semaphores, cancellation hooks
│   │   ├── state.py                          # Immutable FSM state container with revision hashes
│   │   ├── profiler.py                       # Apple Silicon Unified Memory & Metal buffer watchdog
│   │   ├── file_store.py                     # Atomic JSON/CSV/JSONL IO, locks, backups, corruption fallback
│   │   └── token_budget.py                   # Hard < 2,048 token knapsack packer & boundary validator
│   ├── backend/
│   │   ├── ingest/
│   │   │   ├── arxiv_client.py               # Async arXiv search & non-blocking PDF downloader
│   │   │   ├── extractor.py                  # PyMuPDF 6-8 page high-density slicer & regex cleaner
│   │   │   ├── chunker.py                    # Section-aware 256-512 token sliding window chunker
│   │   │   └── batcher.py                    # Micro-batch stream aggregator
│   │   ├── extraction/
│   │   │   ├── schemas.py                    # Pydantic schemas for 9-field paper extraction & reranking
│   │   │   └── batch_processor.py            # Async Ollama GBNF caller & pedagogical study reranker
│   │   ├── graph/
│   │   │   └── mindmap_synthesizer.py        # Node/Edge JSON generator for papers, topics & fields
│   │   ├── retrieval/
│   │   │   ├── mlx_embed.py                  # Native Apple Silicon MLX embedding generator
│   │   │   ├── qdrant_store.py               # Embedded Qdrant wrapper: per-paper collections (dense + sparse + payload)
│   │   │   ├── partition_manager.py          # Per-paper collection handles; structural cross-paper isolation
│   │   │   ├── hybrid_search.py              # Dense + Sparse BM25 + RRF + Cross-Encoder pipeline
│   │   │   └── context_provider.py           # Council context provider: Qdrant retrieval -> packed, cited ContextBundle
│   │   ├── agents/
│   │   │   ├── turn_manager.py               # Single-LLM multi-agent debate FSM (Advocates + Moderator)
│   │   │   ├── agent_factory.py              # Spawns one advocate per selected paper (+ Moderator)
│   │   │   └── compression.py                # Sliding-window history + position-card summarizer (< 768 tokens)
│   │   ├── library/
│   │   │   ├── paper_store.py                # Local paper folders: atomic IO, manifests, integrity, rebuild
│   │   │   ├── inbox_watcher.py              # Watches data/papers/_inbox/ and imports dropped PDFs
│   │   │   ├── library_store.py              # JSON/CSV library registry (papers.csv, collections, relations, tray)
│   │   │   ├── relations.py                  # User-defined + AI paper relations
│   │   │   └── council_launcher.py           # Validate 2..N papers, spawn agents & hand off to the Council
│   │   └── telemetry/
│   │       ├── events.py                     # Pydantic schemas for all telemetry events
│   │       ├── tracer.py                     # session/trace/span context + instrumentation decorators
│   │       ├── collector.py                  # Bounded async queue, batch writer, ring buffer, SSE fan-out
│   │       ├── store.py                      # Append-only CSV/JSONL writers, daily rotation, tolerant reader
│   │       ├── failure_log.py                # Failure taxonomy, global handlers, sink-fallback chain
│   │       └── aggregates.py                 # Rollups & percentiles for the dashboard
│   ├── api/
│   │   ├── stream.py                         # FastAPI REST + Server-Sent Events (SSE) streaming bus
│   │   ├── library_routes.py                 # Library, collections, relations, council-tray endpoints
│   │   └── telemetry_routes.py               # Telemetry query, export, failures & live SSE endpoints
│   └── frontend/                             # Vite + React + Tailwind + @xyflow/react UI
│       ├── src/
│       │   ├── components/
│       │   │   ├── CommandInput.tsx          # Topic prompt & animated ingestion progress bar
│       │   │   ├── SciFiMindMap.tsx          # Interactive React Flow canvas with glowing edges
│       │   │   ├── PaperHudTiles.tsx         # 8-tile modular inspector for paper metadata
│       │   │   ├── DebateChamber.tsx         # Live multi-agent debate stream & Moderator panel
│       │   │   ├── TelemetryBar.tsx          # Live 2,048 token gauge & M5 RAM meter (expands to call inspector)
│       │   │   ├── NavShell.tsx              # Top nav, live health LED, failure badge & toasts
│       │   │   ├── library/
│       │   │   │   ├── LibraryShelf.tsx      # Bookshelf (spine/cover views, grouping, filters)
│       │   │   │   ├── BookSpine.tsx         # Single book with status badges & relation arcs
│       │   │   │   ├── BookDetailDrawer.tsx  # Tiles, abstract, PDF link, debates, per-paper telemetry
│       │   │   │   ├── RelationComposer.tsx  # Create/edit relations between selected books
│       │   │   │   └── CouncilTray.tsx       # 2..N paper staging tray (N <= COUNCIL_MAX_PAPERS) + prompt + Send to Council
│       │   │   └── dashboard/
│       │   │       ├── DashboardPage.tsx     # Dashboard layout, time-range & filter controls
│       │   │       ├── KpiOverview.tsx       # Headline KPIs & health summary
│       │   │       ├── LlmCallExplorer.tsx   # Call table + detail drawer
│       │   │       ├── TokenAnalytics.tsx    # Token charts by compartment/agent/paper/session
│       │   │       ├── LatencyCharts.tsx     # TTFT / total latency / tokens-per-sec percentiles
│       │   │       ├── MemoryChart.tsx       # RSS & Metal memory with 12/16/18 GB lines
│       │   │       ├── PipelineWaterfall.tsx # Gantt of ingestion/processing spans
│       │   │       ├── RetrievalAnalytics.tsx# Per-stage retrieval latency & partition checks
│       │   │       ├── DebateAnalytics.tsx   # Per-debate turn timeline
│       │   │       ├── FailureConsole.tsx    # Live log tail, grouped failures, stack traces, ack
│       │   │       └── TraceExplorer.tsx     # Full trace/span/state-transition view
│       │   └── App.tsx
│       └── package.json
├── data/                                     # Local runtime data (git-ignored)
│   ├── papers/                               # PAPERS_DIR: one local folder per paper (source of truth)
│   │   ├── <arxiv_id>v<ver>/                 #   paper.pdf, metadata.json, sliced_text.txt, chunks.jsonl,
│   │   │                                     #   extraction.json, manifest.json
│   │   ├── local-<hash12>/                   #   user-imported PDFs
│   │   └── _inbox/                           #   drop PDFs here to auto-import
│   ├── qdrant_db/                            # Embedded Qdrant local store: one collection per paper (derived; rebuildable)
│   ├── library/                              # papers.csv, collections.json, relations.json, council_tray.json, backups/
│   ├── debates/                              # index.csv + one folder per debate (debate.json, transcript.jsonl, synthesis.json)
│   ├── telemetry/                            # CSV + JSONL telemetry files (llm_calls/, retrieval/, system/, events/, failures/, rollups/)
│   └── logs/                                 # fallback.jsonl (last-resort sink)
├── docs/
│   ├── TELEMETRY_AND_OBSERVABILITY.md        # Event schemas, failure taxonomy, dashboard panel catalog
│   ├── BACKEND_OPTIMIZATIONS.md              # ADR log: MLX batching, chunk math, RRF latency, RAM curves
│   └── FRONTEND_DECISIONS.md                 # ADR log: Graph layout algorithms, SSE state, UI rendering
└── tests/
    ├── mocks/                                # Pre-downloaded sample arXiv PDFs for offline testing
    ├── benchmarks/
    │   ├── test_phase1_runtime.py            # Concurrency, p99 dispatch (<1.2ms), RAM idle checks
    │   ├── test_phase2_ingest.py             # PDF throughput (<6.5s), 100% GBNF schema validation
    │   ├── test_phase3_retrieval.py          # MLX speed (>=120 chunks/s), Recall@5 (>=0.85), p95 (<40ms)
    │   ├── test_phase4_budget_and_e2e.py     # Hard <=2048 token assertion, compression speed, E2E RAM <=12GB
    │   └── test_telemetry_and_failures.py    # Event coverage, overhead, reconciliation, injected-failure capture
    └── e2e/
        ├── test_user_workflow.py             # Full user simulation: Query -> Graph -> 4-Turn Council Debate
        └── test_library_to_council.py        # Library -> relate -> Council Tray -> debate -> dashboard check
```

---

## 7. Engineering Rules, Coding Persona & Interview Strategy (`.cursorrules`)

To maximize hiring signal during technical interviews that request exported AI coding transcripts (e.g., Cursor / Claude Code `/export` sessions), development strictly follows these operational rules:

1. **Architecture-First Prompting:** Every coding session begins by referencing `@MASTER_ARCHITECTURE_SPECIFICATION.md` and enforcing hardware/token bounds before generating implementation code.
2. **Batching & Parallelism by Default:** Never execute LLM calls or embedding passes inside sequential `for` loops. Always batch array inputs for MLX and use `asyncio.gather` with bounded semaphores for concurrent I/O.
3. **Living Architecture Decision Records (ADRs):** Every major backend optimization is logged in `docs/BACKEND_OPTIMIZATIONS.md` and every UI state/rendering decision is logged in `docs/FRONTEND_DECISIONS.md`, so reviewers can audit engineering decisions without reading raw source code.
4. **End-to-End User Emulation Testing:** Rather than isolated unit tests, every milestone requires automated benchmark scripts simulating real user flows and verifying latency, Recall@K, schema determinism, and memory ceilings.
5. **Instrument First, Never Silent:** No model call, retrieval query, or I/O step ships without telemetry instrumentation, and no `except` block may swallow an error without emitting a failure record. Telemetry schemas and the failure taxonomy are documented in `docs/TELEMETRY_AND_OBSERVABILITY.md`.

---

## 8. 4-Phase Execution Blueprint & Verification Gates

### Phase 1: Async Core, Deterministic State & M5 Hardware Profiler

**Build:**

- `app/core/engine.py`
- `app/core/state.py`
- `app/core/profiler.py`
- `app/core/file_store.py` (atomic JSON/CSV/JSONL persistence used by everything below)
- `app/config.py`
- `app/backend/telemetry/` (`events.py`, `tracer.py`, `collector.py`, `store.py`, `failure_log.py`) so all later modules are instrumented from day one
- Initialize `docs/BACKEND_OPTIMIZATIONS.md` and `docs/TELEMETRY_AND_OBSERVABILITY.md`

**Verification Gate (`test_phase1_runtime.py`):**

- [ ] 100 concurrent async state transitions under `Semaphore(10)` with **0 dropped tasks**.
- [ ] p99 state dispatch latency **< 1.2 ms**.
- [ ] Baseline idle footprint **< 250 MB** Unified RAM.
- [ ] Simulated failure rollback **< 5 ms**.
- [ ] Telemetry collector sustains **≥ 10,000 events/sec** with **0 dropped `ERROR`/`FATAL` events**; hot-path overhead **< 1 ms p99**.
- [ ] Injected primary-sink failure falls back to `data/logs/fallback.jsonl` with **0 lost events** and emits `TELEMETRY_SINK_FALLBACK`.
- [ ] **File-store durability:** killing the process mid-write never leaves a corrupt JSON file; a deliberately corrupted file is restored from backup with `DATA_FILE_CORRUPT` logged; 100 concurrent read-modify-write updates lose **0 updates**; a torn last line in a CSV/JSONL file is skipped without error.
- [ ] Unhandled exceptions in tasks and `TaskGroup` are captured as `UNHANDLED_EXCEPTION` records with stack traces.

---

### Phase 2: Async arXiv Ingestion, High-Density Slicing & Batched GBNF Extraction

**Build:**

- `arxiv_client.py`
- `extractor.py`
- `chunker.py`
- `batcher.py`
- `schemas.py`
- `batch_processor.py` (including the 9-field paper extraction and pedagogical study-order reranker)
- `app/backend/library/paper_store.py`, `inbox_watcher.py`, and `library_store.py` (local paper folders as source of truth; auto-registration of every ingested paper) with LLM-call telemetry wired into extraction

**Verification Gate (`test_phase2_ingest.py`):**

- [ ] Download, slice (first 6–8 pages), and chunk 5 papers in **< 6.5 seconds**.
- [ ] 100% of chunks **≤ 512 tokens**; **0 leaked file descriptors**.
- [ ] **100% GBNF JSON schema validity** across 50 test runs with **0 parsing failures**.
- [ ] Every ingested paper has a complete local folder (`paper.pdf`, `metadata.json`, `sliced_text.txt`, `chunks.jsonl`, `extraction.json`, `manifest.json`) written atomically; an interrupted run resumes from the last completed stage; a PDF dropped in `_inbox/` is imported and indexed as `local-<hash12>`.
- [ ] **100% of papers touched** are registered in the library with correct status; re-ingesting a known paper dedupes by `arxiv_id` + version / `content_hash`.
- [ ] **100% of extraction LLM calls** produce a complete LLM call record (tokens, TTFT, latency, status).
- [ ] Injected arXiv failure and corrupt-PDF cases each produce a classified failure record (`ARXIV_FETCH_ERROR`, `PDF_PARSE_ERROR`) with trace context and surface a `⚠ Failed` state on the paper.

---

### Phase 3: MLX Hybrid Indexing (Qdrant), Context Partitioning, RRF Reranking & Council Context Provider

**Build:**

- `mlx_embed.py`
- `qdrant_store.py`
- `partition_manager.py`
- `hybrid_search.py`
- `context_provider.py` (Qdrant → packed, cited `ContextBundle` for the Council)

**Verification Gate (`test_phase3_retrieval.py`):**

- [ ] MLX embedding throughput **≥ 120 chunks/second** on M5 Metal cores.
- [ ] Hybrid search (Dense + BM25 + RRF) achieves **Recall@5 ≥ 0.85** and **MRR ≥ 0.78** on a 500-chunk evaluation set.
- [ ] **p95 retrieval latency < 40 ms**.
- [ ] Embedded Qdrant memory footprint **< 1.5 GB for 10,000 chunks**.
- [ ] **Strict zero cross-talk** between paper partitions; any attempted violation is logged as `PARTITION_VIOLATION`.
- [ ] Every retrieval query and embedding batch emits telemetry with per-stage latencies (dense / BM25 / RRF / cross-encoder).
- [ ] **Rebuild gate:** delete `data/library/papers.csv` and `data/qdrant_db/`, run `rebuild-index` with the network disabled, and recover the registry and every Qdrant collection from `data/papers/` (and `data/debates/`) with 0 lost papers and identical retrieval results; `collections.json` and `relations.json` remain untouched.
- [ ] **Context-provider gate:** every Council grounding chunk comes from `context_provider.py` and the speaker's own collection; each turn's chunk IDs are recorded in the transcript; injected citations to unsupplied chunks are detected and logged as `CITATION_UNGROUNDED` in 100% of test cases.
- [ ] **Qdrant-outage gate:** with Qdrant forced to fail mid-debate, the debate retries once, then pauses with a logged `QDRANT_ERROR` and generates no ungrounded turns.
- [ ] Corrupting a paper's `paper.pdf` is detected by hash check and logged as `PAPER_STORAGE_ERROR`.

---

### Phase 4: Paper Council FSM, < 2,048 Token Budgeter, Mind Map & Sci-Fi UI

**Build:**

- `token_budget.py`
- `turn_manager.py`
- `compression.py`
- `mindmap_synthesizer.py`
- `stream.py`
- `app/frontend/` (Sci-Fi Mind Map, 8-Tile Paper HUD, Live Council Debate Chamber, Telemetry Bar)
- `docs/FRONTEND_DECISIONS.md`
- `app/backend/agents/agent_factory.py` (dynamic one-agent-per-paper spawning) and N-agent turn scheduling / hierarchical synthesis in `turn_manager.py`
- `app/backend/library/` (`relations.py`, `council_launcher.py`), `app/backend/telemetry/aggregates.py`, `library_routes.py`, `telemetry_routes.py`
- Library bookshelf UI (Screen 4), Telemetry Dashboard (Screen 5), and the navigation shell with health LED and failure badge

**Verification Gate (`test_phase4_budget_and_e2e.py`, `test_telemetry_and_failures.py`, `test_library_to_council.py`):**

- [ ] **Hard Token Gate:** Across 50 simulated debate turns with overflowing retrieval candidates, total prompt tokens never exceed 2,048 (`assert prompt_tokens <= 2048`), with knapsack packing achieving **≥ 85% utilization** of the 1,024-token context slot.
- [ ] **Compression Latency:** Sliding-window history summarization completes in **< 350 ms**.
- [ ] **Full E2E System Gate:** Run query → ingest 5 arXiv papers → render Mind Map & HUD tiles → execute 4-turn multi-agent debate with Moderator synthesis → verify peak Unified Memory remains **≤ 12.0 GB** (well below the 18.0 GB abort tripwire).
- [ ] **Library → Council E2E:** relate books, stage **2 to 6** papers in the Council Tray, send to Council, and observe a debate that spawns exactly one advocate per selected paper plus the Moderator, using the selected prompt and relation context. A 7th paper (above the default max) and a single-paper selection are both rejected.
- [ ] **N-Agent Token Gate:** across debates with N = 2, 3, 4, 6 papers, every call (openings, cross-examinations, checkpoints, closings, cluster and final synthesis) has `prompt_tokens ≤ 2048`; position cards never exceed their `min(96, floor(384 / N))` budget; RAG context in each call comes only from the speaker's own paper partition (0 cross-partition chunks).
- [ ] **N-Agent Memory Gate:** peak unified memory for a 6-paper debate remains **≤ 12.0 GB** (identical single-model footprint to a 2-paper debate).
- [ ] **Local-Only Gate:** a debate on already-ingested papers completes with the network fully disabled.
- [ ] **Telemetry Reconciliation:** dashboard token totals equal the sum of stored LLM call records (0 discrepancy); every debate prompt record shows `prompt_tokens ≤ 2048` with per-compartment breakdown.
- [ ] **Failure Visibility:** every injected failure (LLM timeout, schema violation, budget breach, SSE disconnect, memory warning) appears in the Failure Console within **1 s** via SSE with the correct code, severity, and resolution.
- [ ] **Dashboard Performance:** API queries over 10,000 LLM call records return in **< 100 ms p95**; dashboard initial render < 1 s.

---

## Appendix: Consolidated Quantitative Targets

| Metric | Target |
| :--- | :--- |
| Peak engine memory (target) | ≤ 12.0 GB (~11.5 GB budgeted) |
| Memory warning threshold | 16.0 GB |
| Memory hard abort | 18.0 GB |
| Profiler sampling interval | 20 ms |
| Prompt token ceiling | ≤ 2,048 (system 256 / RAG 1,024 / history 768) |
| Knapsack utilization of RAG slot | ≥ 85% |
| Chunk size / overlap | 256–512 tokens / 10% |
| PDF slice depth | First 6–8 pages |
| Papers per session | 5–10 ingested; 2 to `COUNCIL_MAX_PAPERS` per debate (default 6, up to 10) |
| Mind map edge weight minimum | 0.35 |
| RRF constant | k = 60 |
| MLX embedding throughput | ≥ 120 chunks/sec |
| Embedding dimension | 1024 |
| Recall@5 / MRR | ≥ 0.85 / ≥ 0.78 |
| Retrieval p95 latency | < 40 ms |
| Qdrant footprint (10k chunks) | < 1.5 GB |
| Data stores | Embedded Qdrant (vectors / Council context only); JSON / CSV / JSONL files for library, debates, telemetry; no relational DB |
| Council grounding source | 100% of grounding chunks via Qdrant `context_provider.py` |
| File-store write-loss under 100 concurrent updates | 0 lost updates |
| p99 state dispatch latency | < 1.2 ms |
| Idle footprint | < 250 MB |
| Failure rollback | < 5 ms |
| 5-paper ingest (download + slice + chunk) | < 6.5 s |
| History compression latency | < 350 ms |
| GBNF schema validity | 100% over 50 runs |
| Telemetry hot-path overhead | < 1 ms p99 per event; < 2% generation-throughput impact |
| Telemetry collector throughput | ≥ 10,000 events/sec, 0 dropped `ERROR`/`FATAL` |
| Telemetry in-RAM ring buffer | ≤ ~50 MB (within the 0.50 GB core allocation) |
| Telemetry reconciliation error | 0 tokens discrepancy vs stored call records |
| Failure surfacing latency (to UI) | < 1 s |
| Dashboard API query (10k call records) | < 100 ms p95 |
| Council Tray selection | 2 to `COUNCIL_MAX_PAPERS` papers (default 6, configurable up to 10) |
| Agents per debate | N advocates (one per paper) + 1 Moderator, one LLM instance |
| Position card budget | `min(96, floor(384 / N))` tokens per agent |
| Paper storage | One local folder per paper under `PAPERS_DIR` (`data/papers/`); source of truth, rebuildable index |
| Library coverage | 100% of papers touched are registered |
