"""
Data models package

Pydantic schemas for all core data artifacts with validation and serialization.
All models include schema versioning and support JSON serialization.

Models:
    - ExemplarDigest: Extracted DNA from exemplar text
    - StorySpec: Portable specification for story generation
    - GenerationConfig: Orchestrator control parameters
    - EvalReport: Multi-metric assessment per candidate
    - AuthorProfile: User voice preferences and constraints
"""

from literary_structure_generator.models.exemplar_digest import ExemplarDigest
from literary_structure_generator.models.story_spec import StorySpec
from literary_structure_generator.models.generation_config import GenerationConfig
from literary_structure_generator.models.eval_report import EvalReport
from literary_structure_generator.models.author_profile import AuthorProfile

__all__ = [
    "ExemplarDigest",
    "StorySpec",
    "GenerationConfig",
    "EvalReport",
    "AuthorProfile",
]
