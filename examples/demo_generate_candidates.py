#!/usr/bin/env python
"""
Demo script for Phase 6 multi-candidate generation pipeline.

This script demonstrates how to use the generate_candidates() function
with real LLM API calls (requires API key).

For offline testing, see tests/test_phase6_pipeline.py which uses MockClient.

Usage:
    python examples/demo_generate_candidates.py

Requirements:
    - Set OPENAI_API_KEY environment variable
    - Or configure llm_routing.json for your preferred provider
"""

import json
import os
from pathlib import Path

from literary_structure_generator.models.exemplar_digest import (
    ExemplarDigest,
    MetaInfo as DigestMeta,
)
from literary_structure_generator.models.story_spec import (
    BeatSpec,
    Character,
    Content,
    Form,
    MetaInfo,
    Setting,
    StorySpec,
)
from literary_structure_generator.pipeline.generate_candidates import generate_candidates


def create_demo_spec() -> StorySpec:
    """Create a demo StorySpec."""
    return StorySpec(
        meta=MetaInfo(
            story_id="demo_001",
            seed=42,
        ),
        form=Form(
            beat_map=[
                BeatSpec(
                    id="beat_1",
                    function="establish character in familiar setting",
                    target_words=200,
                    cadence="measured",
                ),
                BeatSpec(
                    id="beat_2",
                    function="introduce conflict or change",
                    target_words=250,
                    cadence="building",
                ),
                BeatSpec(
                    id="beat_3",
                    function="resolve with emotional insight",
                    target_words=150,
                    cadence="reflective",
                ),
            ],
        ),
        content=Content(
            setting=Setting(place="city café", time="autumn evening"),
            characters=[
                Character(name="Maya", role="protagonist"),
                Character(name="Alex", role="friend"),
            ],
            motifs=["connection", "memory", "letting go"],
            imagery_palette=["steam", "amber light", "rain on windows"],
            props=["coffee cup", "phone", "newspaper"],
        ),
    )


def create_demo_digest() -> ExemplarDigest:
    """Create a demo ExemplarDigest."""
    return ExemplarDigest(
        meta=DigestMeta(source="demo_exemplar", tokens=600, paragraphs=8),
        stylometry={
            "sentence_len_hist": [5, 10, 15, 20, 15, 10, 5],
            "type_token_ratio": 0.68,
            "mtld": 80.0,
        },
        discourse={
            "beat_map": [
                {"id": "beat_1", "function": "opening"},
                {"id": "beat_2", "function": "development"},
                {"id": "beat_3", "function": "resolution"},
            ]
        },
        pacing={"paragraph_lengths": [25, 30, 28, 35, 30, 25, 20, 15]},
        coherence={"entity_map": {"Maya": ["she"], "Alex": ["he"]}},
        motifs={"labels": ["connection", "memory", "letting go"]},
        imagery={"palette": ["steam", "amber light", "rain on windows"]},
    )


# Sample exemplar text (for overlap checking)
DEMO_EXEMPLAR = """
The café was almost empty. Maya sat by the window, watching the rain.

"You're thinking about him again," Alex said, sliding into the seat across from her.

She didn't deny it. The steam from her coffee curled upward, disappearing.

"It's been six months," he continued gently.

"I know." Her voice was quiet. Outside, someone hurried past with a newspaper over their head.

Alex reached for her hand. "You can't keep doing this to yourself."

She pulled away, reaching for her phone. No messages. There never were.

The amber light from the street made everything look warmer than it was.
"""


def main():
    """Run the demo."""
    print("=" * 70)
    print("Phase 6 Multi-Candidate Generation Pipeline Demo")
    print("=" * 70)
    print()

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  WARNING: OPENAI_API_KEY not set in environment.")
        print("   This demo will use MockClient for offline testing.")
        print("   For real LLM calls, set OPENAI_API_KEY and configure")
        print("   llm_routing.json with provider='openai'.")
        print()
        use_live = False
    else:
        print("✓ OPENAI_API_KEY found.")
        print("  To use live API, ensure llm_routing.json is configured.")
        print()
        use_live = True

    # Create spec and digest
    print("Creating demo StorySpec and ExemplarDigest...")
    spec = create_demo_spec()
    digest = create_demo_digest()

    print(f"  Story ID: {spec.meta.story_id}")
    print(f"  Beats: {len(spec.form.beat_map)}")
    print(f"  Characters: {', '.join([c.name for c in spec.content.characters])}")
    print(f"  Setting: {spec.content.setting.place}")
    print()

    # Configure number of candidates
    n_candidates = 3
    print(f"Generating {n_candidates} candidate drafts...")
    print("  Each candidate will go through:")
    print("    1. Per-beat generation (using LLM router)")
    print("    2. Stitch beats together")
    print("    3. Guards (overlap, SimHash, grit)")
    print("    4. Repair pass (using LLM router)")
    print("    5. Evaluate (Phase 5 orchestrator)")
    print()

    # Generate candidates
    result = generate_candidates(
        spec=spec,
        digest=digest,
        exemplar_text=DEMO_EXEMPLAR,
        n_candidates=n_candidates,
        run_id="demo_run_001",
    )

    print("✓ Generation complete!")
    print()

    # Show results
    print("=" * 70)
    print("Results Summary")
    print("=" * 70)
    print()
    print(f"Run ID: {result['meta']['run_id']}")
    print(f"Candidates generated: {len(result['candidates'])}")
    print(f"Best candidate: {result['best_id']}")
    print()

    # Show candidate scores
    print("Candidate Scores:")
    print("-" * 70)
    for candidate in result["candidates"]:
        cand_id = candidate["id"]
        eval_report = candidate["eval"]
        scores = eval_report.scores

        marker = "🏆" if cand_id == result["best_id"] else "  "
        pass_mark = "✓" if eval_report.pass_fail else "✗"

        print(f"{marker} {cand_id} [{pass_mark}]:")
        print(f"     Overall: {scores.overall:.3f}")
        print(f"     Stylefit: {scores.stylefit:.3f}")
        print(f"     Formfit: {scores.formfit:.3f}")
        print(f"     Coherence: {scores.coherence:.3f}")
        print(f"     Freshness: {scores.freshness:.3f}")
        print(f"     Cadence: {scores.cadence:.3f}")

        if eval_report.red_flags:
            print(f"     Red flags: {len(eval_report.red_flags)}")
        print()

    # Show output location
    output_dir = Path("runs") / result["meta"]["run_id"]
    print("=" * 70)
    print("Output Files")
    print("=" * 70)
    print()
    print(f"All artifacts saved to: {output_dir}")
    print()
    print("Files:")
    print(f"  - run_metadata.json  (run metadata)")
    print(f"  - summary.json       (candidate scores)")
    print()

    for candidate in result["candidates"]:
        cand_dir = output_dir / candidate["id"]
        print(f"  {candidate['id']}/")
        print(f"    - repaired.txt       (final text)")
        print(f"    - stitched.txt       (before repair)")
        print(f"    - beat_results.json  (per-beat generation)")
        print(f"    - eval_report.json   (evaluation report)")
        print(f"    - metadata.json      (generation metadata)")

    print()

    # Show best candidate preview
    best_candidate = next(c for c in result["candidates"] if c["id"] == result["best_id"])
    best_text = best_candidate["repaired"]

    print("=" * 70)
    print("Best Candidate Preview")
    print("=" * 70)
    print()
    print(best_text[:500] + "..." if len(best_text) > 500 else best_text)
    print()

    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print(f"Full text available at: {output_dir / result['best_id'] / 'repaired.txt'}")
    print()


if __name__ == "__main__":
    main()
