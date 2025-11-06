"""
Exemplar Digest Pipeline

Parses an exemplar story and produces a structured ExemplarDigest@2 JSON artifact
describing style, form, and motifs.

This module uses basic text processing (regex, collections.Counter) to extract
stylometric features, paragraph/sentence statistics, dialogue ratios, and basic
structural information. No heavy NLP dependencies are used to keep the pipeline
deterministic and lightweight.
"""

import re
from collections import Counter
from pathlib import Path

from literary_structure_generator.models.exemplar_digest import (
    Beat,
    Discourse,
    ExemplarDigest,
    MetaInfo,
    Pacing,
    Safety,
    Stylometry,
)


def _read_file(path: str) -> str:
    """
    Read text file content.

    Args:
        path: Path to the exemplar text file

    Returns:
        File content as string
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return file_path.read_text(encoding="utf-8")


def _tokenize_sentences(text: str) -> list[str]:
    """
    Simple sentence tokenization using regex.

    Args:
        text: Input text

    Returns:
        List of sentences
    """
    # Split on sentence-ending punctuation followed by whitespace or end of string
    # This is a simple heuristic that works reasonably well
    sentences = re.split(r"[.!?]+(?:\s+|$)", text)
    # Filter out empty strings and strip whitespace
    return [s.strip() for s in sentences if s.strip()]


def _tokenize_words(text: str) -> list[str]:
    """
    Simple word tokenization using regex.

    Args:
        text: Input text

    Returns:
        List of words (tokens)
    """
    # Match word characters, including contractions
    return re.findall(r"\b[\w']+\b", text.lower())


def _split_paragraphs(text: str) -> list[str]:
    """
    Split text into paragraphs.

    Args:
        text: Input text

    Returns:
        List of paragraphs
    """
    # Split on multiple newlines
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _compute_sentence_length_histogram(sentences: list[str]) -> list[int]:
    """
    Compute histogram of sentence lengths.

    Args:
        sentences: List of sentences

    Returns:
        Histogram as list of counts.
        Bins represent word counts: [0-5], [6-10], [11-15], [16-20], [21-25],
        [26-30], [31-35], [36+], with an extra bin for edge cases.
    """
    # Bin boundaries (inclusive lower bounds)
    bins = [0, 6, 11, 16, 21, 26, 31, 36]
    histogram = [0] * (len(bins) + 1)

    for sentence in sentences:
        word_count = len(_tokenize_words(sentence))
        # Find the highest bin threshold this word_count meets or exceeds
        bin_idx = 0
        for i, threshold in enumerate(bins):
            if word_count >= threshold:
                bin_idx = i
        histogram[bin_idx] += 1

    return histogram


def _compute_paragraph_length_histogram(paragraphs: list[str]) -> list[int]:
    """
    Compute histogram of paragraph lengths in tokens.

    Args:
        paragraphs: List of paragraphs

    Returns:
        Histogram as list of counts (bins: 0-20, 21-40, 41-60, 61-80, 81-100, 101-150,
        151-200, 201+ tokens)
    """
    bins = [0, 21, 41, 61, 81, 101, 151, 201]
    histogram = [0] * (len(bins) + 1)

    for paragraph in paragraphs:
        word_count = len(_tokenize_words(paragraph))
        # Find appropriate bin
        bin_idx = 0
        for i, threshold in enumerate(bins):
            if word_count >= threshold:
                bin_idx = i
        histogram[bin_idx] += 1

    return histogram


def _detect_dialogue_ratio(text: str) -> float:
    """
    Detect dialogue ratio by counting quoted text.

    Args:
        text: Input text

    Returns:
        Ratio of dialogue to total text (0.0-1.0)
    """
    # Find all quoted text (supporting various quote styles)
    # Support curly/smart quotes (U+201C, U+201D) and straight quotes
    left_double = "\u201c"  # "
    right_double = "\u201d"  # "

    # Try smart quotes first, then fall back to straight quotes
    pattern_smart = f"{left_double}([^{left_double}{right_double}]*?){right_double}"
    pattern_straight = r'"([^"]*?)"'
    pattern_single = r"'([^']*?)'"

    matches_smart = re.findall(pattern_smart, text)
    matches_straight = re.findall(pattern_straight, text)
    matches_single = re.findall(pattern_single, text)

    # Calculate total quoted characters
    quoted_chars = (
        sum(len(m) for m in matches_smart) +
        sum(len(m) for m in matches_straight) +
        sum(len(m) for m in matches_single)
    )
    total_chars = len(text.strip())

    if total_chars == 0:
        return 0.0

    return min(1.0, quoted_chars / total_chars)


def _extract_function_word_profile(words: list[str], top_n: int = 20) -> dict[str, float]:
    """
    Extract frequency profile of common function words.

    Args:
        words: List of words (already lowercased)
        top_n: Number of top function words to return

    Returns:
        Dictionary mapping function words to their frequencies (per 100 words)
    """
    # Common function words
    function_words = {
        "the", "and", "but", "or", "as", "if", "when", "where", "while",
        "a", "an", "of", "in", "on", "at", "to", "for", "with", "from",
        "by", "about", "through", "over", "under", "into", "onto",
        "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
        "is", "was", "are", "were", "be", "been", "being", "have", "has", "had",
    }

    total_words = len(words)
    if total_words == 0:
        return {}

    # Count function words
    word_counts = Counter(words)
    function_word_counts = {
        word: count for word, count in word_counts.items()
        if word in function_words
    }

    # Get top N and convert to frequency per 100 words
    top_function_words = Counter(function_word_counts).most_common(top_n)
    return {
        word: (count / total_words) * 100.0
        for word, count in top_function_words
    }


def _calculate_type_token_ratio(words: list[str]) -> float:
    """
    Calculate type-token ratio (lexical diversity).

    Args:
        words: List of words

    Returns:
        Type-token ratio (0.0-1.0)
    """
    if not words:
        return 0.0

    unique_words = set(words)
    return len(unique_words) / len(words)


def _analyze_punctuation_density(text: str, word_count: int) -> dict[str, float]:
    """
    Analyze punctuation density (per 100 words).

    Args:
        text: Input text
        word_count: Total word count

    Returns:
        Dictionary with punctuation densities
    """
    if word_count == 0:
        return {}

    punctuation_counts = {
        "comma_per_100": text.count(","),
        "period_per_100": text.count("."),
        "semicolon_per_100": text.count(";"),
        "dash_per_100": text.count("—") + text.count("\u2013") + text.count("--"),
        "exclamation_per_100": text.count("!"),
        "question_per_100": text.count("?"),
    }

    # Convert to per 100 words
    return {
        key: (count / word_count) * 100.0
        for key, count in punctuation_counts.items()
    }


def _create_placeholder_beats(total_tokens: int) -> list[Beat]:
    """
    Create placeholder beat segmentation.

    For now, this creates a simple 3-beat structure:
    - Opening (first 20%)
    - Middle (middle 60%)
    - Closing (last 20%)

    Args:
        total_tokens: Total token count

    Returns:
        List of Beat objects
    """
    # Simple placeholder segmentation
    opening_end = int(total_tokens * 0.2)
    middle_end = int(total_tokens * 0.8)

    return [
        Beat(
            id="opening",
            span=[0, opening_end],
            function="establish setting and tone",
        ),
        Beat(
            id="middle",
            span=[opening_end, middle_end],
            function="develop conflict and action",
        ),
        Beat(
            id="closing",
            span=[middle_end, total_tokens],
            function="resolution and denouement",
        ),
    ]


def _calculate_profanity_rate() -> float:
    """
    Calculate profanity rate.

    In Clean Mode, this always returns 0.0.

    Returns:
        Profanity rate (always 0.0 in Clean Mode)
    """
    return 0.0


def analyze_text(path: str) -> ExemplarDigest:
    """
    Read exemplar, compute stylometry & structural stats, and return populated model.

    This function performs basic text analysis to extract:
    - Sentence length histogram
    - Paragraph length histogram
    - Dialogue ratio (detected from quotes)
    - Part-of-speech / function-word frequency
    - Simple beat segmentation placeholder
    - Profanity rate (always 0.0 in Clean Mode)

    Args:
        path: Path to the exemplar text file

    Returns:
        Populated ExemplarDigest model with extracted features

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    # Read the text file
    text = _read_file(path)

    # Extract file name for source metadata
    source_name = Path(path).stem

    # Tokenize into sentences, words, and paragraphs
    sentences = _tokenize_sentences(text)
    words = _tokenize_words(text)
    paragraphs = _split_paragraphs(text)

    total_tokens = len(words)
    total_paragraphs = len(paragraphs)

    # Compute sentence length histogram
    sentence_len_hist = _compute_sentence_length_histogram(sentences)

    # Compute paragraph length histogram
    paragraph_len_hist = _compute_paragraph_length_histogram(paragraphs)

    # Detect dialogue ratio
    dialogue_ratio = _detect_dialogue_ratio(text)

    # Extract function word profile
    function_word_profile = _extract_function_word_profile(words, top_n=20)

    # Calculate type-token ratio
    type_token_ratio = _calculate_type_token_ratio(words)

    # Analyze punctuation density
    punctuation = _analyze_punctuation_density(text, total_tokens)

    # Create placeholder beats
    beats = _create_placeholder_beats(total_tokens)

    # Calculate profanity rate (always 0.0 in Clean Mode)
    profanity_rate = _calculate_profanity_rate()

    # Create and populate ExemplarDigest model
    return ExemplarDigest(
        meta=MetaInfo(
            source=source_name,
            tokens=total_tokens,
            paragraphs=total_paragraphs,
        ),
        stylometry=Stylometry(
            sentence_len_hist=sentence_len_hist,
            type_token_ratio=type_token_ratio,
            function_word_profile=function_word_profile,
            punctuation=punctuation,
        ),
        discourse=Discourse(
            beats=beats,
            dialogue_ratio=dialogue_ratio,
        ),
        pacing=Pacing(
            paragraph_len_hist=paragraph_len_hist,
        ),
        safety=Safety(
            profanity_rate=profanity_rate,
        ),
    )
