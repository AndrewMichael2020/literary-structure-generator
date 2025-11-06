"""
Evaluation package

Multi-metric evaluation of generated story candidates.

Modules:
    - metrics: Automated scoring metrics
        - stylefit: Style similarity to target
        - formfit: Structural adherence
        - coherence: Internal consistency
        - freshness: Novelty and originality
        - overlap_guard: Anti-plagiarism checks
    - subjective: LLM-assisted qualitative assessment
    - assemble: Orchestrate evaluation and generate EvalReport
"""

__all__ = ["assemble", "metrics", "subjective"]
