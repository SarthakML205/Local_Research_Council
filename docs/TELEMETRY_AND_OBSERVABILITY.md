# TELEMETRY_AND_OBSERVABILITY.md — Observability Architecture & Failure Taxonomy

| Document Version | 1.0.0-PROD |
| :--- | :--- |
| **Storage Architecture** | Zero-DB: Daily rotated CSV (flat numeric) + JSONL (nested events & failures) |
| **Hot-Path Overhead SLA** | < 1.0 ms p99 overhead per event (< 2% throughput impact) |
| **Error Guarantee** | Zero dropped `ERROR` and `FATAL` records |
| **Fallback Sinks** | Primary FileStore -> `data/logs/fallback.jsonl` -> `stderr` |

---

## 1. Failure Taxonomy & Codes

| Failure Code | Severity | Description & Trigger Conditions |
| :--- | :--- | :--- |
| `ARXIV_FETCH_ERROR` | ERROR | arXiv API query or PDF download timed out or returned non-200. |
| `PDF_PARSE_ERROR` | ERROR | PyMuPDF text extraction failed or yielded empty text stream. |
| `CHUNKING_ERROR` | ERROR | Sliding window chunker exceeded 512 tokens or failed boundary split. |
| `LLM_TIMEOUT` | ERROR | Local Ollama / Llama.cpp inference exceeded allocated deadline. |
| `LLM_SCHEMA_VIOLATION`| WARNING/ERROR | Structured generation failed GBNF / Pydantic schema validation. |
| `LLM_BACKEND_ERROR` | FATAL | Local inference backend unavailable or crashed. |
| `EMBED_ERROR` | ERROR | MLX Apple Silicon embedding batch execution failure. |
| `QDRANT_ERROR` | ERROR | Embedded Qdrant collection missing, corrupt, or query failed. |
| `CITATION_UNGROUNDED` | WARNING | Agent cited a chunk tag not provided in its turn context bundle. |
| `DATA_FILE_CORRUPT` | WARNING/ERROR | JSON/CSV/JSONL parse failure; restored from rolling backup. |
| `PARTITION_VIOLATION` | FATAL | Council agent attempted cross-paper vector query outside its assigned handle. |
| `TOKEN_BUDGET_BREACH` | ERROR | Assembled prompt would exceed hard 2,048 token boundary. |
| `MEMORY_WARNING` | WARNING | Apple Silicon Unified Memory reached 16.0 GB tripwire. |
| `MEMORY_CEILING` | FATAL | Apple Silicon Unified Memory reached 18.0 GB hard abort ceiling. |
| `STATE_ROLLBACK` | INFO/WARNING | FSM state machine rolled back to a previous revision. |
| `NETWORK_GUARD_TRIGGER`| FATAL | Unauthorized socket opened outside `export.arxiv.org` / `localhost`. |
| `SSE_DISCONNECT` | INFO/WARNING | Real-time SSE streaming client disconnected. |
| `LIBRARY_ERROR` | ERROR | Registry index or Council staging validation failed. |
| `PAPER_STORAGE_ERROR` | ERROR | Paper folder integrity check or content hash mismatch. |
| `COUNCIL_SELECTION_INVALID` | WARNING | Council launched with < 2 or > 6 papers. |
| `TELEMETRY_SINK_FALLBACK` | FATAL | Primary telemetry store failed; switched to fallback sink. |
| `UNHANDLED_EXCEPTION` | FATAL | Trapped by global `sys.excepthook` or asyncio loop exception handler. |

---

## 2. Telemetry File Schema Specifications

### `llm_calls/YYYY-MM-DD.csv`
Captures every local LLM invocation with strict compartment token breakdown:
- `call_id`: UUID
- `purpose`: `paper_extraction`, `study_rerank`, `mindmap_synthesis`, `debate_turn`, `moderator_review`, `final_synthesis`, `history_compression`
- `prompt_tokens_system`, `prompt_tokens_rag`, `prompt_tokens_history`, `prompt_tokens_total`
- `completion_tokens`, `total_tokens`
- `chunks_considered`, `chunks_packed`, `chunks_dropped`
- `queue_wait_ms`, `ttft_ms`, `total_latency_ms`, `tokens_per_sec`
- `mem_before_gb`, `mem_after_gb`, `metal_active_gb`

### `retrieval/YYYY-MM-DD.csv`
Captures hybrid vector + keyword queries:
- Latencies: `dense_ms`, `sparse_bm25_ms`, `rrf_ms`, `cross_encoder_ms`, `total_retrieval_ms`
- Candidates: `dense_candidates`, `sparse_candidates`, `fused_candidates`, `chunks_selected`
- Partition verification: `partition_violation_attempted` (must always be 0)

### `failures/YYYY-MM-DD.jsonl`
Captures all system warnings, errors, and fatal crashes with stack traces, correlation IDs, and memory snapshots.
