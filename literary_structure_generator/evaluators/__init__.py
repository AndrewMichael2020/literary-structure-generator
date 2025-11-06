"""
Evaluators for scoring generated drafts against StorySpec and ExemplarDigest.

Phase 5 evaluation suite providing:
- Heuristic-based evaluators (stylefit_rules, formfit, coherence, motif, cadence, overlap)
- LLM-based evaluator (stylefit_llm)
- Orchestrator (evaluate.py)
"""

from literary_structure_generator.evaluators.evaluate import evaluate_draft

__all__ = ["evaluate_draft"]
