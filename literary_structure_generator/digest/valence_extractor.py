"""
Valence and Surprise Curve Extractor

Extracts emotional valence arc and surprise curve from text.

Uses:
    - Lexicon-based sentiment analysis for valence
    - Change point detection for surprise
"""

import re
from typing import Any

from literary_structure_generator.utils.decision_logger import log_decision

# Simple valence lexicon (positive/negative words)
# In a production system, you'd use a more comprehensive lexicon like AFINN or SentiWordNet
POSITIVE_WORDS = {
    "happy",
    "joy",
    "love",
    "wonderful",
    "great",
    "good",
    "beautiful",
    "amazing",
    "excellent",
    "fantastic",
    "perfect",
    "pleasant",
    "smile",
    "laugh",
    "delight",
    "hope",
    "bright",
    "warm",
    "kind",
    "gentle",
    "sweet",
    "calm",
    "peaceful",
}

NEGATIVE_WORDS = {
    "sad",
    "pain",
    "hurt",
    "terrible",
    "bad",
    "awful",
    "horrible",
    "ugly",
    "hate",
    "angry",
    "mad",
    "furious",
    "dark",
    "cold",
    "harsh",
    "cruel",
    "fear",
    "afraid",
    "scared",
    "worried",
    "anxious",
    "nervous",
    "sick",
    "death",
    "die",
    "blood",
    "wound",
    "scream",
    "cry",
    "tear",
}


def _tokenize_words(text: str) -> list[str]:
    """Tokenize text into words."""
    return re.findall(r"\b[\w']+\b", text.lower())


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs."""
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _compute_paragraph_valence(paragraph: str) -> float:
    """
    Compute valence for a single paragraph using lexicon.

    Args:
        paragraph: Input paragraph text

    Returns:
        Valence score (-1.0 to 1.0)
    """
    words = _tokenize_words(paragraph)

    if not words:
        return 0.0

    positive_count = sum(1 for w in words if w in POSITIVE_WORDS)
    negative_count = sum(1 for w in words if w in NEGATIVE_WORDS)

    total_sentiment_words = positive_count + negative_count

    if total_sentiment_words == 0:
        return 0.0

    # Normalize to -1.0 to 1.0
    return (positive_count - negative_count) / total_sentiment_words


def _smooth_valence(valences: list[float], window: int = 3) -> list[float]:
    """
    Apply moving average smoothing to valence scores.

    Args:
        valences: List of valence scores
        window: Window size for moving average

    Returns:
        Smoothed valence scores
    """
    if len(valences) < window:
        return valences

    smoothed = []
    for i in range(len(valences)):
        # Get window around this point
        start = max(0, i - window // 2)
        end = min(len(valences), i + window // 2 + 1)
        window_vals = valences[start:end]

        # Compute average
        smoothed.append(sum(window_vals) / len(window_vals))

    return smoothed


def _detect_change_points(
    valences: list[float],
    threshold: float = 0.3,
) -> list[int]:
    """
    Detect change points where valence changes significantly.

    Args:
        valences: List of valence scores
        threshold: Minimum absolute change to detect

    Returns:
        List of indices where change points occur
    """
    change_points = []

    for i in range(1, len(valences)):
        delta = abs(valences[i] - valences[i - 1])
        if delta >= threshold:
            change_points.append(i)

    return change_points


def extract_valence_arc(
    text: str,
    beats: list[Any],
    run_id: str = "run_001",
    iteration: int = 0,
) -> tuple[dict[str, Any], list[float]]:
    """
    Extract emotional valence arc from text.

    Computes valence per paragraph and organizes by beat.

    Args:
        text: Input text
        beats: List of beat objects with id and span
        run_id: Run ID for logging
        iteration: Iteration number for logging

    Returns:
        Tuple of (valence_arc dict, surprise_curve list)
    """
    # Split into paragraphs
    paragraphs = _split_paragraphs(text)

    # Compute valence for each paragraph
    paragraph_valences = [_compute_paragraph_valence(p) for p in paragraphs]

    # Smooth the valence curve
    smoothed_valences = _smooth_valence(paragraph_valences, window=3)

    # Detect change points (surprise)
    change_points = _detect_change_points(smoothed_valences, threshold=0.3)

    # Create surprise curve: 1.0 at change points, 0.0 elsewhere
    surprise_curve = [1.0 if i in change_points else 0.0 for i in range(len(paragraphs))]

    # Organize valence by beat
    valence_by_beat = {}

    # Simple heuristic: divide paragraphs evenly among beats
    if beats:
        paras_per_beat = len(paragraphs) // len(beats)
        for i, beat in enumerate(beats):
            start_idx = i * paras_per_beat
            end_idx = (i + 1) * paras_per_beat if i < len(beats) - 1 else len(paragraphs)

            beat_valences = smoothed_valences[start_idx:end_idx]
            if beat_valences:
                valence_by_beat[beat.id] = {
                    "mean": sum(beat_valences) / len(beat_valences),
                    "min": min(beat_valences),
                    "max": max(beat_valences),
                    "values": beat_valences,
                }

    valence_arc = {
        "per_paragraph": smoothed_valences,
        "per_beat": valence_by_beat,
        "overall_mean": (
            sum(smoothed_valences) / len(smoothed_valences) if smoothed_valences else 0.0
        ),
    }

    log_decision(
        run_id=run_id,
        iteration=iteration,
        agent="Digest",
        decision=f"Computed valence arc: mean={valence_arc['overall_mean']:.2f}, change_points={len(change_points)}",
        reasoning="Lexicon-based sentiment per paragraph, smoothed with moving average",
        parameters={
            "num_paragraphs": len(paragraphs),
            "num_change_points": len(change_points),
            "overall_mean": valence_arc["overall_mean"],
        },
        metadata={"stage": "valence_extraction"},
    )

    return valence_arc, surprise_curve
