"""
Motif and Imagery Coverage Evaluator

Evaluates coverage of motifs and imagery from Digest/Spec:
- Coverage of top motifs/imagery with repetition penalty
- Balance between coverage and overuse

Returns: coverage (0..1), overuse_penalty (0..1)
"""

import re

from literary_structure_generator.models.exemplar_digest import ExemplarDigest
from literary_structure_generator.models.story_spec import StorySpec


def extract_motif_mentions(text: str, motifs: list[str]) -> dict[str, int]:
    """
    Extract motif mentions from text.

    Args:
        text: Text to analyze
        motifs: List of target motifs

    Returns:
        Dictionary mapping motif to mention count
    """
    text_lower = text.lower()
    motif_counts = {}

    for motif in motifs:
        # Convert motif to regex pattern (handle multi-word motifs)
        motif_lower = motif.lower()
        # Use word boundaries for better matching
        pattern = r"\b" + re.escape(motif_lower) + r"\b"
        matches = re.findall(pattern, text_lower)
        motif_counts[motif] = len(matches)

    return motif_counts


def extract_imagery_mentions(text: str, imagery_palette: list[str]) -> dict[str, int]:
    """
    Extract imagery mentions from text.

    Args:
        text: Text to analyze
        imagery_palette: List of target imagery terms

    Returns:
        Dictionary mapping imagery term to mention count
    """
    # Same logic as motifs
    return extract_motif_mentions(text, imagery_palette)


def calculate_coverage(
    mentions: dict[str, int], target_items: list[str], min_mentions: int = 1
) -> float:
    """
    Calculate coverage of target items.

    Args:
        mentions: Dictionary of item mention counts
        target_items: List of target items
        min_mentions: Minimum mentions to count as covered

    Returns:
        Coverage ratio 0..1
    """
    if not target_items:
        return 1.0

    covered_count = sum(1 for item in target_items if mentions.get(item, 0) >= min_mentions)

    return covered_count / len(target_items)


def calculate_overuse_penalty(
    mentions: dict[str, int], max_mentions_per_item: int = 5
) -> tuple[float, list[str]]:
    """
    Calculate penalty for overusing motifs/imagery.

    Args:
        mentions: Dictionary of item mention counts
        max_mentions_per_item: Maximum acceptable mentions per item

    Returns:
        Tuple of (penalty 0..1, list of overused items)
    """
    overused_items = []
    penalty = 0.0

    for item, count in mentions.items():
        if count > max_mentions_per_item:
            excess = count - max_mentions_per_item
            # Penalty grows with excess
            item_penalty = min(0.2, excess * 0.05)
            penalty += item_penalty
            overused_items.append(f"{item} ({count} times)")

    # Cap total penalty
    penalty = min(1.0, penalty)

    return penalty, overused_items


def calculate_balance_score(mentions: dict[str, int]) -> float:
    """
    Calculate balance in motif/imagery distribution.

    Args:
        mentions: Dictionary of item mention counts

    Returns:
        Balance score 0..1 (higher is more balanced)
    """
    if not mentions or all(count == 0 for count in mentions.values()):
        return 0.5

    counts = [count for count in mentions.values() if count > 0]

    if len(counts) <= 1:
        return 0.5

    # Calculate coefficient of variation (lower is more balanced)
    mean_count = sum(counts) / len(counts)
    variance = sum((count - mean_count) ** 2 for count in counts) / len(counts)
    std_dev = variance**0.5

    if mean_count == 0:
        return 0.5

    cv = std_dev / mean_count

    # Convert CV to score (lower CV = higher score)
    # CV of 0 = perfect balance (score 1.0)
    # CV of 2+ = very imbalanced (score 0)
    return max(0.0, 1.0 - (cv / 2.0))


def evaluate_motif_imagery_coverage(
    text: str, spec: StorySpec, digest: ExemplarDigest
) -> dict[str, any]:
    """
    Evaluate motif and imagery coverage.

    Args:
        text: Generated text to evaluate
        spec: StorySpec with target motifs and imagery
        digest: ExemplarDigest with motif patterns (optional enrichment)

    Returns:
        Dictionary with coverage, overuse_penalty, and details
    """
    # Get target motifs and imagery
    target_motifs = spec.content.motifs
    target_imagery = spec.content.imagery_palette

    # Extract mentions
    motif_mentions = extract_motif_mentions(text, target_motifs)
    imagery_mentions = extract_imagery_mentions(text, target_imagery)

    # Calculate coverage
    motif_coverage = calculate_coverage(motif_mentions, target_motifs, min_mentions=1)
    imagery_coverage = calculate_coverage(imagery_mentions, target_imagery, min_mentions=1)

    # Calculate overuse penalties
    motif_overuse_penalty, motif_overused = calculate_overuse_penalty(
        motif_mentions, max_mentions_per_item=5
    )
    imagery_overuse_penalty, imagery_overused = calculate_overuse_penalty(
        imagery_mentions, max_mentions_per_item=4
    )

    # Calculate balance scores
    motif_balance = calculate_balance_score(motif_mentions)
    imagery_balance = calculate_balance_score(imagery_mentions)

    # Overall coverage (weighted average)
    if target_motifs and target_imagery:
        overall_coverage = motif_coverage * 0.6 + imagery_coverage * 0.4
    elif target_motifs:
        overall_coverage = motif_coverage
    elif target_imagery:
        overall_coverage = imagery_coverage
    else:
        overall_coverage = 1.0

    # Overall overuse penalty (weighted average)
    overall_overuse_penalty = motif_overuse_penalty * 0.6 + imagery_overuse_penalty * 0.4

    # Overall balance
    overall_balance = motif_balance * 0.6 + imagery_balance * 0.4

    # Final score combines coverage, penalty, and balance
    final_score = (
        overall_coverage * (1.0 - overall_overuse_penalty * 0.5) * (0.8 + overall_balance * 0.2)
    )
    final_score = max(0.0, min(1.0, final_score))

    return {
        "overall": final_score,
        "motif_coverage": motif_coverage,
        "imagery_coverage": imagery_coverage,
        "overall_coverage": overall_coverage,
        "motif_overuse_penalty": motif_overuse_penalty,
        "imagery_overuse_penalty": imagery_overuse_penalty,
        "overall_overuse_penalty": overall_overuse_penalty,
        "motif_balance": motif_balance,
        "imagery_balance": imagery_balance,
        "motif_mentions": motif_mentions,
        "imagery_mentions": imagery_mentions,
        "overused_items": motif_overused + imagery_overused,
    }
