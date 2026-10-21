# Local Research Council (LRC)

> 100% On-Device, Zero-Cloud Sovereign AI Research Copilot and Context-Partitioned Multi-Agent Debate Engine on Apple Silicon (M5 24 GB Unified Memory).

---

## Architecture & Operational Invariants

- **Hardware Profile:** Apple Silicon M5 (24.0 GB Unified RAM).
  - Target Footprint: `<= 12.0 GB`
  - Telemetry Warning Tripwire: `16.0 GB`
  - Hard Abort Ceiling: `18.0 GB` (`mlx.core.metal.clear_cache()` + task cancellation)
- **Token Ceiling:** Strict `< 2,048` prompt tokens per inference turn across three compartments:
  - `256` tokens: System Persona & Debate Rules
  - `1,024` tokens: Partitioned RAG Grounding Context (Knapsack packed by RRF/cross-encoder score)
  - `768` tokens: Shared Debate History Memory
- **Persistence:** Zero relational databases. Atomic JSON/CSV/JSONL files via `file_store.py` (`fsync` + `os.replace`, `fcntl` locks, 5 rolling backups, corruption recovery).
- **Retrieval:** Embedded Qdrant, 1 collection per paper (`paper__<sanitized_id>`), Dense MLX + Sparse BM25, RRF fusion, local cross-encoder reranking.

---

## Quickstart

```bash
# Setup environment using uv
make setup

# Run strict type checking and linting
make lint

# Run Phase 1 Verification Gates
make test-phase1
```
