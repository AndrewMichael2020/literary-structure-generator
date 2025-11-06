"""
Optimizer module

Iterative optimization loop for improving story generation quality.

Features:
    - Deterministic heuristic adjustments guided by EvalReport
    - Adjustable fields: beat lengths, sentence length, dialogue ratio, motif weights, temperature
    - Early stopping when improvement plateaus
    - History tracking and artifact persistence

Optimizes GenerationConfig and StorySpec based on EvalReport feedback.
Each decision is logged via log_decision() for reproducibility.
"""

import json
import uuid
from pathlib import Path
from typing import Any

from literary_structure_generator.evaluators.evaluate import evaluate_draft, save_eval_report
from literary_structure_generator.generation.draft_generator import run_draft_generation
from literary_structure_generator.models.eval_report import EvalReport, TuningSuggestion
from literary_structure_generator.models.exemplar_digest import ExemplarDigest
from literary_structure_generator.models.generation_config import GenerationConfig
from literary_structure_generator.models.story_spec import StorySpec
from literary_structure_generator.utils.decision_logger import log_decision


class Optimizer:
    """
    Iterative optimization engine that refines StorySpec and GenerationConfig
    over multiple rounds using evaluation feedback.
    """

    def __init__(
        self,
        max_iters: int = 5,
        candidates: int = 3,
        early_stop_delta: float = 0.01,
        run_id: str | None = None,
    ):
        """
        Initialize the optimizer.

        Args:
            max_iters: Maximum number of optimization iterations
            candidates: Number of candidate drafts to generate per iteration
            early_stop_delta: Minimum improvement required to continue optimization
            run_id: Unique run identifier (auto-generated if None)
        """
        self.max_iters = max_iters
        self.candidates = candidates
        self.early_stop_delta = early_stop_delta
        self.run_id = run_id or f"opt_{uuid.uuid4().hex[:8]}"

    def suggest(self, spec: StorySpec, report: EvalReport) -> StorySpec:
        """
        Return an updated spec with small, directed adjustments based on evaluation.

        Adjusts:
        - form.beat_map[*].target_words ± 5-15%
        - voice.syntax.avg_sentence_len ± 1-2 tokens
        - form.dialogue_ratio ± 0.03
        - Per-evaluator tuning suggestions

        Args:
            spec: Current StorySpec
            report: EvalReport with evaluation feedback

        Returns:
            Updated StorySpec with adjustments
        """
        # Create a deep copy to avoid mutating the original
        new_spec = spec.model_copy(deep=True)

        # Process tuning suggestions from evaluators
        for suggestion in report.tuning_suggestions:
            self._apply_suggestion(new_spec, suggestion)

        # Process drift items to correct deviations
        for drift in report.drift_vs_spec:
            self._correct_drift(new_spec, drift)

        # Adjust beat lengths if formfit score is low
        if report.scores.formfit < 0.7:
            self._adjust_beat_lengths(new_spec, report)

        # Adjust sentence length if stylefit is low
        if report.scores.stylefit < 0.7:
            self._adjust_syntax(new_spec, report)

        # Adjust dialogue ratio if dialogue_balance is low
        if report.scores.dialogue_balance < 0.7:
            self._adjust_dialogue_ratio(new_spec, report)

        return new_spec

    def run(
        self,
        spec: StorySpec,
        digest: ExemplarDigest,
        exemplar_text: str,
        config: GenerationConfig | None = None,
        output_dir: str = "runs",
    ) -> dict[str, Any]:
        """
        Run multi-iteration optimization loop.

        Each iteration:
        → generate → evaluate → adjust → repeat → stop when improvement plateaus

        Args:
            spec: Initial StorySpec
            digest: ExemplarDigest for evaluation
            exemplar_text: Original exemplar text for overlap checking
            config: GenerationConfig (uses default if None)
            output_dir: Base directory for saving artifacts

        Returns:
            Dictionary with:
            - best_spec: Best StorySpec found
            - best_draft: Best draft generated
            - best_score: Best overall score achieved
            - history: List of iteration results
        """
        # Initialize config if not provided
        if config is None:
            config = GenerationConfig()

        # Log start of optimization
        log_decision(
            run_id=self.run_id,
            iteration=0,
            agent="Optimizer",
            decision="Start optimization loop",
            reasoning=(
                f"Beginning {self.max_iters} iterations with {self.candidates} "
                f"candidates per iteration. Early stopping at delta < {self.early_stop_delta}."
            ),
            parameters={
                "max_iters": self.max_iters,
                "candidates": self.candidates,
                "early_stop_delta": self.early_stop_delta,
            },
            output_dir=output_dir,
        )

        # Track optimization state
        current_spec = spec.model_copy(deep=True)
        current_config = config.model_copy(deep=True)
        best_spec = current_spec
        best_draft = None
        best_score = 0.0
        best_report = None
        history = []
        no_improvement_count = 0

        # Main optimization loop
        for iteration in range(self.max_iters):
            iteration_result = self._run_iteration(
                iteration=iteration,
                spec=current_spec,
                config=current_config,
                digest=digest,
                exemplar_text=exemplar_text,
                output_dir=output_dir,
            )

            # Update history
            history.append(iteration_result)

            # Check if this is the best so far
            iter_score = iteration_result["best_score"]
            improvement = iter_score - best_score

            if iter_score > best_score:
                best_score = iter_score
                best_spec = iteration_result["best_spec"]
                best_draft = iteration_result["best_draft"]
                best_report = iteration_result["best_report"]
                no_improvement_count = 0

                log_decision(
                    run_id=self.run_id,
                    iteration=iteration,
                    agent="Optimizer",
                    decision=f"New best score: {best_score:.4f}",
                    reasoning=f"Improvement of {improvement:.4f} over previous best",
                    parameters={"score": best_score, "improvement": improvement},
                    output_dir=output_dir,
                )
            else:
                no_improvement_count += 1

                log_decision(
                    run_id=self.run_id,
                    iteration=iteration,
                    agent="Optimizer",
                    decision="No improvement",
                    reasoning=f"Score {iter_score:.4f} not better than best {best_score:.4f}",
                    parameters={
                        "current_score": iter_score,
                        "best_score": best_score,
                        "no_improvement_count": no_improvement_count,
                    },
                    output_dir=output_dir,
                )

            # Early stopping check
            if improvement < self.early_stop_delta and no_improvement_count >= 2:
                log_decision(
                    run_id=self.run_id,
                    iteration=iteration,
                    agent="Optimizer",
                    decision="Early stopping triggered",
                    reasoning=(
                        f"No significant improvement for {no_improvement_count} iterations. "
                        f"Last improvement: {improvement:.4f} < {self.early_stop_delta}"
                    ),
                    parameters={
                        "final_score": best_score,
                        "iterations_completed": iteration + 1,
                    },
                    output_dir=output_dir,
                )
                break

            # Adjust spec for next iteration based on best report
            if best_report:
                current_spec = self.suggest(current_spec, best_report)
                current_config = self._adjust_config(current_config, best_report, iteration)

        # Save final results
        self._save_final_results(
            best_spec=best_spec,
            best_draft=best_draft,
            best_score=best_score,
            best_report=best_report,
            history=history,
            output_dir=output_dir,
        )

        return {
            "best_spec": best_spec,
            "best_draft": best_draft,
            "best_score": best_score,
            "best_report": best_report,
            "history": history,
        }

    def _run_iteration(
        self,
        iteration: int,
        spec: StorySpec,
        config: GenerationConfig,
        digest: ExemplarDigest,
        exemplar_text: str,
        output_dir: str,
    ) -> dict[str, Any]:
        """Run a single optimization iteration."""
        log_decision(
            run_id=self.run_id,
            iteration=iteration,
            agent="Optimizer",
            decision=f"Start iteration {iteration}",
            reasoning=f"Generating {self.candidates} candidates for evaluation",
            parameters={"iteration": iteration, "num_candidates": self.candidates},
            output_dir=output_dir,
        )

        # Generate candidates
        candidates = []
        for i in range(self.candidates):
            candidate_id = f"{self.run_id}_iter{iteration}_cand{i}"

            # Generate draft using run_draft_generation
            draft_result = run_draft_generation(
                spec=spec,
                exemplar=exemplar_text,
                output_dir=None,  # Don't save per-candidate artifacts automatically
            )

            # Prepare draft dict for evaluation
            draft = {
                "text": draft_result.get("repaired", draft_result.get("stitched", "")),
                "seeds": draft_result.get("metadata", {}).get("seeds", {}),
            }

            # Evaluate draft
            report = evaluate_draft(
                draft=draft,
                spec=spec,
                digest=digest,
                exemplar_text=exemplar_text,
                config=config,
                run_id=self.run_id,
                candidate_id=candidate_id,
                use_llm_stylefit=False,  # Use heuristics only for optimization
            )

            candidates.append({"draft": draft, "report": report, "spec": spec})

            # Save iteration artifacts
            iter_dir = Path(output_dir) / self.run_id / f"iter_{iteration}"
            iter_dir.mkdir(parents=True, exist_ok=True)

            # Save draft
            draft_path = iter_dir / f"draft_{i}.txt"
            with open(draft_path, "w", encoding="utf-8") as f:
                f.write(draft.get("text", ""))

            # Save evaluation report
            save_eval_report(report, output_dir=str(iter_dir.parent))

        # Find best candidate in this iteration
        best_candidate = max(candidates, key=lambda c: c["report"].scores.overall)

        return {
            "iteration": iteration,
            "best_spec": best_candidate["spec"],
            "best_draft": best_candidate["draft"],
            "best_report": best_candidate["report"],
            "best_score": best_candidate["report"].scores.overall,
            "all_scores": [c["report"].scores.overall for c in candidates],
        }

    def _apply_suggestion(self, spec: StorySpec, suggestion: TuningSuggestion) -> None:
        """Apply a tuning suggestion to the spec."""
        param = suggestion.param
        action = suggestion.action.lower()
        amount = suggestion.by

        # Handle different parameter types
        if "sentence_len" in param or "avg_sentence" in param:
            if action == "increase":
                spec.voice.syntax.avg_sentence_len = min(
                    spec.voice.syntax.avg_sentence_len + int(amount), 30
                )
            elif action == "decrease":
                spec.voice.syntax.avg_sentence_len = max(
                    spec.voice.syntax.avg_sentence_len - int(amount), 8
                )

        elif "dialogue" in param:
            if action == "increase":
                spec.form.dialogue_ratio = min(spec.form.dialogue_ratio + amount, 0.6)
            elif action == "decrease":
                spec.form.dialogue_ratio = max(spec.form.dialogue_ratio - amount, 0.0)

    def _correct_drift(self, spec: StorySpec, drift: Any) -> None:
        """Correct drift from target specification."""
        field = drift.field

        # Correct in opposite direction of drift
        if "dialogue_ratio" in field:
            # Move toward target
            spec.form.dialogue_ratio = max(0.0, min(0.6, drift.target))

    def _adjust_beat_lengths(self, spec: StorySpec, report: EvalReport) -> None:
        """Adjust beat target_words based on formfit feedback."""
        # Find beats that are too short or too long based on per-beat scores
        for beat_score in report.per_beat:
            # Find corresponding beat in spec
            for beat in spec.form.beat_map:
                if beat.id == beat_score.id and beat_score.formfit < 0.7:
                    # If formfit is low, adjust target words slightly (5-10%)
                    adjustment = int(beat.target_words * 0.08)
                    beat.target_words += adjustment if beat_score.formfit < 0.5 else -adjustment
                    beat.target_words = max(50, min(300, beat.target_words))

    def _adjust_syntax(self, spec: StorySpec, report: EvalReport) -> None:
        """Adjust syntax parameters based on stylefit feedback."""
        # Adjust sentence length slightly (±1-2 tokens)
        if report.scores.stylefit < 0.65:
            spec.voice.syntax.avg_sentence_len = max(
                8, min(30, spec.voice.syntax.avg_sentence_len + 1)
            )

    def _adjust_dialogue_ratio(self, spec: StorySpec, report: EvalReport) -> None:
        """Adjust dialogue ratio based on evaluation."""
        if report.scores.dialogue_balance < 0.7:
            # Move slightly toward better balance (±0.03)
            adjustment = 0.03 if report.scores.dialogue_balance < 0.5 else -0.02
            spec.form.dialogue_ratio = max(0.0, min(0.6, spec.form.dialogue_ratio + adjustment))

    def _adjust_config(
        self, config: GenerationConfig, report: EvalReport, iteration: int
    ) -> GenerationConfig:
        """Adjust GenerationConfig based on evaluation feedback."""
        new_config = config.model_copy(deep=True)

        # Adjust temperature slightly if supported (±0.05)
        # Note: GPT-5 models don't support temperature, router will filter it out
        if report.scores.freshness < 0.6 and iteration > 0:
            # Increase temperature for more diversity
            temp_range = new_config.per_beat_generation.temperature
            new_temp = [min(t + 0.05, 1.0) for t in temp_range]
            new_config.per_beat_generation.temperature = new_temp
        elif report.scores.freshness > 0.85:
            # Decrease temperature for more consistency
            temp_range = new_config.per_beat_generation.temperature
            new_temp = [max(t - 0.05, 0.1) for t in temp_range]
            new_config.per_beat_generation.temperature = new_temp

        # Re-weight objectives toward low-scoring metrics
        weights = new_config.objective_weights.copy()
        for metric in ["stylefit", "formfit", "coherence", "freshness", "cadence"]:
            score = getattr(report.scores, metric, 0.0)
            if score < 0.6 and metric in weights:
                # Slightly increase weight for low-scoring metrics
                weights[metric] = min(weights[metric] + 0.05, 0.5)

        # Normalize weights
        total = sum(weights.values())
        if total > 0:
            new_config.objective_weights = {k: v / total for k, v in weights.items()}

        return new_config

    def _save_final_results(
        self,
        best_spec: StorySpec,
        best_draft: dict[str, Any] | None,
        best_score: float,
        best_report: EvalReport | None,  # noqa: ARG002
        history: list[dict[str, Any]],
        output_dir: str,
    ) -> None:
        """Save final optimization results."""
        results_dir = Path(output_dir) / self.run_id
        results_dir.mkdir(parents=True, exist_ok=True)

        # Save best spec
        spec_path = results_dir / "best_spec.json"
        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(best_spec.model_dump(by_alias=True), f, indent=2)

        # Save best draft
        if best_draft:
            draft_path = results_dir / "best_draft.txt"
            with open(draft_path, "w", encoding="utf-8") as f:
                f.write(best_draft.get("text", ""))

        # Save optimization summary
        summary = {
            "run_id": self.run_id,
            "best_score": best_score,
            "iterations_completed": len(history),
            "score_progression": [h["best_score"] for h in history],
        }
        summary_path = results_dir / "optimization_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        log_decision(
            run_id=self.run_id,
            iteration=len(history) - 1 if history else 0,
            agent="Optimizer",
            decision="Optimization complete",
            reasoning=f"Final score: {best_score:.4f} after {len(history)} iterations",
            parameters={
                "best_score": best_score,
                "iterations": len(history),
                "artifacts_saved": str(results_dir),
            },
            output_dir=output_dir,
        )
