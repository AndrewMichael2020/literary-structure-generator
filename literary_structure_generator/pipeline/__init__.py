"""
Pipeline orchestrators for multi-stage story generation.

Contains high-level orchestrators that coordinate generation,
evaluation, and selection of story candidates.
"""

from literary_structure_generator.pipeline.generate_candidates import generate_candidates

__all__ = ["generate_candidates"]
