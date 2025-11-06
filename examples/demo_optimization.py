#!/usr/bin/env python3
"""
Demo: Phase 7 Optimization Loop

Demonstrates the iterative optimization engine that refines StorySpec and
GenerationConfig over multiple rounds using evaluation feedback.

Usage:
    # Offline mode (default, uses MockClient):
    python examples/demo_optimization.py

    # With real LLM (requires OPENAI_API_KEY):
    OPENAI_API_KEY=xxx python examples/demo_optimization.py --live

The optimizer will:
1. Generate candidates with current spec/config
2. Evaluate each candidate
3. Adjust spec based on feedback
4. Repeat until improvement plateaus or max iterations reached
5. Save all artifacts to /runs/{run_id}/
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from literary_structure_generator.models.exemplar_digest import (
    ExemplarDigest,
)
from literary_structure_generator.models.exemplar_digest import (
    MetaInfo as DigestMeta,
)
from literary_structure_generator.models.generation_config import GenerationConfig
from literary_structure_generator.models.story_spec import (
    BeatSpec,
    Character,
    Content,
    Form,
    MetaInfo,
    Setting,
    StorySpec,
)
from literary_structure_generator.optimization.optimizer import Optimizer


def main():
    """Run optimization demo."""
    # Check for --live flag
    use_live = "--live" in sys.argv

    print("=" * 80)
    print("Phase 7: Optimization Loop Demo")
    print("=" * 80)
    print()

    if use_live:
        print("🔴 LIVE MODE: Using real LLM for generation")
        print("   (requires OPENAI_API_KEY environment variable)")
        print("   Note: This will consume API credits!")
    else:
        print("🟢 OFFLINE MODE: Using MockClient for all operations")
        print("   (No API key required)")
    print()

    # Create initial story spec
    spec = StorySpec(
        meta=MetaInfo(
            story_id="opt_demo_001",
            seed=137,
            version="2.0",
            derived_from={"exemplar": "Emergency", "digest_version": 2},
        ),
        content=Content(
            setting=Setting(
                place="Rural Emergency Room, Iowa",
                time="Winter Night, 1995",
                weather_budget=["snow", "ice", "darkness"],
            ),
            characters=[
                Character(
                    name="Dr. Katherine Walsh",
                    role="protagonist",
                    goal="Save a critical patient",
                    wound="Lost her mother to preventable medical error",
                    quirks=["obsessively checks equipment", "quotes textbooks under stress"],
                    diction_quirks=["terse medical jargon", "clipped sentences"],
                ),
                Character(
                    name="Nurse Emma Rodriguez",
                    role="ally",
                    goal="Support Dr. Walsh through the crisis",
                    quirks=["hums when anxious", "exceptional memory for protocols"],
                ),
                Character(
                    name="Jake Miller",
                    role="patient",
                    goal="survive",
                ),
            ],
            motifs=["time", "snow", "light", "distance", "failure", "redemption"],
            imagery_palette=[
                "fluorescent lights",
                "beeping monitors",
                "sterile corridors",
                "frost on windows",
                "amber warning lights",
                "falling snow",
            ],
            props=["defibrillator", "ambulance", "monitors", "IV bags"],
        ),
        form=Form(
            beat_map=[
                BeatSpec(
                    id="cold_open",
                    target_words=100,
                    function="hook - establish tone and urgency",
                    cadence="short",
                    summary="Late night call, empty ER, tension rising",
                ),
                BeatSpec(
                    id="inciting_incident",
                    target_words=120,
                    function="catalyst - introduce crisis",
                    cadence="mixed",
                    summary="Critical patient arrives, equipment issues",
                ),
                BeatSpec(
                    id="rising_action",
                    target_words=130,
                    function="complications - stakes escalate",
                    cadence="mixed",
                    summary="Multiple failures, personal stakes revealed",
                ),
                BeatSpec(
                    id="crisis",
                    target_words=100,
                    function="crisis - moment of maximum tension",
                    cadence="short",
                    summary="Equipment fails at critical moment",
                ),
                BeatSpec(
                    id="climax",
                    target_words=90,
                    function="climax - decisive action",
                    cadence="short",
                    summary="Doctor makes life-or-death decision",
                ),
                BeatSpec(
                    id="resolution",
                    target_words=80,
                    function="denouement - aftermath and meaning",
                    cadence="long",
                    summary="Patient stabilizes, reflection on the night",
                ),
            ],
            dialogue_ratio=0.20,
        ),
    )

    # Create exemplar digest (minimal for demo)
    digest = ExemplarDigest(
        meta=DigestMeta(
            source="Emergency by Denis Johnson",
            tokens=3200,
            paragraphs=78,
        ),
    )

    # Create exemplar text (different content to avoid overlap)
    exemplar_text = """
The bar was dim. Music played from somewhere unseen. A woman sat alone at the counter.

Outside, the city continued its relentless rhythm. Inside, time seemed suspended.

He remembered the summer they first met. Hot pavement, distant thunder, the smell of rain.
Now winter had arrived, bringing silence and cold.

The bartender poured another drink. Glasses clinked. Conversations murmured.

Decisions had to be made. Some paths led forward, others circled back. In the end,
nothing changed. Everything changed.

The neon sign flickered. Red, blue, red again. Patterns in the darkness.
""" * 30  # Repeat to make realistic length

    # Create generation config
    config = GenerationConfig(
        seed=137,
        num_candidates=4,
        objective_weights={
            "stylefit": 0.30,
            "formfit": 0.30,
            "coherence": 0.25,
            "freshness": 0.10,
            "cadence": 0.05,
        },
    )

    # Create optimizer
    print("🔧 Initializing optimizer...")
    print()
    optimizer = Optimizer(
        max_iters=3,  # Keep it short for demo
        candidates=2,  # 2 candidates per iteration
        early_stop_delta=0.01,
        run_id="demo_opt_001",
    )

    print("Configuration:")
    print(f"  Max iterations:     {optimizer.max_iters}")
    print(f"  Candidates/iter:    {optimizer.candidates}")
    print(f"  Early stop delta:   {optimizer.early_stop_delta}")
    print(f"  Run ID:             {optimizer.run_id}")
    print()

    # Run optimization
    print("=" * 80)
    print("🚀 Starting optimization loop...")
    print("=" * 80)
    print()
    print("Each iteration will:")
    print("  1. Generate candidate drafts with current spec")
    print("  2. Evaluate each candidate")
    print("  3. Select best candidate")
    print("  4. Adjust spec based on evaluation feedback")
    print("  5. Repeat (or stop if improvement plateaus)")
    print()
    print("This may take a few minutes...")
    print()

    result = optimizer.run(
        spec=spec,
        digest=digest,
        exemplar_text=exemplar_text,
        config=config,
        output_dir="runs",
    )

    # Display results
    print()
    print("=" * 80)
    print("✅ OPTIMIZATION COMPLETE")
    print("=" * 80)
    print()

    print(f"Run ID: {optimizer.run_id}")
    print(f"Iterations completed: {len(result['history'])}")
    print(f"Best score achieved: {result['best_score']:.4f}")
    print()

    print("SCORE PROGRESSION:")
    for i, hist in enumerate(result["history"]):
        print(f"  Iteration {i}: {hist['best_score']:.4f}")
        if i > 0:
            improvement = hist["best_score"] - result["history"][i - 1]["best_score"]
            symbol = "↑" if improvement > 0 else "↓" if improvement < 0 else "→"
            print(f"              {symbol} {abs(improvement):.4f}")
    print()

    # Show best report details if available
    if result["best_report"]:
        report = result["best_report"]
        print("BEST CANDIDATE SCORES:")
        print(f"  Overall:         {report.scores.overall:.3f}")
        print(f"  Stylefit:        {report.scores.stylefit:.3f}")
        print(f"  Formfit:         {report.scores.formfit:.3f}")
        print(f"  Coherence:       {report.scores.coherence:.3f}")
        print(f"  Freshness:       {report.scores.freshness:.3f}")
        print(f"  Cadence:         {report.scores.cadence:.3f}")
        print()

        if report.scores.overlap_guard:
            print("OVERLAP GUARD:")
            print(f"  Max N-gram:      {report.scores.overlap_guard.max_ngram}")
            print(f"  Overlap %:       {report.scores.overlap_guard.overlap_pct:.1%}")
            print()

    # Show artifacts saved
    print("📁 ARTIFACTS SAVED:")
    artifacts_dir = Path("runs") / optimizer.run_id
    if artifacts_dir.exists():
        print(f"  Directory: {artifacts_dir}")
        print("  Files:")

        # List key files
        for file_path in sorted(artifacts_dir.glob("*")):
            if file_path.is_file():
                print(f"    - {file_path.name}")

        # List iteration directories
        iter_dirs = sorted(artifacts_dir.glob("iter_*"))
        if iter_dirs:
            print(f"  Iteration directories: {len(iter_dirs)}")
            for iter_dir in iter_dirs:
                print(f"    - {iter_dir.name}/")
    print()

    # Show excerpt from best draft if available
    if result["best_draft"] and result["best_draft"].get("text"):
        text = result["best_draft"]["text"]
        excerpt_len = min(300, len(text))
        print("📝 BEST DRAFT (excerpt):")
        print("-" * 80)
        print(text[:excerpt_len])
        if len(text) > excerpt_len:
            print("...")
        print("-" * 80)
        print()

    # Show optimization summary
    summary_path = artifacts_dir / "optimization_summary.json"
    if summary_path.exists():
        with open(summary_path, encoding="utf-8") as f:
            summary = json.load(f)

        print("📊 OPTIMIZATION SUMMARY:")
        print(json.dumps(summary, indent=2))
        print()

    print("=" * 80)
    print("Demo complete!")
    print()

    if not use_live:
        print("💡 Tip: Run with --live flag to use real LLM for generation")
        print("   (requires OPENAI_API_KEY environment variable)")
        print("   WARNING: This will consume API credits!")

    print()


if __name__ == "__main__":
    main()
