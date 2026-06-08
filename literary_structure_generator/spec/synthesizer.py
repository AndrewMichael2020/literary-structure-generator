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

import json
from pathlib import Path
from typing import Any

from literary_structure_generator.models.author_profile import AuthorProfile
from literary_structure_generator.models.exemplar_digest import ExemplarDigest
from literary_structure_generator.models.story_spec import StorySpec
from literary_structure_generator.utils.decision_logger import log_decision


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Clamp numeric value to inclusive bounds."""
    return max(minimum, min(maximum, value))


def _estimate_average_from_histogram(
    histogram: list[int],
    bucket_midpoints: list[int],
    default: int,
) -> int:
    """Estimate an average from a histogram and bucket midpoints."""
    total = sum(histogram)
    if total <= 0:
        return default

    weighted_sum = sum(
        count * midpoint for count, midpoint in zip(histogram, bucket_midpoints, strict=False)
    )
    return round(weighted_sum / total)


def map_voice_parameters(digest: ExemplarDigest, _profile: AuthorProfile | None = None) -> dict:
    """
    Map digest stylometry to voice parameters.

    Args:
        digest: ExemplarDigest to map from
        profile: Optional AuthorProfile to blend with

    Returns:
        Dictionary with voice parameters
    """
    avg_sentence_len = _estimate_average_from_histogram(
        digest.stylometry.sentence_len_hist,
        [3, 8, 13, 18, 25, 35, 45, 63, 80],
        15,
    )

    dialogue_ratio = digest.discourse.dialogue_ratio
    focalization = digest.discourse.focalization or ""

    if "third" in focalization.lower():
        person = "third-limited"
    elif "omniscient" in focalization.lower():
        person = "omniscient"
    elif "second" in focalization.lower():
        person = "second"
    else:
        person = "first"

    if avg_sentence_len < 12:
        distance = "intimate"
    elif avg_sentence_len < 18:
        distance = "close"
    else:
        distance = "medium"

    punctuation = digest.stylometry.punctuation
    comma_density = punctuation.get("comma_per_100", 0.55)
    if comma_density > 1:
        comma_density = comma_density / 100

    dash_density = punctuation.get("dash_per_100", 0.0)
    if dash_density >= 1.0:
        em_dash = "frequent"
    elif dash_density >= 0.25:
        em_dash = "moderate"
    else:
        em_dash = "rare"

    return {
        "person": person,
        "distance": distance,
        "register": {
            "lyric": 0.3,
            "deadpan": 0.7,
            "irony": 0.5,
            "tender": 0.6,
        },
        "syntax": {
            "avg_sentence_len": avg_sentence_len,
            "variance": 0.6,
            "fragment_ok": avg_sentence_len < 15,
            "comma_density": _clamp(comma_density),
            "em_dash": em_dash,
        },
        "dialogue_style": {
            "quote_marks": "double",
            "tag_verbs_allowed": ["said", "asked"],
        },
        "profanity": {
            "allowed": False,
            "frequency": 0.0,
        },
        "dialogue_ratio_hint": dialogue_ratio,
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
    beat_specs = []
    beat_functions = []

    source_beats = digest.discourse.beats
    if not source_beats:
        total_tokens = max(digest.meta.tokens, 1500)
        source_beats = [
            {
                "id": "opening",
                "span": [0, round(total_tokens * 0.25)],
                "function": "establish setting, character, and tone",
            },
            {
                "id": "middle",
                "span": [round(total_tokens * 0.25), round(total_tokens * 0.75)],
                "function": "develop conflict and deepen stakes",
            },
            {
                "id": "closing",
                "span": [round(total_tokens * 0.75), total_tokens],
                "function": "resolve the central emotional movement",
            },
        ]

    for beat in source_beats:
        if isinstance(beat, dict):
            beat_id = beat.get("id", f"beat_{len(beat_specs) + 1}")
            span = beat.get("span", [0, 260])
            function = beat.get("function", "advance the story")
        else:
            beat_id = beat.id
            span = beat.span
            function = beat.function

        span_start = span[0] if len(span) > 0 else 0
        span_end = span[1] if len(span) > 1 else span_start + 260
        span_length = max(120, span_end - span_start)
        target_words = max(120, round(span_length / 1.3))

        if "opening" in function.lower() or "closing" in function.lower():
            cadence = "short"
        elif "conflict" in function.lower() or "action" in function.lower():
            cadence = "mixed"
        else:
            cadence = "measured"

        beat_specs.append(
            {
                "id": beat_id,
                "target_words": target_words,
                "function": function,
                "cadence": cadence,
                "summary": function,
            }
        )
        beat_functions.append(function)

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
            for i, summary in enumerate(beat_summaries):
                if i < len(beat_specs):
                    beat_specs[i]["summary"] = summary
    except Exception:
        for spec in beat_specs:
            spec["summary"] = spec["function"]

    avg_para_len = _estimate_average_from_histogram(
        digest.pacing.paragraph_len_hist,
        [10, 30, 50, 70, 90, 125, 175, 225, 275],
        45,
    )

    return {
        "structure": "episodic",
        "beat_map": beat_specs,
        "dialogue_ratio": digest.discourse.dialogue_ratio or 0.25,
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
    if not 0.0 <= alpha_exemplar <= 1.0:
        raise ValueError("alpha_exemplar must be between 0.0 and 1.0")

    blended = {
        key: value.copy() if isinstance(value, dict) else value
        for key, value in exemplar_params.items()
    }

    syntax = blended.setdefault("syntax", {})
    syntax["avg_sentence_len"] = round(
        alpha_exemplar * syntax.get("avg_sentence_len", 15)
        + (1.0 - alpha_exemplar) * profile.syntax.avg_sentence_len
    )
    syntax["variance"] = (
        alpha_exemplar * syntax.get("variance", 0.6)
        + (1.0 - alpha_exemplar) * profile.syntax.variance
    )

    if alpha_exemplar < 0.5:
        syntax["em_dash"] = profile.syntax.em_dash

    exemplar_register = blended.setdefault("register", {})
    author_register = profile.register_sliders.model_dump()
    for key, author_value in author_register.items():
        exemplar_value = exemplar_register.get(key, author_value)
        exemplar_register[key] = _clamp(
            alpha_exemplar * exemplar_value + (1.0 - alpha_exemplar) * author_value
        )

    profanity = blended.setdefault("profanity", {})
    profanity["allowed"] = bool(profile.profanity.allowed and profanity.get("allowed", False))
    profanity["frequency"] = (
        min(float(profile.profanity.frequency), float(profanity.get("frequency", 0.0)))
        if profanity["allowed"]
        else 0.0
    )

    return blended


def _extract_motifs_from_digest(digest: ExemplarDigest, limit: int = 8) -> list[str]:
    """Extract motif labels from digest motif map."""
    motifs = []
    for motif in digest.motif_map[:limit]:
        motif_name = motif.motif.strip()
        if motif_name and motif_name not in motifs:
            motifs.append(motif_name)
    return motifs


def _extract_imagery_from_digest(digest: ExemplarDigest, limit: int = 12) -> list[str]:
    """Flatten imagery palettes into a compact list."""
    imagery = []
    for phrases in digest.imagery_palettes.values():
        for phrase in phrases:
            clean_phrase = phrase.strip()
            if clean_phrase and clean_phrase not in imagery:
                imagery.append(clean_phrase)
            if len(imagery) >= limit:
                return imagery
    return imagery


def _extract_characters_from_digest(digest: ExemplarDigest, limit: int = 4) -> list[dict[str, str]]:
    """Extract likely character placeholders from PERSON entities."""
    characters = []
    for entity in digest.coherence_graph.entities:
        if entity.type.upper() == "PERSON":
            characters.append(
                {
                    "name": entity.canonical,
                    "role": "supporting" if characters else "protagonist",
                }
            )
        if len(characters) >= limit:
            break

    if not characters:
        characters.append({"name": "protagonist", "role": "protagonist"})

    return characters


def initialize_content_section(
    setting_prompt: str = "",
    characters_prompt: str = "",
    digest: ExemplarDigest | None = None,
) -> dict[str, Any]:
    """
    Initialize content section with placeholders or prompts.

    Args:
        setting_prompt: Optional setting description
        characters_prompt: Optional character descriptions
        digest: Optional digest to extract motifs, imagery, and entities from

    Returns:
        Dictionary with content parameters
    """
    motifs = _extract_motifs_from_digest(digest) if digest is not None else []
    imagery_palette = _extract_imagery_from_digest(digest) if digest is not None else []
    characters = _extract_characters_from_digest(digest) if digest is not None else []

    content = {
        "setting": {
            "place": setting_prompt or "an unspecified familiar place",
            "time": "contemporary",
            "weather_budget": [],
        },
        "characters": characters,
        "motifs": motifs,
        "imagery_palette": imagery_palette,
        "props": imagery_palette[:3],
        "sensory_quotas": {
            "visual": 0.4,
            "auditory": 0.2,
            "tactile": 0.2,
            "olfactory": 0.1,
            "gustatory": 0.1,
        },
    }

    if characters_prompt:
        char_names = [name.strip() for name in characters_prompt.split(",")]
        parsed_characters = [
            {"name": name, "role": "supporting" if index else "protagonist"}
            for index, name in enumerate(char_names)
            if name
        ]
        if parsed_characters:
            content["characters"] = parsed_characters

    return content


def synthesize_spec(
    digest: ExemplarDigest,
    story_id: str,
    seed: int = 137,
    profile: AuthorProfile | None = None,
    alpha_exemplar: float = 0.7,
    output_path: str | None = None,
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
    log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="SpecSynth",
        decision=f"Use alpha_exemplar={alpha_exemplar} for blending",
        reasoning=(
            f"Blending exemplar digest with author profile using "
            f"{alpha_exemplar:.0%} exemplar weight."
        ),
        parameters={
            "alpha_exemplar": alpha_exemplar,
            "has_author_profile": profile is not None,
            "seed": seed,
        },
        metadata={"story_id": story_id},
    )

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

    content_params = initialize_content_section(digest=digest)

    from literary_structure_generator.models.story_spec import (
        AntiPlagiarism,
        BeatSpec,
        Character,
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

    meta = MetaInfo(
        story_id=story_id,
        seed=seed,
        version="2.0",
        derived_from={
            "exemplar": digest.meta.source,
            "digest_version": digest.schema_version,
        },
    )

    voice = Voice(
        person=voice_params.get("person", "first"),
        distance=voice_params.get("distance", "intimate"),
        register=voice_params.get("register", {}),
        syntax=Syntax(**voice_params.get("syntax", {})),
        dialogue_style=DialogueStyle(**voice_params.get("dialogue_style", {})),
        profanity=Profanity(**voice_params.get("profanity", {})),
    )

    beat_specs = [BeatSpec(**beat_data) for beat_data in form_params.get("beat_map", [])]
    form = Form(
        structure=form_params.get("structure", "episodic"),
        beat_map=beat_specs,
        dialogue_ratio=form_params.get("dialogue_ratio", 0.25),
        paragraphing=Paragraphing(**form_params.get("paragraphing", {})),
    )

    content = Content(
        setting=Setting(**content_params["setting"]),
        characters=[
            Character(**character_data) for character_data in content_params.get("characters", [])
        ],
        motifs=content_params.get("motifs", []),
        imagery_palette=content_params.get("imagery_palette", []),
        props=content_params.get("props", []),
        sensory_quotas=content_params.get("sensory_quotas", {}),
    )

    target_words = sum(beat.target_words for beat in beat_specs) if beat_specs else 2000

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

    spec = StorySpec(
        meta=meta,
        voice=voice,
        form=form,
        content=content,
        constraints=constraints,
    )

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(spec.model_dump(by_alias=True, mode="json"), f, indent=2)

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
            "target_words": target_words,
        },
        metadata={"stage": "completion"},
    )

    return spec
