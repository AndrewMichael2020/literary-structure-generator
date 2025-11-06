#!/usr/bin/env python3
"""
Demo script for Phase 4 draft generation.

Shows how to:
1. Create a StorySpec
2. Run per-beat draft generation
3. Apply overlap guards and clean mode
4. Run repair pass
5. Save artifacts
"""

from pathlib import Path

from literary_structure_generator.generation.draft_generator import run_draft_generation
from literary_structure_generator.models.story_spec import (
    BeatSpec,
    Character,
    Content,
    MetaInfo,
    Setting,
    StorySpec,
)


def main():
    """Run draft generation demo."""
    print("=== Phase 4 Draft Generation Demo ===\n")

    # Create a simple story spec
    spec = StorySpec(
        meta=MetaInfo(
            story_id="demo_story",
            seed=137,
            version="2.0",
        ),
        content=Content(
            setting=Setting(
                place="A small hospital in Iowa",
                time="Late autumn, 1973",
            ),
            characters=[
                Character(
                    name="Dr. Sarah Chen",
                    role="protagonist",
                    goal="Help her patients heal",
                    wound="Lost a patient years ago",
                ),
                Character(
                    name="Mr. Thompson",
                    role="patient",
                    goal="Recover from surgery",
                ),
            ],
            motifs=["healing", "autumn", "transitions"],
            imagery_palette=["amber light", "white walls", "fallen leaves"],
            props=["stethoscope", "window"],
        ),
    )

    # Define beats
    spec.form.beat_map = [
        BeatSpec(
            id="beat_1",
            target_words=200,
            function="establish setting and introduce protagonist",
            cadence="mixed",
            summary="Dr. Chen begins her rounds on a quiet autumn morning",
        ),
        BeatSpec(
            id="beat_2",
            target_words=250,
            function="develop character and reveal wound",
            cadence="long",
            summary="A conversation with Mr. Thompson stirs old memories",
        ),
        BeatSpec(
            id="beat_3",
            target_words=150,
            function="resolution and reflection",
            cadence="short",
            summary="Evening light, quiet understanding",
        ),
    ]

    print(f"Story ID: {spec.meta.story_id}")
    print(f"Setting: {spec.content.setting.place}, {spec.content.setting.time}")
    print(f"Characters: {', '.join(c.name for c in spec.content.characters)}")
    print(f"Beats: {len(spec.form.beat_map)}")
    print()

    # Run draft generation
    print("Generating draft...")
    output_dir = Path("runs") / spec.meta.story_id

    result = run_draft_generation(
        spec,
        exemplar=None,  # No exemplar for this demo
        output_dir=str(output_dir),
    )

    print(f"\n✓ Generated {len(result['beats'])} beats")
    print(f"✓ Total words: {result['metadata']['total_words']}")
    print(f"✓ Target words: {result['metadata']['target_words']}")

    # Show a snippet of the stitched text (before repair)
    stitched_text = result["stitched"]
    snippet = stitched_text[:500] + "..." if len(stitched_text) > 500 else stitched_text

    print(f"\n--- Stitched Story (snippet) ---")
    print(snippet)
    print()

    print(f"\n✓ Artifacts saved to: {output_dir}")
    print(f"  - story_spec.json")
    print(f"  - beat_results.json")
    print(f"  - stitched.txt")
    print(f"  - repaired.txt")
    print(f"  - final.txt")
    print(f"  - metadata.json")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
