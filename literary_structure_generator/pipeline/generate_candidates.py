"""
Multi-candidate generation pipeline.

Orchestrates the generation of N candidate drafts from a StorySpec and ExemplarDigest.
Each candidate goes through:
1. Per-beat generation (using router: beat_generator)
2. Stitch beats together
3. Guards (overlap %, SimHash, profanity)
4. Repair pass (using router: repair_pass)
5. Evaluate (using Phase 5 orchestrator)

Finally, select the best candidate based on evaluation scores.
All LLM calls go through the router, with GPT-5 parameter handling.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from literary_structure_generator.evaluators.evaluate import evaluate_draft
from literary_structure_generator.generation.draft_generator import (
    generate_beat_text,
    stitch_beats,
)
from literary_structure_generator.generation.guards import check_overlap_guard
from literary_structure_generator.generation.repair import repair_text
from literary_structure_generator.models.exemplar_digest import ExemplarDigest
from literary_structure_generator.models.generation_config import GenerationConfig
from literary_structure_generator.models.story_spec import StorySpec


def generate_single_candidate(
    spec: StorySpec,
    digest: ExemplarDigest,
    exemplar_text: str,
    candidate_id: str,
    run_id: str,
    config: Optional[GenerationConfig] = None,
) -> dict:
    """
    Generate a single candidate draft.

    Steps:
    1. Generate beats using router (beat_generator)
    2. Stitch beats
    3. Check guards (overlap, SimHash, profanity)
    4. Repair if needed (using router: repair_pass)
    5. Evaluate using Phase 5 orchestrator

    Args:
        spec: StorySpec with voice, form, and content parameters
        digest: ExemplarDigest for comparison
        exemplar_text: Original exemplar text (for overlap checking)
        candidate_id: Unique candidate identifier
        run_id: Run identifier
        config: Optional GenerationConfig (uses default if not provided)

    Returns:
        Dictionary with:
            - id: candidate_id
            - beats: List of beat generation results
            - stitched: Stitched text
            - repaired: Repaired text
            - eval: EvalReport object
            - metadata: Generation metadata
    """
    if config is None:
        config = GenerationConfig()

    # Step 1: Generate beats
    beat_results = []
    beat_texts = []
    memory = {}  # Context for beat generation

    for beat_spec in spec.form.beat_map:
        beat_result = generate_beat_text(
            beat_spec=beat_spec,
            story_spec=spec,
            memory=memory,
            exemplar=exemplar_text,
            max_retries=2,
        )
        beat_results.append(beat_result)
        beat_texts.append(beat_result["text"])

        # Update memory for next beat
        memory[beat_spec.id] = {
            "text": beat_result["text"],
            "function": beat_spec.function,
        }

    # Step 2: Stitch beats
    stitched = stitch_beats(beat_texts)

    # Step 3: Check guards on stitched text
    guard_result = check_overlap_guard(
        stitched,
        exemplar_text,
        max_ngram=spec.constraints.anti_plagiarism.max_ngram,
        max_overlap_pct=spec.constraints.anti_plagiarism.overlap_pct,
        min_simhash_hamming=spec.constraints.anti_plagiarism.simhash_hamming_min,
    )

    # Step 4: Repair if needed
    repair_notes = {"issues": []}
    if not guard_result["passed"]:
        repair_notes["issues"].extend(guard_result["violations"])

    repaired = repair_text(stitched, spec, notes=repair_notes)

    # Re-check guards after repair
    final_guard = check_overlap_guard(
        repaired,
        exemplar_text,
        max_ngram=spec.constraints.anti_plagiarism.max_ngram,
        max_overlap_pct=spec.constraints.anti_plagiarism.overlap_pct,
        min_simhash_hamming=spec.constraints.anti_plagiarism.simhash_hamming_min,
    )

    # Step 5: Evaluate using Phase 5
    # Extract seeds for repro (use 0 as default if not present)
    default_seed = 0
    per_beat_seeds = [br.get("metadata", {}).get("seed", default_seed) for br in beat_results]

    draft_dict = {
        "text": repaired,
        "seeds": {"per_beat": per_beat_seeds},
    }

    eval_report = evaluate_draft(
        draft=draft_dict,
        spec=spec,
        digest=digest,
        exemplar_text=exemplar_text,
        config=config,
        run_id=run_id,
        candidate_id=candidate_id,
        use_llm_stylefit=False,  # Keep offline for tests
    )

    # Compile metadata
    metadata = {
        "candidate_id": candidate_id,
        "run_id": run_id,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "num_beats": len(beat_results),
        "total_words": len(repaired.split()),
        "target_words": spec.constraints.length_words.target,
        "stitched_guard": guard_result,
        "final_guard": final_guard,
        "beat_guard_failures": sum(1 for br in beat_results if not br.get("guard_passed", True)),
    }

    return {
        "id": candidate_id,
        "beats": beat_results,
        "stitched": stitched,
        "repaired": repaired,
        "eval": eval_report,
        "metadata": metadata,
    }


def select_best_candidate(candidates: list[dict]) -> str:
    """
    Select the best candidate based on evaluation scores.

    Selection criteria (in order):
    1. Pass/fail status (must pass guards and minimum quality threshold)
    2. Overall score (highest wins)
    3. Freshness score (tie-breaker)

    Args:
        candidates: List of candidate dictionaries with eval reports

    Returns:
        ID of the best candidate
    """
    if not candidates:
        raise ValueError("No candidates to select from")

    # Sort by: pass_fail (True first), overall score (desc), freshness (desc)
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (
            c["eval"].pass_fail,
            c["eval"].scores.overall,
            c["eval"].scores.freshness,
        ),
        reverse=True,
    )

    return sorted_candidates[0]["id"]


def generate_candidates(
    spec: StorySpec,
    digest: ExemplarDigest,
    exemplar_text: str,
    n_candidates: int = 3,
    routing_overrides: Optional[dict] = None,
    run_id: Optional[str] = None,
) -> dict:
    """
    Generate N candidate drafts, evaluate them, and select the best.

    Main orchestrator for Phase 6 multi-candidate generation pipeline.

    Args:
        spec: StorySpec with voice, form, and content parameters
        digest: ExemplarDigest for comparison
        exemplar_text: Original exemplar text (for overlap checking)
        n_candidates: Number of candidates to generate (default: 3)
        routing_overrides: Optional routing configuration overrides
        run_id: Optional run identifier (auto-generated if not provided)

    Returns:
        Dictionary with:
            - candidates: List of candidate dicts [{id, beats, stitched, repaired, eval}, ...]
            - best_id: ID of the best candidate
            - meta: Metadata about the run
    """
    # Generate run_id if not provided
    if run_id is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_id = f"run_{timestamp}"

    # Apply routing overrides if provided
    if routing_overrides:
        # Note: Router uses global config, overrides would need to be applied
        # via environment or config file. For now, just note in metadata.
        pass

    # Create GenerationConfig
    config = GenerationConfig()

    # Generate candidates
    candidates = []
    for i in range(n_candidates):
        candidate_id = f"cand_{i+1:03d}"

        candidate = generate_single_candidate(
            spec=spec,
            digest=digest,
            exemplar_text=exemplar_text,
            candidate_id=candidate_id,
            run_id=run_id,
            config=config,
        )

        candidates.append(candidate)

    # Select best candidate
    best_id = select_best_candidate(candidates)

    # Compile metadata
    meta = {
        "run_id": run_id,
        "n_candidates": n_candidates,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "story_id": spec.meta.story_id,
        "routing_overrides": routing_overrides or {},
        "config_hash": hashlib.md5(config.model_dump_json().encode()).hexdigest()[:8],  # noqa: S324
    }

    # Persist to /runs/ directory
    output_dir = Path("runs") / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save each candidate
    for candidate in candidates:
        candidate_dir = output_dir / candidate["id"]
        candidate_dir.mkdir(exist_ok=True)

        # Save repaired text
        with open(candidate_dir / "repaired.txt", "w", encoding="utf-8") as f:
            f.write(candidate["repaired"])

        # Save stitched text
        with open(candidate_dir / "stitched.txt", "w", encoding="utf-8") as f:
            f.write(candidate["stitched"])

        # Save beat results
        with open(candidate_dir / "beat_results.json", "w", encoding="utf-8") as f:
            json.dump(candidate["beats"], f, indent=2, default=str)

        # Save eval report
        with open(candidate_dir / "eval_report.json", "w", encoding="utf-8") as f:
            f.write(candidate["eval"].model_dump_json(indent=2, by_alias=True))

        # Save metadata
        with open(candidate_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(candidate["metadata"], f, indent=2, default=str)

    # Save run metadata
    with open(output_dir / "run_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)

    # Save summary
    summary = {
        "run_id": run_id,
        "best_candidate": best_id,
        "n_candidates": n_candidates,
        "candidate_scores": [
            {
                "id": c["id"],
                "overall": c["eval"].scores.overall,
                "pass_fail": c["eval"].pass_fail,
            }
            for c in candidates
        ],
    }
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return {
        "candidates": candidates,
        "best_id": best_id,
        "meta": meta,
    }
