"""
ReasonLog Pydantic model

Represents a structured decision log entry from an agent during the workflow.
Each agent (Digest, SpecSynth, Generator, Evaluator, Optimizer) can log decisions
with reasoning, parameters, and outcomes for reproducibility and debugging.

Schema version: ReasonLog@1

Used to track agent decisions across workflow runs and iterations.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReasonLog(BaseModel):
    """
    ReasonLog@1 schema

    Structured decision log entry for agentic workflow.
    Captures agent decisions with reasoning for reproducibility across runs.
    """

    schema_version: str = Field(
        default="ReasonLog@1", description="Schema version identifier", alias="schema"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of decision",
    )
    run_id: str = Field(..., description="Unique run identifier")
    iteration: int = Field(..., description="Iteration number (0-indexed)")
    agent: str = Field(
        ...,
        description="Agent name: Digest|SpecSynth|Generator|Evaluator|Optimizer",
    )
    decision: str = Field(..., description="Brief description of the decision made")
    reasoning: str = Field(
        ..., description="Explanation of why this decision was made"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Relevant parameters that influenced the decision",
    )
    outcome: Optional[str] = Field(
        default=None, description="Outcome or result of the decision (if available)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context or metadata"
    )

    class Config:
        """Pydantic config."""

        populate_by_name = True

        json_schema_extra = {
            "example": {
                "schema": "ReasonLog@1",
                "timestamp": "2024-01-15T10:30:00.000000",
                "run_id": "run_001",
                "iteration": 0,
                "agent": "SpecSynth",
                "decision": "Set voice.person to 'first' based on exemplar digest",
                "reasoning": (
                    "Exemplar digest shows 95% first-person pronouns, "
                    "strong intimate distance"
                ),
                "parameters": {
                    "exemplar_first_person_ratio": 0.95,
                    "distance": "intimate",
                    "alpha_exemplar": 0.7,
                },
                "outcome": "voice.person='first'",
                "metadata": {"digest_version": "ExemplarDigest@2"},
            }
        }
