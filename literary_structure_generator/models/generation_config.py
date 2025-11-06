"""
GenerationConfig Pydantic model

Configuration parameters for the story generation orchestrator.
Controls LLM parameters, diversity settings, constraint enforcement,
and optimization loop behavior.

Schema version: GenerationConfig@2

Used to control the generation and optimization process.
"""

from pydantic import BaseModel, Field


class PerBeatGeneration(BaseModel):
    """Per-beat generation parameters."""

    temperature: list[float] = Field(
        default_factory=lambda: [0.7, 0.95], description="Temperature range for sampling"
    )
    top_p: list[float] = Field(
        default_factory=lambda: [0.85, 0.95], description="Top-p range for nucleus sampling"
    )
    length_tolerance: float = Field(
        default=0.2, description="Allowed deviation from target length (as fraction)"
    )
    repetition_penalty: float = Field(default=1.05, description="Repetition penalty factor")
    stop_on: list[str] = Field(default_factory=list, description="Stop sequences")
    rewrite_passes: int = Field(default=1, description="Number of rewrite passes per beat")


class Diversity(BaseModel):
    """Diversity control parameters."""

    beat_shuffle: float = Field(
        default=0.15, description="Probability of shuffling beat order (for variation)"
    )
    spec_jitter: float = Field(
        default=0.1, description="Random jitter to spec parameters (for exploration)"
    )


class ConstraintEnforcement(BaseModel):
    """Constraint enforcement settings."""

    max_ngram: int = Field(default=12, description="Maximum shared n-gram length with exemplar")
    simhash_hamming_min: int = Field(
        default=18, description="Minimum SimHash Hamming distance from exemplar"
    )
    forbidden_lexicon: list[str] = Field(
        default_factory=list, description="Forbidden words or phrases"
    )


class RepairSteps(BaseModel):
    """Repair and refinement settings."""

    enable_line_edit: bool = Field(default=True, description="Whether to enable line-level edits")
    max_passes: int = Field(default=2, description="Maximum number of repair passes")


class Optimizer(BaseModel):
    """Optimizer loop configuration (Adam-ish schedule)."""

    mode: str = Field(default="adamish", description="Optimizer mode")
    max_iters: int = Field(default=10, description="Maximum optimization iterations")
    warmup_iters: int = Field(default=2, description="Warmup iterations before optimization")
    patience: int = Field(default=3, description="Early stopping patience")
    step_size: float = Field(default=0.1, description="Optimization step size")
    beta1: float = Field(default=0.8, description="Adam beta1 parameter (momentum)")
    beta2: float = Field(default=0.95, description="Adam beta2 parameter (variance)")
    exploration_radius: float = Field(
        default=0.08, description="Exploration radius for escaping local minima"
    )
    population: int = Field(default=6, description="Population size for evolutionary sampling")


class Caching(BaseModel):
    """Caching settings."""

    prompt_cache: bool = Field(default=True, description="Whether to cache prompts")
    digest_cache: bool = Field(default=True, description="Whether to cache digest")


class Profanity(BaseModel):
    """Profanity filtering settings."""

    enabled: bool = Field(
        default=True, description="Whether profanity filtering is enabled (always recommended)"
    )
    substitution: str = Field(
        default="[bleep]", description="Substitution string for profanity replacement"
    )


class GenerationConfig(BaseModel):
    """
    GenerationConfig@2 schema

    Complete configuration for story generation and optimization.
    Controls LLM parameters, diversity, constraints, evaluation, and optimization.
    """

    schema_version: str = Field(
        default="GenerationConfig@2", description="Schema version identifier", alias="schema"
    )
    seed: int = Field(default=137, description="Global random seed for reproducibility")
    num_candidates: int = Field(default=8, description="Number of candidate stories to generate")
    per_beat_generation: PerBeatGeneration = Field(
        default_factory=PerBeatGeneration, description="Per-beat generation parameters"
    )
    diversity: Diversity = Field(default_factory=Diversity, description="Diversity controls")
    constraint_enforcement: ConstraintEnforcement = Field(
        default_factory=ConstraintEnforcement, description="Constraint enforcement settings"
    )
    repair_steps: RepairSteps = Field(
        default_factory=RepairSteps, description="Repair and refinement settings"
    )
    profanity: Profanity = Field(
        default_factory=Profanity, description="Profanity filtering settings"
    )
    evaluator_suite: list[str] = Field(
        default_factory=lambda: [
            "stylefit",
            "formfit",
            "coherence",
            "freshness",
            "overlap_guard",
            "valence_arc_fit",
            "cadence",
        ],
        description="List of evaluators to run",
    )
    objective_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "stylefit": 0.3,
            "formfit": 0.3,
            "coherence": 0.25,
            "freshness": 0.1,
            "cadence": 0.05,
        },
        description="Weights for objective function",
    )
    optimizer: Optimizer = Field(default_factory=Optimizer, description="Optimizer configuration")
    caching: Caching = Field(default_factory=Caching, description="Caching settings")

    class Config:
        """Pydantic config."""

        populate_by_name = True

        json_schema_extra = {
            "example": {
                "schema": "GenerationConfig@2",
                "seed": 137,
                "num_candidates": 8,
                "per_beat_generation": {
                    "temperature": [0.7, 0.95],
                    "top_p": [0.85, 0.95],
                    "repetition_penalty": 1.05,
                },
                "evaluator_suite": ["stylefit", "formfit", "coherence", "freshness"],
                "objective_weights": {"stylefit": 0.3, "formfit": 0.3},
            }
        }
