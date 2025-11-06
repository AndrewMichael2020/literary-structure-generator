"""
Stylefit Rules Evaluator

Heuristic checks against StorySpec for style conformance:
- Voice person/tense consistency (regex cues)
- Target sentence length (± tolerance)
- Parataxis ratio
- Dialogue ratio tolerance
- Clean Mode confirmation

Returns score 0..1
"""

import re
from typing import Dict

from literary_structure_generator.models.story_spec import StorySpec


def check_person_consistency(text: str, target_person: str) -> float:
    """
    Check narrative person consistency using regex cues.
    
    Args:
        text: Generated text
        target_person: Target person (first, second, third-limited, omniscient)
        
    Returns:
        Score 0..1 where 1.0 is perfect consistency
    """
    # Count person markers
    first_person = len(re.findall(r'\b(I|me|my|mine|we|us|our|ours)\b', text, re.IGNORECASE))
    second_person = len(re.findall(r'\byou\b', text, re.IGNORECASE))
    third_person = len(re.findall(r'\b(he|him|his|she|her|hers|they|them|their)\b', text, re.IGNORECASE))
    
    total = first_person + second_person + third_person
    if total == 0:
        return 0.5  # Neutral - no clear person markers
    
    # Calculate dominance of target person
    if target_person == "first":
        ratio = first_person / total
    elif target_person == "second":
        ratio = second_person / total
    elif target_person in ["third-limited", "omniscient"]:
        ratio = third_person / total
    else:
        return 0.5  # Unknown target person
    
    return min(1.0, ratio * 1.5)  # Boost good ratios, cap at 1.0


def check_tense_consistency(text: str, target_tense: str) -> float:
    """
    Check narrative tense consistency using regex cues.
    
    Args:
        text: Generated text
        target_tense: Target tense (past, present, future)
        
    Returns:
        Score 0..1 where 1.0 is perfect consistency
    """
    # Simple heuristic: count verb forms
    # Past tense markers: -ed endings (simplified)
    past_markers = len(re.findall(r'\b\w+ed\b', text))
    # Present tense markers: -s endings on verbs, am/is/are
    present_markers = len(re.findall(r'\b(am|is|are|was|were)\b', text, re.IGNORECASE))
    
    total = past_markers + present_markers
    if total == 0:
        return 0.5
    
    if target_tense == "past":
        ratio = past_markers / total
    elif target_tense == "present":
        ratio = present_markers / total
    else:
        return 0.5
    
    return min(1.0, ratio * 1.3)


def calculate_avg_sentence_length(text: str) -> float:
    """
    Calculate average sentence length in words.
    
    Args:
        text: Text to analyze
        
    Returns:
        Average sentence length
    """
    # Split by sentence-ending punctuation
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return 0.0
    
    total_words = sum(len(s.split()) for s in sentences)
    return total_words / len(sentences)


def check_sentence_length(text: str, target_length: int, tolerance: float = 0.3) -> float:
    """
    Check if average sentence length matches target within tolerance.
    
    Args:
        text: Generated text
        target_length: Target average sentence length
        tolerance: Allowed deviation (as fraction)
        
    Returns:
        Score 0..1 where 1.0 is within tolerance
    """
    actual_length = calculate_avg_sentence_length(text)
    
    if actual_length == 0:
        return 0.0
    
    deviation = abs(actual_length - target_length) / target_length
    
    if deviation <= tolerance:
        return 1.0 - (deviation / tolerance) * 0.3  # Linear decay within tolerance
    else:
        # Exponential decay outside tolerance
        excess = deviation - tolerance
        return max(0.0, 0.7 * (0.5 ** (excess * 5)))


def calculate_parataxis_ratio(text: str) -> float:
    """
    Estimate parataxis ratio (simple vs complex sentences).
    
    Args:
        text: Text to analyze
        
    Returns:
        Parataxis ratio 0..1 (higher = more paratactic/simple)
    """
    # Count coordinating conjunctions (and, but, or) vs subordinating (because, although, if, when)
    coord_conj = len(re.findall(r'\b(and|but|or)\b', text, re.IGNORECASE))
    subord_conj = len(re.findall(r'\b(because|although|though|if|when|while|since|unless|until)\b', text, re.IGNORECASE))
    
    # Count commas (proxy for clause complexity)
    commas = text.count(',')
    
    # Simple heuristic: more coordination and fewer commas = more paratactic
    total_conj = coord_conj + subord_conj
    if total_conj == 0:
        return 0.5
    
    coord_ratio = coord_conj / total_conj
    
    # Adjust by comma density
    sentences = len(re.split(r'[.!?]+', text))
    comma_density = commas / max(1, sentences)
    
    # Low comma density and high coordination = paratactic
    parataxis_score = coord_ratio * (1.0 - min(1.0, comma_density / 3.0))
    
    return parataxis_score


def check_parataxis_ratio(text: str, target_ratio: float, tolerance: float = 0.2) -> float:
    """
    Check if parataxis ratio matches target within tolerance.
    
    Args:
        text: Generated text
        target_ratio: Target parataxis ratio (0..1)
        tolerance: Allowed deviation
        
    Returns:
        Score 0..1
    """
    actual_ratio = calculate_parataxis_ratio(text)
    deviation = abs(actual_ratio - target_ratio)
    
    if deviation <= tolerance:
        return 1.0 - (deviation / tolerance) * 0.3
    else:
        excess = deviation - tolerance
        return max(0.0, 0.7 * (0.5 ** (excess * 3)))


def calculate_dialogue_ratio(text: str) -> float:
    """
    Calculate dialogue ratio (text in quotes / total text).
    
    Args:
        text: Text to analyze
        
    Returns:
        Dialogue ratio 0..1
    """
    # Find all quoted text
    dialogue_pattern = r'"([^"]+)"'
    dialogue_matches = re.findall(dialogue_pattern, text)
    
    dialogue_words = sum(len(d.split()) for d in dialogue_matches)
    total_words = len(text.split())
    
    if total_words == 0:
        return 0.0
    
    return dialogue_words / total_words


def check_dialogue_ratio(text: str, target_ratio: float, tolerance: float = 0.1) -> float:
    """
    Check if dialogue ratio matches target within tolerance.
    
    Args:
        text: Generated text
        target_ratio: Target dialogue ratio (0..1)
        tolerance: Allowed deviation
        
    Returns:
        Score 0..1
    """
    actual_ratio = calculate_dialogue_ratio(text)
    deviation = abs(actual_ratio - target_ratio)
    
    if deviation <= tolerance:
        return 1.0 - (deviation / tolerance) * 0.2
    else:
        excess = deviation - tolerance
        return max(0.0, 0.8 * (0.5 ** (excess * 5)))


def check_clean_mode(text: str) -> bool:
    """
    Check if text passes clean mode (no profanity).
    
    Args:
        text: Text to check
        
    Returns:
        True if clean, False otherwise
    """
    # Simple profanity check (extend as needed)
    profanity_words = [
        r'\bdamn\b', r'\bhell\b', r'\bass\b', r'\bshit\b', r'\bfuck\b',
        r'\bbitch\b', r'\bbastard\b', r'\bcrap\b'
    ]
    
    text_lower = text.lower()
    for word_pattern in profanity_words:
        if re.search(word_pattern, text_lower):
            return False
    
    return True


def evaluate_stylefit_rules(text: str, spec: StorySpec) -> Dict[str, float]:
    """
    Evaluate style conformance using heuristic rules.
    
    Args:
        text: Generated text to evaluate
        spec: StorySpec with target style parameters
        
    Returns:
        Dictionary with overall score and component scores
    """
    # Extract target parameters from spec
    target_person = spec.voice.person
    target_tense = spec.voice.tense_strategy.primary
    target_sentence_len = spec.voice.syntax.avg_sentence_len
    target_parataxis = spec.voice.syntax.parataxis_vs_hypotaxis
    target_dialogue_ratio = spec.form.dialogue_ratio
    profanity_allowed = spec.voice.profanity.allowed
    
    # Run all checks
    person_score = check_person_consistency(text, target_person)
    tense_score = check_tense_consistency(text, target_tense)
    sentence_len_score = check_sentence_length(text, target_sentence_len)
    parataxis_score = check_parataxis_ratio(text, target_parataxis)
    dialogue_score = check_dialogue_ratio(text, target_dialogue_ratio)
    clean_mode_pass = check_clean_mode(text)
    
    # Clean mode hard fail
    if not profanity_allowed and not clean_mode_pass:
        clean_mode_score = 0.0
    else:
        clean_mode_score = 1.0
    
    # Weighted combination
    overall = (
        person_score * 0.2 +
        tense_score * 0.15 +
        sentence_len_score * 0.25 +
        parataxis_score * 0.15 +
        dialogue_score * 0.15 +
        clean_mode_score * 0.1
    )
    
    return {
        "overall": overall,
        "person_consistency": person_score,
        "tense_consistency": tense_score,
        "sentence_length": sentence_len_score,
        "parataxis_ratio": parataxis_score,
        "dialogue_ratio": dialogue_score,
        "clean_mode": clean_mode_score,
    }
