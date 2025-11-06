"""
EvalReport Pydantic model

Multi-metric evaluation report for a generated story candidate.
Includes objective scores, per-beat analysis, coherence graphs,
drift analysis, and tuning suggestions.

Schema version: EvalReport@2

Used to assess quality and provide feedback for optimization.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OverlapGuard(BaseModel):
    """Anti-plagiarism overlap metrics."""

    max_ngram: int = Field(default=0, description="Maximum shared n-gram length found")
    overlap_pct: float = Field(default=0.0, description="Percentage overlap with exemplar")


class Scores(BaseModel):
    """Evaluation scores."""

    overall: float = Field(default=0.0, description="Weighted overall score")
    stylefit: float = Field(default=0.0, description="Style similarity to target")
    formfit: float = Field(default=0.0, description="Structural adherence to spec")
    coherence: float = Field(default=0.0, description="Internal coherence and consistency")
    freshness: float = Field(default=0.0, description="Novelty and originality")
    overlap_guard: OverlapGuard = Field(
        default_factory=OverlapGuard, description="Anti-plagiarism metrics"
    )
    valence_arc_fit: float = Field(default=0.0, description="Emotional arc alignment")
    cadence: float = Field(default=0.0, description="Rhythm and pacing quality")
    dialogue_balance: float = Field(default=0.0, description="Dialogue ratio adherence")
    motif_coverage: float = Field(default=0.0, description="Motif presence and distribution")


class PerBeatScore(BaseModel):
    """Per-beat evaluation scores."""

    id: str = Field(..., description="Beat identifier")
    stylefit: float = Field(default=0.0, description="Style score for this beat")
    formfit: float = Field(default=0.0, description="Form score for this beat")
    notes: str = Field(default="", description="Qualitative notes")


class CoherenceGraph(BaseModel):
    """Entity coherence graph."""

    entities: List[str] = Field(default_factory=list, description="List of entities")
    edges: List[List[str]] = Field(
        default_factory=list, description="Entity relationships [[entity1, relation, entity2], ...]"
    )


class DriftItem(BaseModel):
    """Drift from specification."""

    field: str = Field(..., description="Spec field that drifted")
    target: float = Field(..., description="Target value from spec")
    actual: float = Field(..., description="Actual value in generated text")
    delta: float = Field(..., description="Difference (actual - target)")


class TuningSuggestion(BaseModel):
    """Tuning suggestion for next iteration."""

    param: str = Field(..., description="Parameter to adjust")
    action: str = Field(..., description="Action to take (increase, decrease, etc.)")
    by: float = Field(..., description="Amount to adjust by")
    reason: str = Field(..., description="Reason for suggestion")


class Repro(BaseModel):
    """Reproducibility information."""

    git_commit: str = Field(default="", description="Git commit hash")
    model: str = Field(default="", description="LLM model used")
    model_temp: float = Field(default=0.0, description="Model temperature")


class EvalReport(BaseModel):
    """
    EvalReport@2 schema

    Complete evaluation report for a generated story candidate.
    Includes multi-metric scores, diagnostics, and optimization feedback.
    """

    schema_version: str = Field(default="EvalReport@2", description="Schema version identifier", alias="schema")
    run_id: str = Field(..., description="Unique run identifier")
    candidate_id: str = Field(..., description="Candidate identifier")
    config_hash: str = Field(..., description="Hash of generation config")
    seeds: Dict[str, Any] = Field(
        default_factory=dict, description="Random seeds used (global and per-beat)"
    )
    length: Dict[str, int] = Field(
        default_factory=dict, description="Length metrics (words, paragraphs)"
    )
    scores: Scores = Field(default_factory=Scores, description="Evaluation scores")
    per_beat: List[PerBeatScore] = Field(
        default_factory=list, description="Per-beat evaluation scores"
    )
    coherence_graph: CoherenceGraph = Field(
        default_factory=CoherenceGraph, description="Entity coherence graph"
    )
    red_flags: List[str] = Field(default_factory=list, description="Quality red flags")
    guardrail_failures: List[str] = Field(
        default_factory=list, description="Guardrail violations"
    )
    drift_vs_spec: List[DriftItem] = Field(
        default_factory=list, description="Drift from specification"
    )
    tuning_suggestions: List[TuningSuggestion] = Field(
        default_factory=list, description="Optimization suggestions"
    )
    pass_fail: bool = Field(default=False, description="Whether this candidate passes all checks")
    notes: str = Field(default="", description="Qualitative notes")
    repro: Repro = Field(default_factory=Repro, description="Reproducibility information")

    class Config:
        """Pydantic config."""
        
        populate_by_name = True

        json_schema_extra = {
            "example": {
                "schema": "EvalReport@2",
                "run_id": "run_001",
                "candidate_id": "cand_001",
                "config_hash": "a1b2c3",
                "seeds": {"global": 137, "per_beat": [137, 138, 139]},
                "length": {"words": 2150, "paragraphs": 48},
                "scores": {
                    "overall": 0.76,
                    "stylefit": 0.78,
                    "formfit": 0.74,
                    "coherence": 0.81,
                    "freshness": 0.69,
                },
                "pass_fail": True,
            }
        }
