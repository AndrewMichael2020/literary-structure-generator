"""
StorySpec Synthesizer

Maps ExemplarDigest to initial StorySpec with tunable parameters.
Blends exemplar style with AuthorProfile preferences.

Workflow:
    1. Load ExemplarDigest
    2. Load AuthorProfile (optional)
    3. Map digest features to StorySpec parameters
    4. Apply blending weights (alpha_exemplar vs alpha_author)
    5. Initialize content section with placeholders
    6. Set anti-plagiarism constraints
    7. Validate and save StorySpec

Each decision is logged via log_decision() for reproducibility.
"""

from typing import Optional

from literary_structure_generator.models.author_profile import AuthorProfile
from literary_structure_generator.models.exemplar_digest import ExemplarDigest
from literary_structure_generator.models.story_spec import StorySpec
from literary_structure_generator.utils.decision_logger import log_decision


def map_voice_parameters(digest: ExemplarDigest, profile: Optional[AuthorProfile] = None) -> dict:
    """
    Map digest stylometry to voice parameters.

    Args:
        digest: ExemplarDigest to map from
        profile: Optional AuthorProfile to blend with

    Returns:
        Dictionary with voice parameters
    """
    # Calculate average sentence length from histogram
    sentence_len_hist = digest.stylometry.sentence_len_hist
    total_sentences = sum(sentence_len_hist)
    if total_sentences > 0:
        # Each bucket represents a range: [1-5, 6-10, 11-15, 16-20, 21-30, 31-40, 41-50, 51-75, 76+]
        bucket_midpoints = [3, 8, 13, 18, 25, 35, 45, 63, 80]
        weighted_sum = sum(
            count * midpoint for count, midpoint in zip(sentence_len_hist, bucket_midpoints)
        )
        avg_sentence_len = round(weighted_sum / total_sentences)
    else:
        avg_sentence_len = 15  # Default

    # Determine narrative person from dialogue ratio and focalization
    dialogue_ratio = digest.discourse.dialogue_ratio
    focalization = digest.discourse.focalization
    if "first" in focalization.lower() or dialogue_ratio > 0.5:
        person = "first"
    elif "third" in focalization.lower():
        person = "third-limited"
    else:
        person = "first"  # Default

    # Determine distance based on sentence length and register
    if avg_sentence_len < 12:
        distance = "intimate"
    elif avg_sentence_len < 18:
        distance = "close"
    else:
        distance = "medium"

    # Build voice parameters
    return {
        "person": person,
        "distance": distance,
        "syntax": {
            "avg_sentence_len": avg_sentence_len,
            "variance": 0.6,  # Default
            "fragment_ok": avg_sentence_len < 15,
            "comma_density": digest.stylometry.punctuation.get("comma_per_100", 50) / 100,
        },
        "dialogue_style": {
            "quote_marks": "double",
            "tag_verbs_allowed": ["said", "asked"],
        },
    }


def map_form_parameters(
    digest: ExemplarDigest,
    run_id: str = "run_001",
    iteration: int = 0,
) -> dict:
    """
    Map digest discourse structure to form parameters.

    Args:
        digest: ExemplarDigest to map from
        run_id: Run identifier for LLM logging
        iteration: Iteration number

    Returns:
        Dictionary with form parameters
    """
    # Convert beats from digest to beat specs
    beat_specs = []
    beat_functions = []

    for beat in digest.discourse.beats:
        span_length = beat.span[1] - beat.span[0]
        # Convert tokens to approximate words (tokens ~= words * 1.3)
        target_words = round(span_length / 1.3)

        # Determine cadence based on beat function
        if "opening" in beat.function.lower() or "closing" in beat.function.lower():
            cadence = "short"
        else:
            cadence = "mixed"

        beat_specs.append(
            {
                "id": beat.id,
                "target_words": target_words,
                "function": beat.function,
                "cadence": cadence,
            }
        )
        beat_functions.append(beat.function)

    # Phase 3.2: LLM-enhanced beat paraphrasing
    # Generate concise beat summaries using LLM
    try:
        from literary_structure_generator.llm.adapters import paraphrase_beats

        if beat_functions:
            beat_summaries = paraphrase_beats(
                beat_functions,
                register_hint="neutral",
                run_id=run_id,
                iteration=iteration,
                use_cache=True,
            )
            # Add summaries to beat specs
            for i, summary in enumerate(beat_summaries):
                if i < len(beat_specs):
                    beat_specs[i]["summary"] = summary
    except Exception:
        # LLM is optional - continue if it fails
        # Add default summaries
        for spec in beat_specs:
            spec["summary"] = spec["function"]

    # Calculate paragraph stats
    para_len_hist = digest.pacing.paragraph_len_hist
    total_paragraphs = sum(para_len_hist)
    if total_paragraphs > 0:
        # Bucket midpoints for paragraph lengths
        bucket_midpoints = [3, 8, 13, 25, 50, 75, 100, 150, 200]
        weighted_sum = sum(
            count * midpoint for count, midpoint in zip(para_len_hist, bucket_midpoints)
        )
        avg_para_len = round(weighted_sum / total_paragraphs)
    else:
        avg_para_len = 45  # Default

    # Build form parameters
    return {
        "structure": "episodic",  # Default for now
        "beat_map": beat_specs,
        "dialogue_ratio": digest.discourse.dialogue_ratio,
        "paragraphing": {
            "avg_len_tokens": avg_para_len,
            "variance": 0.4,
        },
    }


def blend_with_author_profile(
    exemplar_params: dict, profile: AuthorProfile, alpha_exemplar: float = 0.7
) -> dict:
    """
    Blend exemplar parameters with AuthorProfile.

    Args:
        exemplar_params: Parameters extracted from exemplar
        profile: User's AuthorProfile
        alpha_exemplar: Blending weight (0=all author, 1=all exemplar)

    Returns:
        Blended parameters
    """
    # Simple blending: for numeric values, use weighted average
    # For categorical values, prefer exemplar if alpha >= 0.5, else author
    blended = exemplar_params.copy()

    # Blend syntax parameters if available
    if "syntax" in exemplar_params and hasattr(profile, "syntax_preferences"):
        syntax = blended["syntax"]
        author_syntax = profile.syntax_preferences

        # Blend numeric fields
        if "avg_sentence_len" in author_syntax:
            syntax["avg_sentence_len"] = round(
                alpha_exemplar * syntax["avg_sentence_len"]
                + (1 - alpha_exemplar) * author_syntax["avg_sentence_len"]
            )

    # Blend profanity policy
    if hasattr(profile, "profanity_allowed"):
        if "profanity" not in blended:
            blended["profanity"] = {}
        # If author disallows profanity, always respect that
        blended["profanity"]["allowed"] = profile.profanity_allowed and blended.get(
            "profanity", {}
        ).get("allowed", False)

    return blended


def initialize_content_section(setting_prompt: str = "", characters_prompt: str = "") -> dict:
    """
    Initialize content section with placeholders or prompts.

    Args:
        setting_prompt: Optional setting description
        characters_prompt: Optional character descriptions

    Returns:
        Dictionary with content parameters
    """
    # Create basic content structure with placeholders
    content = {
        "setting": {
            "place": setting_prompt or "[to be defined]",
            "time": "[to be defined]",
            "weather_budget": [],
        },
        "characters": [],
        "motifs": [],
        "imagery_palettes": {},
        "sensory_quotas": {
            "visual": 0.4,
            "auditory": 0.2,
            "tactile": 0.2,
            "olfactory": 0.1,
            "gustatory": 0.1,
        },
    }

    # Parse character descriptions if provided
    if characters_prompt:
        # Simple comma-separated character names
        char_names = [name.strip() for name in characters_prompt.split(",")]
        content["characters"] = [
            {"name": name, "role": "[to be defined]"} for name in char_names if name
        ]

    return content


def synthesize_spec(
    digest: ExemplarDigest,
    story_id: str,
    seed: int = 137,
    profile: Optional[AuthorProfile] = None,
    alpha_exemplar: float = 0.7,
    output_path: Optional[str] = None,
    run_id: str = "run_001",
    iteration: int = 0,
) -> StorySpec:
    """
    Main entry point: synthesize StorySpec from ExemplarDigest.

    Args:
        digest: ExemplarDigest to synthesize from
        story_id: Unique identifier for this story
        seed: Random seed for reproducibility
        profile: Optional AuthorProfile to blend with
        alpha_exemplar: Blending weight (0=all author, 1=all exemplar)
        output_path: Optional path to save spec JSON
        run_id: Unique run identifier for logging
        iteration: Iteration number for logging

    Returns:
        Complete StorySpec object
    """
    # Log decision about blending strategy
    log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="SpecSynth",
        decision=f"Use alpha_exemplar={alpha_exemplar} for blending",
        reasoning=(
            f"Blending exemplar digest with author profile using "
            f"{alpha_exemplar:.0%} exemplar weight. "
            f"This balances structural learning from exemplar with "
            f"author's voice preferences."
        ),
        parameters={
            "alpha_exemplar": alpha_exemplar,
            "has_author_profile": profile is not None,
            "seed": seed,
        },
        metadata={"story_id": story_id},
    )

    # Map digest to voice parameters
    voice_params = map_voice_parameters(digest, profile)
    log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="SpecSynth",
        decision=(
            f"Mapped voice: person={voice_params['person']}, "
            f"distance={voice_params['distance']}"
        ),
        reasoning="Extracted voice parameters from digest stylometry and discourse features",
        parameters={"voice_params": voice_params},
        metadata={"stage": "voice_mapping"},
    )

    # Map digest to form parameters
    form_params = map_form_parameters(digest, run_id=run_id, iteration=iteration)
    log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="SpecSynth",
        decision=(
            f"Mapped form: {len(form_params['beat_map'])} beats, "
            f"dialogue_ratio={form_params['dialogue_ratio']:.2f}"
        ),
        reasoning="Extracted form structure from digest discourse and pacing features",
        parameters={"beat_count": len(form_params["beat_map"])},
        metadata={"stage": "form_mapping"},
    )

    # Blend with author profile if provided
    if profile:
        voice_params = blend_with_author_profile(voice_params, profile, alpha_exemplar)
        log_decision(
            run_id=run_id,
            iteration=iteration,
            agent="SpecSynth",
            decision="Blended voice params with author profile",
            reasoning=f"Applied alpha_exemplar={alpha_exemplar} blending",
            parameters={"alpha_exemplar": alpha_exemplar},
            metadata={"stage": "blending"},
        )

    # Initialize content section
    content_params = initialize_content_section()

    # Build StorySpec from mapped parameters
    from literary_structure_generator.models.story_spec import (
        AntiPlagiarism,
        BeatSpec,
        Constraints,
        Content,
        DialogueStyle,
        Form,
        LengthConstraints,
        MetaInfo,
        Paragraphing,
        Profanity,
        Setting,
        Syntax,
        Voice,
    )

    # Create MetaInfo
    meta = MetaInfo(
        story_id=story_id,
        seed=seed,
        version="2.0",
        derived_from={
            "exemplar": digest.meta.source,
            "digest_version": digest.schema_version,
        },
    )

    # Create Voice
    voice = Voice(
        person=voice_params.get("person", "first"),
        distance=voice_params.get("distance", "intimate"),
        syntax=Syntax(**voice_params.get("syntax", {})),
        dialogue_style=DialogueStyle(**voice_params.get("dialogue_style", {})),
        profanity=Profanity(**voice_params.get("profanity", {})),
    )

    # Create Form with BeatSpecs
    beat_specs = [BeatSpec(**beat_data) for beat_data in form_params.get("beat_map", [])]
    form = Form(
        beat_map=beat_specs,
        dialogue_ratio=form_params.get("dialogue_ratio", 0.25),
        paragraphing=Paragraphing(**form_params.get("paragraphing", {})),
    )

    # Create Content
    content = Content(
        setting=Setting(
            **content_params.get("setting", {"place": "[to be defined]", "time": "[to be defined]"})
        ),
        characters=[],
        motifs=content_params.get("motifs", []),
    )

    # Calculate target length from beats
    target_words = sum(beat.target_words for beat in beat_specs) if beat_specs else 2000

    # Create Constraints with anti-plagiarism defaults
    constraints = Constraints(
        anti_plagiarism=AntiPlagiarism(
            max_ngram=12,
            overlap_pct=0.03,
            simhash_hamming_min=18,
        ),
        length_words=LengthConstraints(
            min=round(target_words * 0.8),
            target=target_words,
            max=round(target_words * 1.2),
        ),
    )

    # Build final StorySpec
    spec = StorySpec(
        meta=meta,
        voice=voice,
        form=form,
        content=content,
        constraints=constraints,
    )

    # Save to JSON if output_path provided
    if output_path:
        import json
        from pathlib import Path

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(spec.model_dump(by_alias=True), f, indent=2)

        log_decision(
            run_id=run_id,
            iteration=iteration,
            agent="SpecSynth",
            decision=f"Saved StorySpec to {output_path}",
            reasoning="Persisting synthesized spec for generation phase",
            parameters={"output_path": str(output_path)},
            metadata={"stage": "persistence"},
        )

    log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="SpecSynth",
        decision="Completed StorySpec synthesis",
        reasoning="Successfully mapped digest to spec with all sections populated",
        parameters={
            "story_id": story_id,
            "beat_count": len(beat_specs),
            "target_words": sum(beat.target_words for beat in beat_specs) if beat_specs else 0,
        },
        metadata={"stage": "completion"},
    )

    return spec
