.PHONY: help setup docker-up docker-down test test-phase1 bench clean lint

help:
	@echo "Local Research Council (LRC) - Development Commands"
	@echo "  make setup        - Install dependencies using uv"
	@echo "  make docker-up    - Start containerized Qdrant (gRPC 6334 / HTTP 6333)"
	@echo "  make docker-down  - Stop Qdrant container"
	@echo "  make test         - Run full pytest suite"
	@echo "  make test-phase1  - Run Phase 1 FSM & concurrency benchmarks"
	@echo "  make lint         - Run strict mypy type checking and ruff"
	@echo "  make clean        - Remove caches and temporary files"

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PYTEST ?= $(VENV)/bin/pytest
MYPY ?= $(VENV)/bin/mypy
RUFF ?= $(VENV)/bin/ruff

setup:
	uv venv --python 3.11 $(VENV)
	uv pip install -e ".[dev]" --python $(VENV)

docker-up:
	docker compose up -d qdrant

docker-down:
	docker compose down

test:
	$(PYTEST) -v tests/

test-phase1:
	$(PYTEST) -v tests/benchmarks/test_phase1_runtime.py

lint:
	$(MYPY) app/ tests/
	$(RUFF) check app/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache