"""
Draft Generator module

Per-beat story generation with stitching, overlap guard, and repair.

Features:
    - Generate prose for individual beats
    - Stitch beats into coherent story
    - Enforce anti-plagiarism constraints
    - Apply Clean Mode filtering
    - Run repair passes for quality
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from literary_structure_generator.generation.guards import (
    apply_clean_mode_if_needed,
    check_overlap_guard,
)
from literary_structure_generator.generation.repair import repair_text
from literary_structure_generator.llm.router import get_client
from literary_structure_generator.models.story_spec import BeatSpec, StorySpec


def build_beat_prompt(beat_spec: BeatSpec, story_spec: StorySpec) -> str:
    """
    Build prompt for beat generation from templates.

    Args:
        beat_spec: Beat specification
        story_spec: Story specification

    Returns:
        Formatted prompt string
    """
    # Load beat generation prompt template
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "beat_generate.v1.md"

    if prompt_path.exists():
        with open(prompt_path, encoding="utf-8") as f:
            template = f.read()
    else:
        # Fallback minimal template
        template = """# Beat Generation

**Function:** {function}
**Summary:** {summary}
**Target words:** {target_words}

Generate prose for this beat matching the specified voice and style.
"""

    # Extract voice and form parameters
    voice = story_spec.voice
    form = story_spec.form
    content = story_spec.content

    # Format character names
    character_names = ", ".join([c.name for c in content.characters[:5]])

    # Format motifs
    motifs = "\n".join([f"- {m}" for m in content.motifs[:5]])

    # Format imagery
    imagery = "\n".join([f"- {i}" for i in content.imagery_palette[:5]])

    # Format props
    props = ", ".join(content.props[:5])

    # Format register info
    register_info = "\n".join([f"- {k}: {v:.2f}" for k, v in voice.register_sliders.items()])

    # Determine parataxis style
    parataxis_val = voice.syntax.parataxis_vs_hypotaxis
    if parataxis_val > 0.7:
        parataxis_style = "paratactic (coordinate clauses)"
    elif parataxis_val < 0.3:
        parataxis_style = "hypotactic (subordinate clauses)"
    else:
        parataxis_style = "balanced"

    # Format the template
    return template.format(
        function=beat_spec.function,
        summary=beat_spec.summary or beat_spec.function,
        target_words=beat_spec.target_words,
        cadence=beat_spec.cadence,
        person=voice.person,
        distance=voice.distance,
        tense=voice.tense_strategy.primary,
        avg_sentence_len=voice.syntax.avg_sentence_len,
        sentence_variance=voice.syntax.variance,
        parataxis_style=parataxis_style,
        fragments_ok="yes" if voice.syntax.fragment_ok else "no",
        register_info=register_info,
        dialogue_ratio=f"{form.dialogue_ratio:.1%}",
        setting_place=content.setting.place,
        setting_time=content.setting.time,
        character_names=character_names,
        motifs=motifs if motifs else "- (none specified)",
        imagery=imagery if imagery else "- (none specified)",
        props=props if props else "(none)",
    )


def generate_beat_text(
    beat_spec: BeatSpec,
    story_spec: StorySpec,
    memory: dict | None = None,
    exemplar: str | None = None,
    max_retries: int = 2,
) -> dict:
    """
    Generate text for a single beat with overlap guard.

    Args:
        beat_spec: Beat specification
        story_spec: Story specification
        memory: Optional context from previous beats
        exemplar: Optional exemplar text for overlap checking
        max_retries: Maximum regeneration attempts on guard failure

    Returns:
        Dictionary with:
            - text: Generated beat text
            - metadata: Generation metadata (model, tokens, etc.)
            - guard_passed: Whether overlap guard passed
            - attempt: Which attempt succeeded
    """
    if memory is None:
        memory = {}

    client = get_client("beat_generator")

    for attempt in range(max_retries + 1):
        # Build prompt
        prompt = build_beat_prompt(beat_spec, story_spec)

        # Add guidance to avoid overlap on retry
        if attempt > 0 and exemplar:
            prompt += (
                "\n\n**Important:** Avoid phrasing similar to exemplar text. "
                f"Use fresh language and distinct sentence structures. "
                f"This is attempt {attempt + 1}."
            )

        # Generate beat text
        raw_text = client.complete(prompt)

        # Apply clean mode if grit not allowed
        clean_text = apply_clean_mode_if_needed(raw_text, not story_spec.voice.profanity.allowed)

        # Check overlap guard if exemplar provided
        guard_result = {"passed": True, "violations": []}
        if exemplar:
            guard_result = check_overlap_guard(
                clean_text,
                exemplar,
                max_ngram=story_spec.constraints.anti_plagiarism.max_ngram,
                max_overlap_pct=story_spec.constraints.anti_plagiarism.overlap_pct,
                min_simhash_hamming=story_spec.constraints.anti_plagiarism.simhash_hamming_min,
            )

        if guard_result["passed"]:
            # Calculate metadata
            usage = client.get_usage()
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
            text_hash = hashlib.sha256(clean_text.encode()).hexdigest()[:16]

            metadata = {
                "model": client.model,
                "template_version": "beat_generate.v1",
                "params_hash": prompt_hash,
                "input_hash": prompt_hash,
                "checksum": text_hash,
                "tokens": usage,
                "attempt": attempt + 1,
            }

            return {
                "text": clean_text,
                "metadata": metadata,
                "guard_passed": True,
                "attempt": attempt + 1,
            }

    # All attempts failed - return last attempt with warning
    usage = client.get_usage()
    return {
        "text": clean_text,
        "metadata": {
            "model": client.model,
            "template_version": "beat_generate.v1",
            "tokens": usage,
            "attempt": max_retries + 1,
            "warning": "Failed overlap guard - using last attempt",
        },
        "guard_passed": False,
        "attempt": max_retries + 1,
        "guard_result": guard_result,
    }


def stitch_beats(beat_texts: list[str]) -> str:
    """
    Stitch individual beat texts into coherent story.

    Uses simple concatenation with paragraph breaks.
    More sophisticated stitching can be added later.

    Args:
        beat_texts: List of beat text strings

    Returns:
        Stitched story text
    """
    # Join with double newlines for paragraph separation
    return "\n\n".join(beat_texts)


def run_draft_generation(
    spec: StorySpec,
    exemplar: str | None = None,
    output_dir: str | None = None,
) -> dict:
    """
    Run complete draft generation pipeline.

    Process:
        1. Generate text for each beat
        2. Stitch beats together
        3. Run repair pass
        4. Re-check overlap guard
        5. Apply clean mode
        6. Save artifacts

    Args:
        spec: Story specification
        exemplar: Optional exemplar text for overlap checking
        output_dir: Optional output directory (default: /runs/)

    Returns:
        Dictionary with:
            - beats: List of beat results
            - stitched: Stitched story text
            - repaired: Repaired story text (after repair pass)
            - metadata: Generation metadata
            - guard_results: Overlap guard results
    """
    # Generate beats
    beat_results = []
    beat_texts = []

    memory = {}  # Context for beat generation

    for beat_spec in spec.form.beat_map:
        beat_result = generate_beat_text(beat_spec, spec, memory=memory, exemplar=exemplar)
        beat_results.append(beat_result)
        beat_texts.append(beat_result["text"])

        # Update memory for next beat
        memory[beat_spec.id] = {
            "text": beat_result["text"],
            "function": beat_spec.function,
        }

    # Stitch beats
    stitched = stitch_beats(beat_texts)

    # Check stitched text against overlap guard
    stitched_guard = {"passed": True, "violations": []}
    if exemplar:
        stitched_guard = check_overlap_guard(
            stitched,
            exemplar,
            max_ngram=spec.constraints.anti_plagiarism.max_ngram,
            max_overlap_pct=spec.constraints.anti_plagiarism.overlap_pct,
            min_simhash_hamming=spec.constraints.anti_plagiarism.simhash_hamming_min,
        )

    # Apply repair pass if needed
    repair_notes = {"issues": []}
    if not stitched_guard["passed"]:
        repair_notes["issues"].extend(stitched_guard["violations"])

    # Run repair pass
    repaired = repair_text(stitched, spec, notes=repair_notes)

    # Apply clean mode to final text
    final_text = apply_clean_mode_if_needed(repaired, not spec.voice.profanity.allowed)

    # Re-check guard after repair
    final_guard = {"passed": True, "violations": []}
    if exemplar:
        final_guard = check_overlap_guard(
            final_text,
            exemplar,
            max_ngram=spec.constraints.anti_plagiarism.max_ngram,
            max_overlap_pct=spec.constraints.anti_plagiarism.overlap_pct,
            min_simhash_hamming=spec.constraints.anti_plagiarism.simhash_hamming_min,
        )

    # Compile metadata
    metadata = {
        "story_id": spec.meta.story_id,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "num_beats": len(beat_results),
        "total_words": len(final_text.split()),
        "target_words": spec.constraints.length_words.target,
        "stitched_guard": stitched_guard,
        "final_guard": final_guard,
    }

    # Save artifacts if output_dir specified
    if output_dir:
        save_artifacts(
            output_dir,
            spec,
            beat_results,
            stitched,
            repaired,
            final_text,
            metadata,
        )

    return {
        "beats": beat_results,
        "stitched": stitched,
        "repaired": repaired,
        "final": final_text,
        "metadata": metadata,
    }


def save_artifacts(
    output_dir: str,
    spec: StorySpec,
    beat_results: list[dict],
    stitched: str,
    repaired: str,
    final: str,
    metadata: dict,
) -> None:
    """
    Save generation artifacts to disk.

    Args:
        output_dir: Output directory path
        spec: Story specification
        beat_results: Beat generation results
        stitched: Stitched text
        repaired: Repaired text
        final: Final text
        metadata: Generation metadata
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save story spec
    spec_path = output_path / "story_spec.json"
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(spec.model_dump(), f, indent=2)

    # Save beat results
    beats_path = output_path / "beat_results.json"
    with open(beats_path, "w", encoding="utf-8") as f:
        json.dump(beat_results, f, indent=2)

    # Save stitched text
    stitched_path = output_path / "stitched.txt"
    with open(stitched_path, "w", encoding="utf-8") as f:
        f.write(stitched)

    # Save repaired text
    repaired_path = output_path / "repaired.txt"
    with open(repaired_path, "w", encoding="utf-8") as f:
        f.write(repaired)

    # Save final text
    final_path = output_path / "final.txt"
    with open(final_path, "w", encoding="utf-8") as f:
        f.write(final)

    # Save metadata
    metadata_path = output_path / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
