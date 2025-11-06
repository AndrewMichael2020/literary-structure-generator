"""
FormFit Evaluator

Measures structural adherence to StorySpec:
- Per-beat length adherence (target_words tolerance)
- Beat function alignment (keyword cues on beat summaries)
- Scene:summary ratio proxy from paragraph sizes

Returns score 0..1
"""

import re

from literary_structure_generator.models.story_spec import BeatSpec, StorySpec


def split_into_beats(text: str, num_beats: int) -> list[str]:
    """
    Split text into approximate beats based on paragraph breaks.

    Args:
        text: Full generated text
        num_beats: Expected number of beats

    Returns:
        List of beat texts (approximate)
    """
    # Split by double newlines or paragraph markers
    paragraphs = re.split(r"\n\n+", text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return [""] * num_beats

    # Divide paragraphs evenly into beats
    beats_per_section = max(1, len(paragraphs) // num_beats)
    beats = []

    for i in range(num_beats):
        start_idx = i * beats_per_section
        end_idx = start_idx + beats_per_section if i < num_beats - 1 else len(paragraphs)
        beat_text = "\n\n".join(paragraphs[start_idx:end_idx])
        beats.append(beat_text)

    return beats


def count_words(text: str) -> int:
    """
    Count words in text.

    Args:
        text: Text to count

    Returns:
        Word count
    """
    return len(text.split())


def check_beat_length_adherence(
    beat_texts: list[str], beat_specs: list[BeatSpec], tolerance: float = 0.2
) -> tuple[float, list[dict]]:
    """
    Check if beat lengths match targets within tolerance.

    Args:
        beat_texts: List of beat text segments
        beat_specs: List of BeatSpec objects with target_words
        tolerance: Allowed deviation as fraction

    Returns:
        Tuple of (overall score, per-beat details)
    """
    if len(beat_texts) != len(beat_specs):
        # Penalize beat count mismatch
        return 0.3, []

    per_beat_scores = []
    per_beat_details = []

    for _i, (beat_text, beat_spec) in enumerate(zip(beat_texts, beat_specs, strict=False)):
        actual_words = count_words(beat_text)
        target_words = beat_spec.target_words

        if target_words == 0:
            score = 0.5
            deviation = 0
        else:
            deviation = abs(actual_words - target_words) / target_words

            if deviation <= tolerance:
                score = 1.0 - (deviation / tolerance) * 0.2
            else:
                excess = deviation - tolerance
                score = max(0.0, 0.8 * (0.5 ** (excess * 3)))

        per_beat_scores.append(score)
        per_beat_details.append(
            {
                "beat_id": beat_spec.id,
                "target_words": target_words,
                "actual_words": actual_words,
                "deviation": deviation,
                "score": score,
            }
        )

    overall_score = sum(per_beat_scores) / len(per_beat_scores) if per_beat_scores else 0.0

    return overall_score, per_beat_details


def check_beat_function_alignment(
    beat_texts: list[str], beat_specs: list[BeatSpec]
) -> tuple[float, list[dict]]:
    """
    Check if beats align with their narrative functions using keyword cues.

    Args:
        beat_texts: List of beat text segments
        beat_specs: List of BeatSpec objects with function descriptions

    Returns:
        Tuple of (overall score, per-beat details)
    """
    # Function keyword mappings
    function_keywords = {
        "hook": ["began", "started", "first", "opening", "sudden"],
        "inciting": ["changed", "discovered", "realized", "noticed", "happened"],
        "rising": ["tried", "attempted", "struggled", "worked", "pushed"],
        "crisis": ["failed", "broke", "collapsed", "worst", "lost"],
        "climax": ["faced", "confronted", "decided", "chose", "fought"],
        "falling": ["aftermath", "after", "settled", "calmed", "subsided"],
        "resolution": ["ended", "finally", "concluded", "understood", "accepted"],
        "denouement": ["left", "departed", "finished", "last", "closed"],
    }

    if len(beat_texts) != len(beat_specs):
        return 0.3, []

    per_beat_scores = []
    per_beat_details = []

    for beat_text, beat_spec in zip(beat_texts, beat_specs, strict=False):
        beat_text_lower = beat_text.lower()
        function = beat_spec.function.lower()

        # Find matching keywords for this function
        matching_keywords = []
        for func_key, keywords in function_keywords.items():
            if func_key in function:
                matching_keywords = keywords
                break

        if not matching_keywords:
            # Unknown function, give neutral score
            score = 0.5
            matches = 0
        else:
            # Count keyword matches
            matches = sum(1 for kw in matching_keywords if kw in beat_text_lower)
            # Score based on matches (at least 1 match is good)
            if matches >= 2:
                score = 1.0
            elif matches == 1:
                score = 0.8
            else:
                score = 0.4

        per_beat_scores.append(score)
        per_beat_details.append(
            {
                "beat_id": beat_spec.id,
                "function": beat_spec.function,
                "keyword_matches": matches,
                "score": score,
            }
        )

    overall_score = sum(per_beat_scores) / len(per_beat_scores) if per_beat_scores else 0.0

    return overall_score, per_beat_details


def estimate_scene_summary_ratio(text: str) -> float:
    """
    Estimate scene:summary ratio from paragraph sizes.

    Heuristic: Shorter paragraphs = summary, longer = scene

    Args:
        text: Full text

    Returns:
        Scene ratio (0..1)
    """
    paragraphs = re.split(r"\n\n+", text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return 0.5

    # Count words per paragraph
    para_lengths = [len(p.split()) for p in paragraphs]
    avg_length = sum(para_lengths) / len(para_lengths)

    # Scene paragraphs are above average, summary below
    scene_paras = sum(1 for length in para_lengths if length > avg_length)

    return scene_paras / len(paragraphs)


def check_scene_summary_ratio(
    text: str, target_scene_ratio: float, tolerance: float = 0.15
) -> float:
    """
    Check if scene:summary ratio matches target.

    Args:
        text: Generated text
        target_scene_ratio: Target scene ratio from spec
        tolerance: Allowed deviation

    Returns:
        Score 0..1
    """
    actual_ratio = estimate_scene_summary_ratio(text)
    deviation = abs(actual_ratio - target_scene_ratio)

    if deviation <= tolerance:
        return 1.0 - (deviation / tolerance) * 0.2
    excess = deviation - tolerance
    return max(0.0, 0.8 * (0.5 ** (excess * 4)))


def evaluate_formfit(text: str, spec: StorySpec) -> dict[str, any]:
    """
    Evaluate structural adherence to StorySpec.

    Args:
        text: Generated text to evaluate
        spec: StorySpec with structural targets

    Returns:
        Dictionary with overall score and component scores
    """
    # Split text into beats
    num_beats = len(spec.form.beat_map)
    beat_texts = split_into_beats(text, num_beats)

    # Check beat length adherence
    length_score, length_details = check_beat_length_adherence(
        beat_texts, spec.form.beat_map, tolerance=0.2
    )

    # Check beat function alignment
    function_score, function_details = check_beat_function_alignment(beat_texts, spec.form.beat_map)

    # Check scene:summary ratio
    target_scene_ratio = spec.form.scene_ratio.get("scene", 0.7)
    scene_ratio_score = check_scene_summary_ratio(text, target_scene_ratio)

    # Weighted combination
    overall = length_score * 0.4 + function_score * 0.35 + scene_ratio_score * 0.25

    return {
        "overall": overall,
        "beat_length_adherence": length_score,
        "beat_function_alignment": function_score,
        "scene_summary_ratio": scene_ratio_score,
        "per_beat_length": length_details,
        "per_beat_function": function_details,
    }
