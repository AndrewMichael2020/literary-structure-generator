"""
Overlap guard and Clean Mode filters

Anti-plagiarism checks:
    - N-gram overlap detection
    - SimHash distance checking
    - Profanity filtering with [bleep] replacement
"""

from literary_structure_generator.utils.profanity import structural_bleep
from literary_structure_generator.utils.similarity import calculate_simhash, hamming_distance


def max_ngram_overlap(text: str, exemplar_text: str, n: int = 12) -> float:
    """
    Calculate maximum n-gram overlap between text and exemplar.

    Checks all n-grams from 1 to n and returns the maximum overlap percentage.

    Args:
        text: Generated text to check
        exemplar_text: Reference exemplar text
        n: Maximum n-gram size to check (default: 12)

    Returns:
        Maximum overlap percentage (0.0 - 1.0)
    """
    if not text or not exemplar_text:
        return 0.0

    # Tokenize both texts
    text_tokens = text.lower().split()
    exemplar_tokens = exemplar_text.lower().split()

    if not text_tokens or not exemplar_tokens:
        return 0.0

    max_overlap = 0.0

    # Check n-grams from size 3 to n (smaller n-grams not meaningful)
    for ngram_size in range(3, min(n + 1, len(text_tokens) + 1)):
        # Create n-gram sets
        text_ngrams = set()
        for i in range(len(text_tokens) - ngram_size + 1):
            ngram = tuple(text_tokens[i : i + ngram_size])
            text_ngrams.add(ngram)

        exemplar_ngrams = set()
        for i in range(len(exemplar_tokens) - ngram_size + 1):
            ngram = tuple(exemplar_tokens[i : i + ngram_size])
            exemplar_ngrams.add(ngram)

        # Calculate overlap
        if text_ngrams:
            overlap = len(text_ngrams & exemplar_ngrams) / len(text_ngrams)
            max_overlap = max(max_overlap, overlap)

    return max_overlap


def simhash_distance(a: str, b: str) -> int:
    """
    Calculate SimHash Hamming distance between two texts.

    Uses 256-bit SimHash fingerprints.

    Args:
        a: First text
        b: Second text

    Returns:
        Hamming distance (0-256)
    """
    hash_a = calculate_simhash(a, num_bits=256)
    hash_b = calculate_simhash(b, num_bits=256)
    return hamming_distance(hash_a, hash_b)


def check_overlap_guard(
    text: str,
    exemplar: str,
    max_ngram: int = 12,
    max_overlap_pct: float = 0.03,
    min_simhash_hamming: int = 18,
) -> dict:
    """
    Perform all anti-plagiarism checks.

    Args:
        text: Generated text to check
        exemplar: Exemplar text to compare against
        max_ngram: Maximum n-gram size to check (default: 12)
        max_overlap_pct: Maximum allowed overlap percentage (default: 0.03)
        min_simhash_hamming: Minimum required SimHash Hamming distance (default: 18)

    Returns:
        Dictionary with:
            - passed: bool (True if all checks pass)
            - ngram_overlap: float (actual overlap)
            - simhash_distance: int (actual distance)
            - violations: list of str (constraint violations)
    """
    violations = []

    # Check n-gram overlap
    ngram_overlap = max_ngram_overlap(text, exemplar, n=max_ngram)
    if ngram_overlap > max_overlap_pct:
        violations.append(f"N-gram overlap {ngram_overlap:.3f} exceeds threshold {max_overlap_pct}")

    # Check SimHash distance
    simhash_dist = simhash_distance(text, exemplar)
    if simhash_dist < min_simhash_hamming:
        violations.append(f"SimHash distance {simhash_dist} below minimum {min_simhash_hamming}")

    return {
        "passed": len(violations) == 0,
        "ngram_overlap": ngram_overlap,
        "simhash_distance": simhash_dist,
        "violations": violations,
    }


def apply_clean_mode_if_needed(text: str, clean_mode_enabled: bool = True) -> str:
    """
    Apply clean mode filter if enabled.

    NOTE: This function now uses the universal structural_bleep profanity filter
    for consistent [bleep] replacement across all outputs.

    Args:
        text: Input text
        clean_mode_enabled: Whether to apply filter (default: True)

    Returns:
        Filtered text if enabled, otherwise original text
    """
    if not clean_mode_enabled:
        return text
    return structural_bleep(text)
