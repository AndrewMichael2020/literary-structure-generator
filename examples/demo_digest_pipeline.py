#!/usr/bin/env python
"""
Example: Using the ExemplarDigest Pipeline

This script demonstrates how to use the analyze_text function to process
an exemplar text file and generate a structured ExemplarDigest artifact.
"""

from pathlib import Path

from literary_structure_generator.ingest.digest_exemplar import analyze_text


def main() -> None:
    """Run the ExemplarDigest pipeline example."""
    # Path to the exemplar text
    exemplar_path = "data/Emergency.txt"

    # Check if file exists
    if not Path(exemplar_path).exists():
        print(f"Error: File not found: {exemplar_path}")
        return

    print("🔍 Analyzing exemplar text...")
    print(f"   File: {exemplar_path}")
    print()

    # Analyze the text
    digest = analyze_text(exemplar_path)

    # Display results
    print("✅ Analysis complete!")
    print()
    print("=" * 60)
    print("METADATA")
    print("=" * 60)
    print(f"Source:     {digest.meta.source}")
    print(f"Tokens:     {digest.meta.tokens:,}")
    print(f"Paragraphs: {digest.meta.paragraphs}")
    print()

    print("=" * 60)
    print("STYLOMETRY")
    print("=" * 60)
    print(f"Type-Token Ratio:  {digest.stylometry.type_token_ratio:.3f}")
    print(f"Sentence Lengths:  {sum(digest.stylometry.sentence_len_hist)} sentences")
    print(
        f"Function Words:    {len(digest.stylometry.function_word_profile)} profiled"
    )
    print()

    # Show top function words
    print("Top 5 function words:")
    sorted_words = sorted(
        digest.stylometry.function_word_profile.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    for word, freq in sorted_words[:5]:
        print(f"  • {word:10s} {freq:5.2f} per 100 words")
    print()

    print("=" * 60)
    print("DISCOURSE")
    print("=" * 60)
    print(f"Dialogue Ratio:    {digest.discourse.dialogue_ratio:.1%}")
    print(f"Beats:             {len(digest.discourse.beats)}")
    for beat in digest.discourse.beats:
        span_str = f"{beat.span[0]:,}-{beat.span[1]:,}"
        print(f"  • {beat.id:10s} (tokens {span_str:15s}) - {beat.function}")
    print()

    print("=" * 60)
    print("PACING")
    print("=" * 60)
    print(f"Paragraph Lengths: {sum(digest.pacing.paragraph_len_hist)} paragraphs")
    print()

    print("=" * 60)
    print("SAFETY")
    print("=" * 60)
    print(f"Profanity Rate:    {digest.safety.profanity_rate} (Clean Mode)")
    print()

    # Save to file
    output_path = Path("runs/exemplar_digest_emergency.json")
    output_path.parent.mkdir(exist_ok=True)

    with output_path.open("w") as f:
        f.write(digest.model_dump_json(indent=2, by_alias=True))

    print("💾 Saved ExemplarDigest to:", output_path)
    print()


if __name__ == "__main__":
    main()
