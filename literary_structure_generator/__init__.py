"""
Literary Structure Generator

An agentic workflow for literary short-story generation that learns structural DNA
from exemplar texts and generates new stories with similar form but original content.

Core Architecture:
    Exemplar → Digest → StorySpec → Generate Candidates → Evaluate → Optimize → Final Story

Main Components:
    - models: Pydantic schemas for data artifacts
    - digest: Exemplar analysis and extraction
    - spec: StorySpec synthesis
    - generation: Draft generation with LLMs
    - evaluation: Multi-metric scoring
    - optimization: Iterative refinement loop
    - profiles: AuthorProfile management
    - orchestrators: High-level workflows
    - utils: Shared utilities

Anti-Plagiarism Guardrails:
    - Max shared n-gram ≤ 12 tokens
    - Overall overlap ≤ 3% vs exemplar
    - SimHash Hamming distance ≥ 18 for 256-bit chunks
"""

__version__ = "0.1.0"
__author__ = "Andrew Michael"

from literary_structure_generator.models import (
    AuthorProfile,
    EvalReport,
    ExemplarDigest,
    GenerationConfig,
    StorySpec,
)

__all__ = [
    "AuthorProfile",
    "EvalReport",
    "ExemplarDigest",
    "GenerationConfig",
    "StorySpec",
    "__version__",
]
