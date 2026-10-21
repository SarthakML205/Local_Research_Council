.PHONY: help setup docker-up docker-down test test-phase1 test-phase2 test-phase3 test-phase4 test-telemetry test-all bench clean lint run-backend run-frontend

help:
	@echo "Local Research Council (LRC) - Development Commands"
	@echo "  make setup          - Install dependencies using uv"
	@echo "  make test-phase1    - Run Phase 1 FSM, storage & concurrency benchmarks"
	@echo "  make test-phase2    - Run Phase 2 Ingestion & extraction benchmarks"
	@echo "  make test-phase3    - Run Phase 3 Native MLX & Qdrant retrieval benchmarks"
	@echo "  make test-phase4    - Run Phase 4 Token budget & debate benchmarks"
	@echo "  make test-telemetry - Run Telemetry, zero-token audit & fault injection tests"
	@echo "  make test-all       - Run all 5 benchmark verification suites"
	@echo "  make lint           - Run strict mypy type checking and ruff"
	@echo "  make run-backend    - Start sovereign FastAPI backend on 127.0.0.1:8000"
	@echo "  make run-frontend   - Start Vite development server for Sci-Fi UI"
	@echo "  make clean          - Remove caches and temporary files"

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PYTEST ?= $(VENV)/bin/pytest
MYPY ?= $(VENV)/bin/mypy
RUFF ?= $(VENV)/bin/ruff
UVICORN ?= $(VENV)/bin/uvicorn

setup:
	uv venv --python 3.11 $(VENV)
	uv pip install -e ".[dev]" --python $(VENV)
	npm install --prefix app/frontend

docker-up:
	docker compose up -d qdrant

docker-down:
	docker compose down

test:
	$(PYTEST) -v tests/benchmarks/

test-phase1:
	$(PYTEST) -v tests/benchmarks/test_phase1_runtime.py

test-phase2:
	$(PYTEST) -v tests/benchmarks/test_phase2_ingest.py

test-phase3:
	$(PYTEST) -v tests/benchmarks/test_phase3_retrieval.py

test-phase4:
	$(PYTEST) -v tests/benchmarks/test_phase4_budget_and_e2e.py

test-telemetry:
	$(PYTEST) -v tests/benchmarks/test_telemetry_and_failures.py

test-all:
	$(PYTEST) -v tests/benchmarks/

lint:
	$(MYPY) app/ tests/
	$(RUFF) check app/ tests/

run-backend:
	$(UVICORN) app.main:app --host 127.0.0.1 --port 8000 --reload

run-frontend:
	npm run dev --prefix app/frontend

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache