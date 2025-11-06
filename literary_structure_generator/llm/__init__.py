"""
LLM integration module for literary structure generator.

Provides first-class LLM adapters with:
- Per-component routing via llm_routing.json
- Deterministic mock clients for offline testing
- Caching and retry logic
- Drift controls (prompt versioning, sampling caps, checksums)
"""

from literary_structure_generator.llm.adapters import (
    label_motifs,
    name_imagery,
    paraphrase_beats,
    repair_pass,
    stylefit_score,
)
from literary_structure_generator.llm.router import get_client, get_params

__all__ = [
    "get_client",
    "get_params",
    "label_motifs",
    "name_imagery",
    "paraphrase_beats",
    "repair_pass",
    "stylefit_score",
]
