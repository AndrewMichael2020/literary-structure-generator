"""
Full Pipeline Orchestrator

End-to-end story generation workflow.

Workflow:
    1. Load exemplar text
    2. Generate ExemplarDigest (or load from cache)
    3. Load/create AuthorProfile
    4. Synthesize StorySpec
    5. Run candidate generation without optimizer:
        a. Generate candidate ensemble
        b. Evaluate all candidates
        c. Select best
    6. Save final story and all artifacts

CLI interface for running complete workflow.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from literary_structure_generator.ingest.digest_exemplar import analyze_text
from literary_structure_generator.models.exemplar_digest import ExemplarDigest
from literary_structure_generator.models.generation_config import GenerationConfig
from literary_structure_generator.pipeline.generate_candidates import generate_candidates
from literary_structure_generator.profiles.author_profile import (
    create_default_profile,
    load_profile,
    save_profile,
    validate_profile,
)
from literary_structure_generator.spec.synthesizer import synthesize_spec
from literary_structure_generator.utils.decision_logger import log_decision
from literary_structure_generator.utils.io_utils import (
    create_artifact_structure,
    load_json,
    load_text_file,
    save_json,
    save_text_file,
)


def _safe_run_id(story_id: str, seed: int) -> str:
    """Create a filesystem-safe run ID."""
    safe_story_id = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in story_id)
    return f"{safe_story_id}_seed{seed}"


def _digest_cache_path(paths: dict[str, Path], exemplar_path: str) -> Path:
    """Return the digest cache path for an exemplar."""
    source_name = Path(exemplar_path).stem
    return paths["digests"] / f"ExemplarDigest_{source_name}.json"


def _write_pipeline_summary(
    paths: dict[str, Path],
    result: dict[str, Any],
    final_story_path: Path,
) -> Path:
    """Persist a lightweight JSON summary for the full pipeline run."""
    summary = {
        "run_id": result["run_id"],
        "story_id": result["spec"].meta.story_id,
        "best_id": result["best_id"],
        "final_story_path": str(final_story_path),
        "candidate_count": len(result["candidates"]),
        "best_score": result["best_eval"].scores.overall,
        "best_pass_fail": result["best_eval"].pass_fail,
        "digest_source": result["digest"].meta.source,
        "config": result["config"].model_dump(mode="json", by_alias=True),
    }

    summary_path = paths["root"] / "pipeline_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def run_pipeline(
    exemplar_path: str,
    author_profile_path: str | None = None,
    story_id: str = "story_001",
    seed: int = 137,
    output_dir: str = "artifacts/",
    num_iterations: int = 10,
    num_candidates: int = 8,
    use_cache: bool = True,
) -> dict:
    """
    Run full story generation pipeline.

    Args:
        exemplar_path: Path to exemplar text file
        author_profile_path: Optional path to AuthorProfile JSON
        story_id: Unique identifier for this story
        seed: Random seed for reproducibility
        output_dir: Directory for saving artifacts
        num_iterations: Maximum optimization iterations
        num_candidates: Number of candidates per iteration
        use_cache: Whether to use cached digest

    Returns:
        Dictionary with final story, spec, config, and best eval report
    """
    run_id = _safe_run_id(story_id, seed)
    paths = create_artifact_structure(output_dir, run_id)

    log_decision(
        run_id=run_id,
        iteration=0,
        agent="Pipeline",
        decision="Start full pipeline",
        reasoning="Running digest, profile, spec synthesis, candidate generation, and selection",
        parameters={
            "exemplar_path": exemplar_path,
            "author_profile_path": author_profile_path,
            "story_id": story_id,
            "seed": seed,
            "num_iterations": num_iterations,
            "num_candidates": num_candidates,
            "use_cache": use_cache,
        },
        output_dir=output_dir,
    )

    exemplar_text = load_text_file(exemplar_path)

    digest_path = _digest_cache_path(paths, exemplar_path)
    if use_cache and digest_path.exists():
        digest = load_json(str(digest_path), ExemplarDigest)
        digest_source = "cache"
    else:
        digest = analyze_text(exemplar_path, run_id=run_id, iteration=0)
        save_json(digest, str(digest_path))
        digest_source = "generated"

    log_decision(
        run_id=run_id,
        iteration=0,
        agent="Pipeline",
        decision=f"Loaded digest from {digest_source}",
        reasoning="Digest is required to synthesize structural and stylistic constraints",
        parameters={"digest_path": str(digest_path)},
        output_dir=output_dir,
    )

    if author_profile_path:
        profile = load_profile(author_profile_path)
        profile_output_path = paths["configs"] / "AuthorProfile.loaded.json"
    else:
        profile = create_default_profile()
        profile_output_path = paths["configs"] / "AuthorProfile.default.json"

    validate_profile(profile)
    save_profile(profile, str(profile_output_path))

    spec_path = paths["specs"] / f"StorySpec_{story_id}.json"
    spec = synthesize_spec(
        digest=digest,
        story_id=story_id,
        seed=seed,
        profile=profile,
        alpha_exemplar=0.7,
        output_path=str(spec_path),
        run_id=run_id,
        iteration=0,
    )

    config = GenerationConfig(seed=seed, num_candidates=num_candidates)
    config.optimizer.max_iters = num_iterations
    config_path = paths["configs"] / "GenerationConfig.json"
    save_json(config, str(config_path))

    candidates_result = generate_candidates(
        spec=spec,
        digest=digest,
        exemplar_text=exemplar_text,
        n_candidates=num_candidates,
        run_id=run_id,
        config=config,
        output_dir=output_dir,
    )

    best_id = candidates_result["best_id"]
    best_candidate = next(
        candidate for candidate in candidates_result["candidates"] if candidate["id"] == best_id
    )

    final_story = best_candidate["repaired"]
    final_story_path = paths["final"] / "final_story.txt"
    save_text_file(final_story, str(final_story_path))

    best_eval_path = paths["reports"] / "best_eval_report.json"
    best_eval_path.write_text(
        best_candidate["eval"].model_dump_json(indent=2, by_alias=True),
        encoding="utf-8",
    )

    result = {
        "run_id": run_id,
        "final_story": final_story,
        "final_story_path": str(final_story_path),
        "digest": digest,
        "digest_path": str(digest_path),
        "profile": profile,
        "profile_path": str(profile_output_path),
        "spec": spec,
        "spec_path": str(spec_path),
        "config": config,
        "config_path": str(config_path),
        "candidates": candidates_result["candidates"],
        "best_id": best_id,
        "best_eval": best_candidate["eval"],
        "best_candidate": best_candidate,
        "candidate_meta": candidates_result["meta"],
        "artifacts": {key: str(value) for key, value in paths.items()},
    }

    summary_path = _write_pipeline_summary(paths, result, final_story_path)
    result["summary_path"] = str(summary_path)

    log_decision(
        run_id=run_id,
        iteration=0,
        agent="Pipeline",
        decision=f"Completed full pipeline; selected {best_id}",
        reasoning="Selected highest-ranked candidate according to evaluation report",
        parameters={
            "best_id": best_id,
            "best_score": best_candidate["eval"].scores.overall,
            "pass_fail": best_candidate["eval"].pass_fail,
            "final_story_path": str(final_story_path),
        },
        output_dir=output_dir,
    )

    return result


def main() -> None:
    """
    CLI entry point for full pipeline.
    """
    parser = argparse.ArgumentParser(description="Literary Structure Generator - Full Pipeline")
    parser.add_argument(
        "--exemplar",
        required=True,
        help="Path to exemplar text file",
    )
    parser.add_argument(
        "--author-profile",
        help="Path to AuthorProfile JSON (optional)",
    )
    parser.add_argument(
        "--story-id",
        default="story_001",
        help="Unique identifier for this story",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=137,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/",
        help="Directory for saving artifacts",
    )
    parser.add_argument(
        "--num-iterations",
        type=int,
        default=10,
        help="Maximum optimization iterations",
    )
    parser.add_argument(
        "--num-candidates",
        type=int,
        default=8,
        help="Number of candidates per iteration",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable digest caching",
    )

    args = parser.parse_args()

    result = run_pipeline(
        exemplar_path=args.exemplar,
        author_profile_path=args.author_profile,
        story_id=args.story_id,
        seed=args.seed,
        output_dir=args.output_dir,
        num_iterations=args.num_iterations,
        num_candidates=args.num_candidates,
        use_cache=not args.no_cache,
    )

    cli_summary = {
        "run_id": result["run_id"],
        "story_id": result["spec"].meta.story_id,
        "best_id": result["best_id"],
        "best_score": result["best_eval"].scores.overall,
        "pass_fail": result["best_eval"].pass_fail,
        "final_story_path": result["final_story_path"],
        "summary_path": result["summary_path"],
    }

    sys.stdout.write(f"{json.dumps(cli_summary, indent=2)}\n")


if __name__ == "__main__":
    main()
