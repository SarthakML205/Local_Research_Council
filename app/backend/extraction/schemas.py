"""Strict Pydantic contracts for 9-field paper extractions and pedagogical study order."""

from pydantic import BaseModel, ConfigDict, Field


class PaperExtractionSchema(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: int = Field(default=1, description="Schema version")
    tldr: str = Field(description="Single-sentence, high-impact technical summary")
    problem_statement: str = Field(description="Core bottleneck or theoretical limitation addressed")
    methodology: str = Field(description="Underlying architecture, math formulation, or algorithmic contribution")
    key_results: list[str] = Field(description="Bullet points of quantitative benchmarks and empirical gains")
    why_it_matters: str = Field(description="Strategic importance of the paper to the broader field")
    audience: str = Field(description="Primary technical persona who benefits most (e.g. Systems Infra Engineers)")
    original_abstract: str = Field(description="Unmodified abstract text from arXiv metadata")
    research_gaps_identified: list[str] = Field(description="Explicit limitations admitted by the authors")
    ai_suggested_gaps: list[str] = Field(description="Novel criticisms, scaling bottlenecks, or flaws synthesized by local LLM")


class StudyRankItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    paper_id: str = Field(description="Unique paper identifier")
    study_rank: int = Field(description="1-based reading sequence order")
    rationale: str = Field(description="Pedagogical rationale for this sequence placement")
    prerequisite_concepts: list[str] = Field(description="Concepts needed prior to reading this paper")
    is_foundational: bool = Field(description="True if paper introduces foundational architectures or primitives")


class StudyCurriculumSchema(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    reading_order: list[StudyRankItem] = Field(description="Optimal sequential curriculum from fundamentals to SOTA")
    pedagogical_summary: str = Field(description="Overall study path justification")
