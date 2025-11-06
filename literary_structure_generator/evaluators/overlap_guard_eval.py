"""
Overlap Guard Evaluator

Re-checks overlaps with exemplar text:
- N-gram overlap percentage
- SimHash Hamming distance
- Hard fail if thresholds violated

Returns pass/fail + stats
"""

from typing import Dict, List, Set

from literary_structure_generator.utils.similarity import calculate_simhash, hamming_distance


def tokenize(text: str) -> List[str]:
    """
    Tokenize text into words.
    
    Args:
        text: Text to tokenize
        
    Returns:
        List of lowercase words
    """
    import re
    # Remove punctuation and convert to lowercase
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = text.split()
    return [w for w in words if w]


def generate_ngrams(tokens: List[str], n: int) -> Set[tuple]:
    """
    Generate n-grams from token list.
    
    Args:
        tokens: List of tokens
        n: N-gram size
        
    Returns:
        Set of n-gram tuples
    """
    if n > len(tokens):
        return set()
    
    ngrams = set()
    for i in range(len(tokens) - n + 1):
        ngram = tuple(tokens[i:i + n])
        ngrams.add(ngram)
    
    return ngrams


def find_max_ngram_overlap(text1: str, text2: str, max_n: int = 20) -> int:
    """
    Find maximum shared n-gram length between two texts.
    
    Args:
        text1: First text
        text2: Second text
        max_n: Maximum n-gram size to check
        
    Returns:
        Length of longest shared n-gram
    """
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    
    # Start from max_n and work down
    for n in range(max_n, 0, -1):
        ngrams1 = generate_ngrams(tokens1, n)
        ngrams2 = generate_ngrams(tokens2, n)
        
        # Check for overlap
        overlap = ngrams1 & ngrams2
        if overlap:
            return n
    
    return 0


def calculate_ngram_overlap_percentage(text1: str, text2: str, n: int = 4) -> float:
    """
    Calculate percentage of n-grams that overlap.
    
    Args:
        text1: First text
        text2: Second text
        n: N-gram size
        
    Returns:
        Overlap percentage 0..1
    """
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    
    ngrams1 = generate_ngrams(tokens1, n)
    ngrams2 = generate_ngrams(tokens2, n)
    
    if not ngrams1:
        return 0.0
    
    overlap = ngrams1 & ngrams2
    overlap_pct = len(overlap) / len(ngrams1)
    
    return overlap_pct


def check_simhash_distance(text1: str, text2: str, num_bits: int = 256) -> int:
    """
    Calculate SimHash Hamming distance between texts.
    
    Args:
        text1: First text
        text2: Second text
        num_bits: Number of bits for SimHash
        
    Returns:
        Hamming distance
    """
    hash1 = calculate_simhash(text1, num_bits=num_bits)
    hash2 = calculate_simhash(text2, num_bits=num_bits)
    
    distance = hamming_distance(hash1, hash2)
    
    return distance


def evaluate_overlap_guard(
    generated_text: str,
    exemplar_text: str,
    max_ngram_threshold: int = 12,
    max_overlap_pct: float = 0.03,
    min_simhash_hamming: int = 18
) -> Dict[str, any]:
    """
    Evaluate overlap with exemplar text.
    
    Args:
        generated_text: Generated text to check
        exemplar_text: Exemplar text to compare against
        max_ngram_threshold: Maximum allowed n-gram length
        max_overlap_pct: Maximum allowed overlap percentage
        min_simhash_hamming: Minimum required SimHash Hamming distance
        
    Returns:
        Dictionary with pass/fail, violations, and detailed metrics
    """
    # Find max shared n-gram
    max_ngram = find_max_ngram_overlap(generated_text, exemplar_text, max_n=20)
    
    # Calculate overlap percentage (using 4-grams)
    overlap_pct = calculate_ngram_overlap_percentage(generated_text, exemplar_text, n=4)
    
    # Calculate SimHash distance
    simhash_distance = check_simhash_distance(generated_text, exemplar_text)
    
    # Check violations
    violations = []
    
    if max_ngram > max_ngram_threshold:
        violations.append(f"Max n-gram {max_ngram} exceeds threshold {max_ngram_threshold}")
    
    if overlap_pct > max_overlap_pct:
        violations.append(f"Overlap {overlap_pct:.3f} exceeds threshold {max_overlap_pct}")
    
    if simhash_distance < min_simhash_hamming:
        violations.append(f"SimHash distance {simhash_distance} below threshold {min_simhash_hamming}")
    
    # Overall pass/fail
    passed = len(violations) == 0
    
    return {
        "pass": passed,
        "violations": violations,
        "max_ngram": max_ngram,
        "overlap_pct": overlap_pct,
        "simhash_distance": simhash_distance,
        "thresholds": {
            "max_ngram": max_ngram_threshold,
            "max_overlap_pct": max_overlap_pct,
            "min_simhash_hamming": min_simhash_hamming,
        }
    }
