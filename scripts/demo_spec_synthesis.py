#!/usr/bin/env python
"""
Demo Script: Synthesize StorySpec from ExemplarDigest

This script demonstrates Phase 3 by:
1. Loading or generating an ExemplarDigest from Emergency.txt
2. Synthesizing a StorySpec from the digest
3. Saving the StorySpec JSON to /runs/

Usage:
    python scripts/demo_spec_synthesis.py
"""

from pathlib import Path

from literary_structure_generator.ingest.digest_exemplar import analyze_text
from literary_structure_generator.spec.synthesizer import synthesize_spec


def main() -> None:
    """Run the spec synthesis demo."""
    print("=" * 70)
    print("Phase 3: StorySpec Synthesis Demo")
    print("=" * 70)
    print()

    # Step 1: Generate or load digest
    exemplar_path = Path("data/Emergency.txt")
    if not exemplar_path.exists():
        print(f"❌ Error: File not found: {exemplar_path}")
        return

    print("Step 1: Analyzing exemplar text...")
    digest = analyze_text(
        path=str(exemplar_path), run_id="spec_demo", iteration=0, output_dir="runs"
    )
    print(f"✅ Digest created: {digest.meta.source}")
    print()

    # Step 2: Synthesize spec
    print("Step 2: Synthesizing StorySpec...")
    spec = synthesize_spec(
        digest=digest,
        story_id="demo_story_001",
        seed=137,
        alpha_exemplar=0.7,
        output_path="runs/spec_demo/StorySpec_demo_story_001.json",
        run_id="spec_demo",
        iteration=0,
    )
    print("✅ StorySpec synthesized!")
    print()

    # Display summary
    print("=" * 70)
    print("STORYSPEC SUMMARY")
    print("=" * 70)
    print(f"Story ID:        {spec.meta.story_id}")
    print(f"Seed:            {spec.meta.seed}")
    print(f"Derived from:    {spec.meta.derived_from.get('exemplar', 'unknown')}")
    print()
    print("VOICE:")
    print(f"  Person:        {spec.voice.person}")
    print(f"  Distance:      {spec.voice.distance}")
    print(f"  Avg sent len:  {spec.voice.syntax.avg_sentence_len} words")
    print()
    print("FORM:")
    print(f"  Beats:         {len(spec.form.beat_map)}")
    print(f"  Dialogue:      {spec.form.dialogue_ratio:.1%}")
    print(f"  Target words:  {spec.constraints.length_words.target:,}")
    print()

    print("Beat Map:")
    for beat in spec.form.beat_map:
        print(f"  • {beat.id:10s} ({beat.target_words:4d} words) - {beat.function}")
    print()

    print("CONSTRAINTS:")
    print(f"  Max overlap:   {spec.constraints.anti_plagiarism.overlap_pct:.1%}")
    print(f"  Max n-gram:    {spec.constraints.anti_plagiarism.max_ngram} tokens")
    print(f"  Min SimHash:   {spec.constraints.anti_plagiarism.simhash_hamming_min}")
    print()

    output_file = Path("runs/spec_demo/StorySpec_demo_story_001.json")
    print(f"💾 Saved to: {output_file}")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
