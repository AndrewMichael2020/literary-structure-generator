"""
Evaluation metrics package

Automated scoring metrics for story quality.

Modules:
    - stylefit: Style similarity to AuthorProfile and ExemplarDigest
    - formfit: Structural adherence to StorySpec
    - coherence: Internal coherence and consistency
    - freshness: Novelty vs exemplar and corpus
    - overlap_guard: Anti-plagiarism checks
"""

__all__ = ["stylefit", "formfit", "coherence", "freshness", "overlap_guard"]
