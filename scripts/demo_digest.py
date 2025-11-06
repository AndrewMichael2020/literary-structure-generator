#!/usr/bin/env python
"""
Demo Script: Generate ExemplarDigest from Emergency.txt

This script demonstrates the Phase 2.1 digest pipeline by:
1. Reading data/Emergency.txt
2. Calling analyze_text() to extract structural DNA
3. Saving ExemplarDigest.json to /runs/

Usage:
    python scripts/demo_digest.py
"""

from pathlib import Path

from literary_structure_generator.ingest.digest_exemplar import analyze_text


def main() -> None:
    """Run the digest generation demo."""
    # Path to exemplar file
    exemplar_path = Path("data/Emergency.txt")

    # Validate file exists
    if not exemplar_path.exists():
        print(f"❌ Error: File not found: {exemplar_path}")
        print(f"   Current directory: {Path.cwd()}")
        return

    print("=" * 70)
    print("Phase 2.1 Digest Generation Demo")
    print("=" * 70)
    print()
    print(f"📖 Reading exemplar: {exemplar_path}")
    print()

    # Run analyze_text to generate ExemplarDigest
    print("🔍 Analyzing text (this may take a moment)...")
    digest = analyze_text(
        path=str(exemplar_path),
        run_id="demo_run",
        iteration=0,
        output_dir="runs",
    )

    print("✅ Analysis complete!")
    print()

    # Display summary
    print("=" * 70)
    print("DIGEST SUMMARY")
    print("=" * 70)
    print(f"Source:          {digest.meta.source}")
    print(f"Tokens:          {digest.meta.tokens:,}")
    print(f"Paragraphs:      {digest.meta.paragraphs}")
    print(f"Type-Token:      {digest.stylometry.type_token_ratio:.3f}")
    print(f"Dialogue Ratio:  {digest.discourse.dialogue_ratio:.1%}")
    print(f"Beats:           {len(digest.discourse.beats)}")
    print(f"Entities:        {len(digest.coherence_graph.entities)}")
    print(f"Motifs:          {len(digest.motif_map)}")
    print()

    # Show beat structure
    print("Beat Structure:")
    for beat in digest.discourse.beats:
        span_str = f"{beat.span[0]:,}-{beat.span[1]:,}"
        print(f"  • {beat.id:10s} (tokens {span_str:15s}) - {beat.function}")
    print()

    # Output location
    output_file = Path("runs/demo_run/ExemplarDigest_Emergency.json")
    print(f"💾 Saved to: {output_file}")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
