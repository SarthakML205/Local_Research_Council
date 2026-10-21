"""Application configuration and hardware ceiling contracts."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LRC_",
        extra="forbid",
        frozen=True,
    )

    # Core Storage Directories (Sources of truth & derived stores)
    PAPERS_DIR: Path = Field(default=Path("data/papers"), description="Source of truth for local papers")
    LIBRARY_DIR: Path = Field(default=Path("data/library"), description="Library metadata (CSV/JSON)")
    DEBATES_DIR: Path = Field(default=Path("data/debates"), description="Debate records and transcripts")
    TELEMETRY_DIR: Path = Field(default=Path("data/telemetry"), description="Telemetry CSV & JSONL sinks")
    LOGS_DIR: Path = Field(default=Path("data/logs"), description="Emergency fallback logs")
    QDRANT_PATH: Path = Field(default=Path("data/qdrant_db"), description="Embedded Qdrant local path")
    QDRANT_URL: str = Field(default="http://localhost:6333", description="Qdrant service URL if in server mode")
    QDRANT_MODE: str = Field(default="embedded", description="embedded | server")

    # Apple M5 24 GB Unified Memory Physical Ceilings
    TARGET_MEMORY_GB: float = Field(default=12.0, description="Nominal operational ceiling")
    MEMORY_WARNING_GB: float = Field(default=16.0, description="Telemetry warning tripwire")
    MEMORY_CEILING_GB: float = Field(default=18.0, description="Hard engine abort ceiling")
    PROFILER_INTERVAL_MS: int = Field(default=20, description="Hardware watchdog sample interval")

    # Local Quantized Model Identifiers
    MODEL_TAG: str = Field(default="llama3.1:8b-instruct-q4_K_M", description="4-bit quantized local LLM")
    EMBEDDING_MODEL_TAG: str = Field(default="bge-large-en-v1.5", description="MLX Apple Silicon embedder")
    RERANKER_MODEL_TAG: str = Field(default="bge-reranker-large", description="Local cross-encoder")

    # Hard < 2,048 Token Budget Compartments
    MAX_PROMPT_TOKENS: int = Field(default=2048, description="Hard ceiling for any debate turn prompt")
    SYSTEM_TOKEN_BUDGET: int = Field(default=256, description="System persona and debate rules")
    RAG_TOKEN_BUDGET: int = Field(default=1024, description="Partitioned grounding context knapsack")
    HISTORY_TOKEN_BUDGET: int = Field(default=768, description="Shared debate history and cards")
    MAX_POSITION_CARDS_BUDGET: int = Field(default=384, description="Total budget for N agent position cards")

    # Council Bounds & Scheduling
    COUNCIL_MIN_PAPERS: int = Field(default=2, description="Minimum papers required for a debate")
    COUNCIL_MAX_PAPERS: int = Field(default=6, description="Default maximum papers (configurable up to 10)")
    COUNCIL_ROUNDS: int = Field(default=3, description="Default debate cross-examination rounds")

    # PDF Slicing & Chunking Bounds
    PDF_MAX_PAGES: int = Field(default=8, description="First 6-8 pages sliced before references")
    CHUNK_MIN_TOKENS: int = Field(default=256, description="Minimum tokens per structural chunk")
    CHUNK_MAX_TOKENS: int = Field(default=512, description="Maximum tokens per structural chunk")
    CHUNK_OVERLAP_PERCENT: float = Field(default=0.10, description="Token overlap between adjacent chunks")
    MINDMAP_EDGE_WEIGHT_MIN: float = Field(default=0.35, description="Minimum confidence weight for graph edges")

    # Telemetry & Hot-Path Isolation
    TELEMETRY_QUEUE_SIZE: int = Field(default=10000, description="Async bounded queue buffer depth")
    TELEMETRY_BATCH_SIZE: int = Field(default=100, description="Events per batched disk flush")
    TELEMETRY_FLUSH_INTERVAL_MS: int = Field(default=100, description="Maximum wait before flush")
    TELEMETRY_RETENTION_DAYS: int = Field(default=30, description="Days to retain telemetry on disk")
    TELEMETRY_RING_BUFFER_CAPACITY: int = Field(default=1000, description="In-RAM recent event ring buffer")
    CAPTURE_PAYLOADS: bool = Field(default=False, description="Whether to capture raw prompts/responses")

    def ensure_directories(self) -> None:
        """Create all required data and telemetry directories atomically."""
        for path in (
            self.PAPERS_DIR,
            self.PAPERS_DIR / "_inbox",
            self.LIBRARY_DIR,
            self.LIBRARY_DIR / "backups",
            self.DEBATES_DIR,
            self.TELEMETRY_DIR / "llm_calls",
            self.TELEMETRY_DIR / "retrieval",
            self.TELEMETRY_DIR / "embeddings",
            self.TELEMETRY_DIR / "system",
            self.TELEMETRY_DIR / "events",
            self.TELEMETRY_DIR / "failures",
            self.TELEMETRY_DIR / "rollups",
            self.TELEMETRY_DIR / "payloads",
            self.LOGS_DIR,
            self.QDRANT_PATH,
        ):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
