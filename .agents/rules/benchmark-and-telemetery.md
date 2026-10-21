---
trigger: model_decision
description: pply whenever writing pytest tests, benchmark scripts in tests/benchmarks/, or telemetry/failure logging in app/backend/telemetry/.
---

#Benchmarking & Telemetry Verification Rules

1. **Deterministic Offline Benchmarks:**
   - Never make live calls to `export.arxiv.org` inside `tests/benchmarks/`. Use pre-downloaded PDFs in `tests/mocks/` and an in-process mock ASGI server to isolate CPU/disk/concurrency speed from ISP latency jitter.
2. **Quantitative Assertions Only:**
   - Every benchmark test must assert hard numerical SLAs from `@MASTER_ARCHITECTURE_SPECIFICATION.md` (e.g., `assert p99_dispatch_ms < 1.2`, `assert max_prompt_tokens <= 2048`, `assert recall_at_5 >= 0.85`).
3. **Telemetry Hot-Path Isolation:**
   - Telemetry emission must never block the inference or state-transition hot path (`< 1.0 ms` p99 overhead).
   - Under queue saturation, drop `DEBUG` events first; `ERROR` and `FATAL` records must never be dropped and must flush through the fallback sink chain (`data/telemetry/failures/` -> `data/logs/fallback.jsonl` -> `stderr`).