"""
Digest package

Modules for analyzing exemplar texts and extracting structural DNA.
Combines heuristic analysis with LLM-assisted annotation.

Modules:
    - stylometry: Statistical text analysis (sentence length, POS, punctuation)
    - discourse: Discourse-level features (beats, dialogue, tense)
    - pacing: Pacing and rhythm analysis
    - coherence: Entity tracking and pronoun chains
    - beat_labeler: LLM-assisted beat identification
    - motif_extractor: Motif and theme extraction
    - voice_analyzer: Voice and POV distance analysis
    - assemble: Orchestrate full digest pipeline
"""

__all__ = [
    "stylometry",
    "discourse",
    "pacing",
    "coherence",
    "beat_labeler",
    "motif_extractor",
    "voice_analyzer",
    "assemble",
]
