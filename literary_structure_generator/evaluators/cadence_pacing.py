"""
Cadence and Pacing Evaluator

Evaluates paragraph rhythm and pacing:
- Paragraph length histogram vs Spec cadence
- Valence smoothness proxy (lexicon-based)

Returns score 0..1
"""

import re
from typing import Dict, List

from literary_structure_generator.models.story_spec import StorySpec


def extract_paragraph_lengths(text: str) -> List[int]:
    """
    Extract paragraph lengths in words.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of paragraph lengths
    """
    # Split by double newlines
    paragraphs = re.split(r'\n\n+', text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    lengths = [len(p.split()) for p in paragraphs]
    
    return lengths


def classify_paragraph_cadence(para_lengths: List[int]) -> Dict[str, float]:
    """
    Classify paragraph cadence (short/mixed/long).
    
    Args:
        para_lengths: List of paragraph lengths
        
    Returns:
        Dictionary with ratios of short/mixed/long
    """
    if not para_lengths:
        return {"short": 0.0, "mixed": 0.0, "long": 0.0}
    
    # Classification thresholds
    short_threshold = 30  # words
    long_threshold = 60   # words
    
    short_count = sum(1 for length in para_lengths if length < short_threshold)
    long_count = sum(1 for length in para_lengths if length > long_threshold)
    mixed_count = len(para_lengths) - short_count - long_count
    
    total = len(para_lengths)
    
    return {
        "short": short_count / total,
        "mixed": mixed_count / total,
        "long": long_count / total,
    }


def map_cadence_to_distribution(cadence: str) -> Dict[str, float]:
    """
    Map cadence label to expected distribution.
    
    Args:
        cadence: Cadence label (short/mixed/long)
        
    Returns:
        Expected distribution
    """
    if cadence == "short":
        return {"short": 0.7, "mixed": 0.2, "long": 0.1}
    elif cadence == "long":
        return {"short": 0.1, "mixed": 0.2, "long": 0.7}
    else:  # mixed
        return {"short": 0.3, "mixed": 0.4, "long": 0.3}


def calculate_cadence_match(
    actual_dist: Dict[str, float],
    target_dist: Dict[str, float]
) -> float:
    """
    Calculate how well actual cadence matches target.
    
    Args:
        actual_dist: Actual distribution
        target_dist: Target distribution
        
    Returns:
        Match score 0..1
    """
    # Calculate total deviation
    total_deviation = 0.0
    for key in ["short", "mixed", "long"]:
        deviation = abs(actual_dist.get(key, 0.0) - target_dist.get(key, 0.0))
        total_deviation += deviation
    
    # Convert deviation to score (0 deviation = 1.0 score)
    # Max possible deviation is 2.0 (completely opposite distributions)
    score = 1.0 - (total_deviation / 2.0)
    
    return max(0.0, score)


def calculate_paragraph_variance(para_lengths: List[int]) -> float:
    """
    Calculate paragraph length variance.
    
    Args:
        para_lengths: List of paragraph lengths
        
    Returns:
        Variance (coefficient of variation)
    """
    if not para_lengths or len(para_lengths) == 1:
        return 0.0
    
    mean_length = sum(para_lengths) / len(para_lengths)
    
    if mean_length == 0:
        return 0.0
    
    variance = sum((length - mean_length) ** 2 for length in para_lengths) / len(para_lengths)
    std_dev = variance ** 0.5
    
    # Coefficient of variation
    cv = std_dev / mean_length
    
    return cv


def check_paragraph_variance(
    para_lengths: List[int],
    target_variance: float,
    tolerance: float = 0.2
) -> float:
    """
    Check if paragraph variance matches target.
    
    Args:
        para_lengths: List of paragraph lengths
        target_variance: Target variance from spec
        tolerance: Allowed deviation
        
    Returns:
        Score 0..1
    """
    actual_variance = calculate_paragraph_variance(para_lengths)
    
    deviation = abs(actual_variance - target_variance)
    
    if deviation <= tolerance:
        return 1.0 - (deviation / tolerance) * 0.3
    else:
        excess = deviation - tolerance
        return max(0.0, 0.7 * (0.5 ** (excess * 3)))


def estimate_valence_smoothness(text: str) -> float:
    """
    Estimate emotional valence smoothness using lexicon proxy.
    
    Args:
        text: Text to analyze
        
    Returns:
        Smoothness score 0..1 (higher = smoother)
    """
    # Simple positive/negative word lexicon
    positive_words = [
        'love', 'happy', 'joy', 'hope', 'smile', 'laugh', 'good', 'great',
        'wonderful', 'beautiful', 'pleasant', 'bright', 'warm', 'kind', 'gentle'
    ]
    
    negative_words = [
        'hate', 'sad', 'pain', 'fear', 'cry', 'anger', 'bad', 'terrible',
        'awful', 'ugly', 'harsh', 'dark', 'cold', 'cruel', 'rough'
    ]
    
    # Split into segments (paragraphs)
    paragraphs = re.split(r'\n\n+', text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    if len(paragraphs) < 2:
        return 1.0  # Too short to have transitions
    
    # Calculate valence per paragraph
    valences = []
    for para in paragraphs:
        para_lower = para.lower()
        pos_count = sum(1 for word in positive_words if word in para_lower)
        neg_count = sum(1 for word in negative_words if word in para_lower)
        
        # Valence score (-1 to +1)
        total = pos_count + neg_count
        if total == 0:
            valence = 0.0
        else:
            valence = (pos_count - neg_count) / total
        
        valences.append(valence)
    
    # Calculate smoothness (lower variance = smoother)
    if len(valences) < 2:
        return 1.0
    
    # Calculate absolute differences between consecutive paragraphs
    transitions = [abs(valences[i + 1] - valences[i]) for i in range(len(valences) - 1)]
    
    avg_transition = sum(transitions) / len(transitions)
    
    # Convert to smoothness score
    # Small transitions = smooth (score close to 1.0)
    # Large transitions = rough (score close to 0.0)
    # Typical transition range is 0-2.0
    smoothness = max(0.0, 1.0 - (avg_transition / 2.0))
    
    return smoothness


def evaluate_cadence_pacing(text: str, spec: StorySpec) -> Dict[str, any]:
    """
    Evaluate paragraph rhythm and pacing.
    
    Args:
        text: Generated text to evaluate
        spec: StorySpec with cadence targets
        
    Returns:
        Dictionary with overall score and component scores
    """
    # Extract paragraph lengths
    para_lengths = extract_paragraph_lengths(text)
    
    # Classify actual cadence
    actual_cadence_dist = classify_paragraph_cadence(para_lengths)
    
    # Get target cadence from spec (use first beat's cadence as overall target)
    # In a more sophisticated system, would check per-beat
    if spec.form.beat_map:
        target_cadence_label = spec.form.beat_map[0].cadence
    else:
        target_cadence_label = "mixed"
    
    target_cadence_dist = map_cadence_to_distribution(target_cadence_label)
    
    # Calculate cadence match score
    cadence_score = calculate_cadence_match(actual_cadence_dist, target_cadence_dist)
    
    # Check paragraph variance
    target_variance = spec.form.paragraphing.variance
    variance_score = check_paragraph_variance(para_lengths, target_variance)
    
    # Estimate valence smoothness
    smoothness_score = estimate_valence_smoothness(text)
    
    # Overall score (weighted combination)
    overall = (
        cadence_score * 0.4 +
        variance_score * 0.3 +
        smoothness_score * 0.3
    )
    
    return {
        "overall": overall,
        "cadence_match": cadence_score,
        "variance_match": variance_score,
        "valence_smoothness": smoothness_score,
        "actual_cadence_dist": actual_cadence_dist,
        "target_cadence_dist": target_cadence_dist,
        "paragraph_count": len(para_lengths),
        "avg_paragraph_length": sum(para_lengths) / len(para_lengths) if para_lengths else 0,
    }
